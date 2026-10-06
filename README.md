# PSEi Index Rebalancing Arbitrage Analysis

An event study of Philippine equities around PSEi (PSE Index) composition changes: do additions and exclusions earn abnormal returns, and does volume spike, between the announcement and the effective rebalance date?

> **Research simulation only. Not investment advice or a recommendation to trade Philippine equities.**

## Overview

The Philippine Stock Exchange reviews the 30-stock PSEi periodically and publishes the changes ahead of the effective date. Index-tracking demand is concentrated on the effective date, which makes the window between announcement and effective date a candidate for a price-pressure / front-running effect in a thin market. This repository measures that effect for 10 historical reviews (2008–2019) and tests whether a simple long-additions / short-exclusions rule would have worked.

## Research Question

> Do Philippine equities experience statistically significant abnormal returns and volume changes after PSEi inclusion or exclusion announcements, and does the effect persist long enough to be traded between announcement and effective date?

- **H1 (additions):** mean CAR from announcement to the effective date is > 0.
- **H2 (exclusions):** mean CAR from announcement to the effective date is < 0.
- **H3 (reversal):** the effect partly reverses after the effective date (price-pressure hypothesis).

## Objectives

1. Build a verified list of PSEi additions/exclusions with announcement (T0) and effective (E) dates.
2. Compute abnormal returns and CARs relative to the PSEi.
3. Test significance with event-clustered, cross-sectional and non-parametric tests.
4. Separate the *event study* (hindsight windows) from the *tradable strategy* (enter after the announcement).

## Key Concepts

Event study methodology, index inclusion/exclusion drift, price pressure vs. information effects, abnormal volume, announcement-to-effective gap.

## Research Design

### Event Definition
- **T0** = announcement date, mapped to the first PSEi trading day on/after it.
- **E** = effective date, mapped to the first trading day on/after it.
- The announcement-to-effective gap ranges from 6 to 19 trading days.
- An *event* is one review. Each stock added or removed in that review is a *stock-event*: 20 additions and 20 exclusions in 10 events (the 9 events with both legs are used for the long-short spread).

| # | Announced (T0) | Effective | Added | Removed |
|---|---|---|---|---|
| 1 | 2008-04-28 | 2008-05-26 | PNB, RCB, UBP, VLL | PCOR, ABS, BEL, DMC |
| 2 | 2009-04-17 | 2009-05-04 | GMA7, APC | PCOR, UBP |
| 3 | 2009-10-22 | 2009-11-03 | PSE, DMC, SECB | VLL, RCB, ABS |
| 4 | 2011-08-25 | 2011-09-12 | BEL, CEB, SMC, SCC, SMDC* | ABS, FLI, FPH, LC, SECB |
| 5 | 2013-02-28 | 2013-03-11 | BLOOM | SMDC* |
| 6 | 2013-08-28 | 2013-09-16 | LTG, GTCAP | MER, BEL |
| 7 | 2014-02-24 | 2014-03-17 | MER | MWC |
| 8 | 2016-08-24 | 2016-09-12 | SECB | BLOOM |
| 9 | 2017-02-22 | 2017-03-13 | PGOLD | EMP |
| 10 | 2019-02-08 | 2019-02-18 | BLOOM | PCOR |

\* SMDC has no price file in the dataset and is excluded. Event 3's T0 is the article publication date (approximate). Reviews with no PSEi change (2015, 2016-03, 2017-09, 2018, 2019-08, 2021) are not events. Changes I could not date reliably (2010–2012) are omitted.

### Event Window
Cumulative from T0−10 for charts (Panels A and B); tests use the windows listed under Statistical Tests.

### Estimation Window
Trading days [T0−250, T0−31] (220 days). A stock-event needs at least 120 usable observations and a trading frequency of at least 50% of days.

### Benchmark
PSEi index close (from the same dataset).

### Abnormal Returns
Primary (market model), with market-adjusted returns as a robustness check:

$$AR_{i,t}=R_{i,t}-(\hat\alpha_i+\hat\beta_i R_{m,t}) \qquad\text{and}\qquad AR_{i,t}=R_{i,t}-R_{m,t}$$

Returns are daily log returns on closing prices.

### Cumulative Abnormal Returns

$$CAR_i(\tau_1,\tau_2)=\sum_{t=\tau_1}^{\tau_2}AR_{i,t}$$

## Strategy Definition

```text
Announcement (T0) ──► Effective date (E)
  Addition  ──► Long
  Exclusion ──► Short
```

### Index Additions / Index Exclusions
Long additions and short exclusions, equal-weighted within each event. The spread is (mean addition CAR) − (mean exclusion CAR) per event.

### Announcement-to-Rebalance Strategy
Two versions are reported: the hindsight window [0, E−1] (which assumes you could trade before the announcement-day move), and the **tradable** window [+1, E−1] (buy/short at the T0 close, exit at the E−1 close).

### Transaction Costs and Slippage
**Not modelled in the results below.** Commissions, the 0.6% stock transaction tax on sells, bid-ask spreads and borrow availability would reduce the gross spread. The short leg is likely not implementable for many of these stocks.

## Data

### Data Sources
- Daily OHLCV JSON: GitHub `carlo01092/pse` (`json/*.json`, 343 tickers including delisted names, through 2021-03-12; PSEi in `json/PSEI.json`).
- Index change history: PSE press releases and press coverage (PSE, Philstar, Inquirer, GMA, ABS-CBN).

### Required Data
Close, volume, PSEi close, announcement and effective dates.

### Data Cleaning
Prices are aligned to the PSEi trading calendar and forward-filled across non-trading days (so non-trading days carry zero return). Stocks with thin trading in the estimation window are dropped.

### Data Limitations
Unknown adjustment methodology for prices, volume units not documented (volume is used only as a ratio to the stock's own history), data ends March 2021, and the dataset is a third-party scrape that has not been reconciled with PSE records.

## Methodology

1. Identify PSEi events (table above).
2. Align dates on the PSEi trading calendar.
3. Compute log returns.
4. Estimate expected returns by OLS on [T0−250, T0−31].
5. Compute abnormal returns.
6. Cumulate to CARs over the windows below.
7. Test significance (see next section).
8. Volume: ratio of daily volume to the stock's median traded volume over [T0−60, T0−11].

## Statistical Tests

- **Event-clustered t-test** (primary): average stock-event CARs within each review, then a one-sample t-test across reviews. This accounts for stocks in the same review sharing a date.
- **Cross-sectional t-test** across stock-events (shown in `car_tests.csv`; overstates precision because of date clustering).
- **Wilcoxon signed-rank** across reviews.
- **95% confidence intervals** across reviews, and the number of events *N* reported with every test.
- Effect size (Cohen's d_z) for the spread.
- Robustness: market-adjusted returns, leave-one-event-out, excluding the three oldest events.

## Results

Market-model abnormal returns, in %. Means are pooled over stock-events; t and p are event-clustered; *N* = 10 events (additions), 9 (exclusions), 9 (spread).

### Key Findings

| Window | Additions mean (t, p) | Exclusions mean (t, p) | Long-short spread mean, [95% CI] | Wilcoxon p (spread) |
|---|---|---|---|---|
| [0,+1] announcement | +3.89 (6.30, <0.001) | −3.88 (−3.45, 0.009) | +8.83 [5.07, 12.58] | 0.004 |
| [+1,E−1] **tradable** | +3.82 (2.55, 0.031) | −4.62 (−2.32, 0.049) | +8.44 [4.58, 12.30] | 0.004 |
| [0,E−1] hindsight | +5.92 (4.10, 0.003) | −6.99 (−4.60, 0.002) | +13.66 (t = 5.23) | n/a |
| [E,E+10] reversal | −2.18 (−0.92, 0.38) | −0.66 (−0.65, 0.54) | −1.57 [−9.10, 5.96] | 0.734 |
| [−10,−1] pre-announcement | +0.37 (0.70, 0.50) | +1.67 (1.68, 0.13) | −1.33 (t = −0.45) | n/a |

Cohen's d_z for the spread: 1.81 ([0,+1]) and 1.68 ([+1,E−1]).

### Abnormal Return Analysis
About 4 points of abnormal return arrives within two days of the announcement on each leg. The positive spread appears in all 9 reviews with both legs for the announcement and tradable windows.

### CAR Analysis
See `psei_rebalance_car.png`, Panels A (aligned on T0) and B (aligned on E). Bands are 95% intervals across reviews.

### Volume Analysis
Median volume relative to the stock's own pre-event norm: additions 2.0× on E−1 and 2.2× on E; exclusions 2.7× on E−1 and 1.5× on E (Panel C). The spike is concentrated on the eve of the effective date.

### Addition vs. Exclusion Comparison
Both legs contribute; the exclusion leg is slightly larger on the tradable window but is also the leg least likely to be implementable.

### Robustness
- Market-adjusted returns give the same conclusions (tradable spread +8.95%, t = 5.34).
- Leave-one-event-out: tradable spread stays between +7.4% and +9.3% (max p = 0.003).
- Excluding events 1–3: tradable spread +8.96% (p = 0.007).
- The full [0,E+10] window is less robust: significant with all events (p = 0.024) but not with events 1–3 removed (p = 0.114).

## Visualizations

`psei_rebalance_car.png`: (A) mean CAR aligned on announcement, (B) aligned on effective date, (C) abnormal volume around E.

## Project Structure

```text
event_study.py        # full pipeline: events -> abnormal returns -> tests -> chart
out/
  psei_rebalance_car.png
  car_tests.csv         # all tests, both models, all windows
  cars_by_stock_event.csv
  stock_events.csv
```

## Installation

```bash
pip install pandas numpy scipy matplotlib
git clone --depth 1 https://github.com/carlo01092/pse.git
```

## Usage

```bash
python event_study.py ./pse/json ./out
```

## Reproducibility

Event dates are hard-coded in `event_study.py` (`EVENTS`). Results depend on the dataset snapshot (latest commit of `carlo01092/pse` at time of analysis, data through 2021-03-12).

## Limitations

- Small sample: 10 reviews; significance rests on 9–10 independent observations, and many windows were tested (no multiple-testing correction).
- Announcement timing: some stocks move on the announcement date itself, which suggests anticipation or leakage, so the tradable window under-captures the full effect.
- Costs, slippage, short-selling constraints and capacity are not modelled.
- Event 3's announcement date is approximate; SMDC is missing; 2010–2012 changes are not covered.
- The PSEi includes the stock being studied, a small bias in the market-model benchmark.
- The PSE revised its index methodology in July 2026 and results from 2008–2019 may not carry over.

## Future Improvements

Extend to 2021–2026 reviews with PSE Edge data; add transaction-cost and borrow assumptions; add a Patell/BMP standardized test; study pre-announcement drift using the published eligibility criteria; add unit tests for the returns and CAR functions.

## Security / Data Handling

No credentials or personal data are used. The price data is a third-party public GitHub dataset; PSE restricts redistribution of its own reports, so raw data is not included in this repository.

## References

- Brown, S. J., & Warner, J. B. (1985). Using daily stock returns: the case of event studies. *Journal of Financial Economics*.
- MacKinlay, A. C. (1997). Event studies in economics and finance. *Journal of Economic Literature*.
- Harris, L., & Gurel, E. (1986). Price and volume effects associated with changes in the S&P 500 list. *Journal of Finance*.
- Shleifer, A. (1986). Do demand curves for stocks slope down? *Journal of Finance*.
- PSE index review announcements (pse.com.ph) and the press coverage cited in the event table.

## License

To be chosen by the repository owner.
