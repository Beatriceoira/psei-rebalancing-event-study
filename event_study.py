"""PSEi rebalancing event study.

Data: carlo01092/pse GitHub dataset (daily OHLCV JSON, through 2021-03-12).
Events: PSEi composition changes verified from PSE releases / press reports.
T0 = announcement date, E = effective date (first trading day on/after).
"""
import json, sys, os
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

DATA = sys.argv[1]            # .../carlo01092_pse/json
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)

EVENTS = [  # id, announcement, effective, adds, dels
    (1, "2008-04-28", "2008-05-26", ["PNB", "RCB", "UBP", "VLL"], ["PCOR", "ABS", "BEL", "DMC"]),
    (2, "2009-04-17", "2009-05-04", ["GMA7", "APC"], ["PCOR", "UBP"]),
    (3, "2009-10-22", "2009-11-03", ["PSE", "DMC", "SECB"], ["VLL", "RCB", "ABS"]),
    (4, "2011-08-25", "2011-09-12", ["BEL", "CEB", "SMC", "SCC", "SMDC"], ["ABS", "FLI", "FPH", "LC", "SECB"]),
    (5, "2013-02-28", "2013-03-11", ["BLOOM"], ["SMDC"]),
    (6, "2013-08-28", "2013-09-16", ["LTG", "GTCAP"], ["MER", "BEL"]),
    (7, "2014-02-24", "2014-03-17", ["MER"], ["MWC"]),
    (8, "2016-08-24", "2016-09-12", ["SECB"], ["BLOOM"]),
    (9, "2017-02-22", "2017-03-13", ["PGOLD"], ["EMP"]),
    (10, "2019-02-08", "2019-02-18", ["BLOOM"], ["PCOR"]),
]

def load(t):
    p = f"{DATA}/{t}.json"
    if not os.path.exists(p):
        return None
    d = json.load(open(p))
    s = pd.DataFrame({"c": d["c"], "v": d["v"]},
                     index=pd.to_datetime(d["t"], unit="s").normalize())
    return s[~s.index.duplicated(keep="last")].sort_index()

mkt = load("PSEI")
cal = mkt.index
rm = np.log(mkt["c"]).diff()

PRE, POST = 30, 45
EST_A, EST_B = 250, 31

rows, skipped = [], []
for eid, ann, eff, adds, dels in EVENTS:
    t0 = cal.searchsorted(pd.Timestamp(ann))
    e = cal.searchsorted(pd.Timestamp(eff))
    for leg, names in (("add", adds), ("del", dels)):
        for tk in names:
            s = load(tk)
            if s is None:
                skipped.append((eid, tk, leg, "no data file")); continue
            px = s["c"].reindex(cal)
            vol = s["v"].reindex(cal)
            traded = vol.fillna(0) > 0
            r = np.log(px.ffill()).diff()
            r[px.ffill().isna()] = np.nan
            lo, hi = t0 - EST_A, t0 - EST_B
            est = pd.DataFrame({"r": r.iloc[lo:hi], "m": rm.iloc[lo:hi], "tr": traded.iloc[lo:hi]}).dropna()
            if len(est) < 120 or est["tr"].mean() < 0.5:
                skipped.append((eid, tk, leg, f"insufficient estimation data (n={len(est)}, traded={est['tr'].mean() if len(est) else 0:.2f})")); continue
            slope, icpt = stats.linregress(est["m"], est["r"])[:2]
            idx = np.arange(t0 - PRE, t0 + POST + 1)
            if idx.max() >= len(cal):
                skipped.append((eid, tk, leg, "event window past data end")); continue
            rr = r.iloc[idx].values; mm = rm.iloc[idx].values
            ar_mm = rr - (icpt + slope * mm)       # market model
            ar_ma = rr - mm                        # market-adjusted
            # abnormal volume: v / median traded volume over [-60,-11]
            base = vol.iloc[t0 - 60:t0 - 10]; base = base[base > 0]
            avr = (vol.iloc[idx].values / base.median()) if len(base) >= 20 else np.full(len(idx), np.nan)
            rows.append(dict(event=eid, leg=leg, ticker=tk, t0=t0, e=e, gap=e - t0,
                             beta=slope, n_est=len(est),
                             off=idx - t0, ar_mm=ar_mm, ar_ma=ar_ma, avr=avr))

R = pd.DataFrame(rows)
print("stock-events used:", R.groupby("leg").size().to_dict(), " events:", R.event.nunique())
print("skipped:", skipped)

def cum(row, key, a, b):
    """sum of AR from relative day a..b (inclusive) relative to T0"""
    off = row["off"]; m = (off >= a) & (off <= b)
    return np.nansum(row[key][m])

def window_defs(row):
    g = row["gap"]
    return {
        "[-10,-1] pre-announcement": (-10, -1),
        "[0,+1] announcement": (0, 1),
        "[0,+5] announcement": (0, 5),
        "[0,E-1] ann. to eve of effective (hindsight entry)": (0, g - 1),
        "[+1,E-1] tradable: buy T0 close, sell E-1 close": (1, g - 1),
        "[E,E+10] post-effective reversal": (g, g + 10),
        "[0,E+10] full": (0, g + 10),
    }

recs = []
for _, row in R.iterrows():
    for wname, (a, b) in window_defs(row).items():
        for key in ("ar_mm", "ar_ma"):
            recs.append(dict(event=row.event, leg=row.leg, ticker=row.ticker, window=wname,
                             model="market model" if key == "ar_mm" else "market-adjusted",
                             car=cum(row, key, a, b)))
C = pd.DataFrame(recs)

def tstats(x):
    x = np.asarray(x, float); x = x[~np.isnan(x)]
    if len(x) < 2: return np.nan, np.nan, len(x)
    t, p = stats.ttest_1samp(x, 0.0)
    return t, p, len(x)

out = []
for (model, wname), g in C.groupby(["model", "window"], sort=False):
    res = dict(model=model, window=wname)
    ev = {}
    for leg in ("add", "del"):
        gl = g[g.leg == leg]
        t, p, n = tstats(gl.car)
        res[f"{leg}_mean_%"] = gl.car.mean() * 100; res[f"{leg}_n"] = n
        res[f"{leg}_t_xsec"] = t
        e_lvl = gl.groupby("event").car.mean()      # event-clustered
        t2, p2, n2 = tstats(e_lvl)
        res[f"{leg}_t_event"] = t2; res[f"{leg}_p_event"] = p2; res[f"{leg}_n_events"] = n2
        ev[leg] = e_lvl
    both = pd.concat(ev, axis=1).dropna()
    spread = both["add"] - both["del"]
    t3, p3, n3 = tstats(spread)
    res.update({"LS_mean_%": spread.mean() * 100, "LS_t_event": t3, "LS_p_event": p3, "LS_n_events": n3,
                "LS_pos_events": int((spread > 0).sum())})
    out.append(res)
T = pd.DataFrame(out)
T.to_csv(f"{OUT}/car_tests.csv", index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
print(T[T.model == "market model"].round(3).to_string(index=False))
print(T[T.model == "market-adjusted"].round(3).to_string(index=False))

# ---------- chart data ----------
def curve_T0(leg, key, start=-10, stop=20):
    arr = []
    for _, r in R[R.leg == leg].iterrows():
        off = r["off"]; m = (off >= start) & (off <= stop)
        arr.append((r.event, np.nancumsum(r[key][m])))
    return arr

def curve_E(leg, key, start=-10, stop=20):
    arr = []
    for _, r in R[R.leg == leg].iterrows():
        rel = r["off"] - r["gap"]; m = (rel >= start) & (rel <= stop)
        arr.append((r.event, np.nancumsum(r[key][m])))
    return arr

def band(curves):
    ev = {}
    for e_, c in curves: ev.setdefault(e_, []).append(c)
    M = np.array([np.mean(v, axis=0) for v in ev.values()])  # event-level
    mean = M.mean(0)
    se = M.std(0, ddof=1) / np.sqrt(len(M)) if len(M) > 1 else np.zeros_like(mean)
    return mean * 100, se * 100, M

BLUE, ORANGE, GREY = "#0072B2", "#D55E00", "#555555"
key = "ar_mm"
fig, axes = plt.subplots(1, 3, figsize=(17, 5.2))
for ax, fn, xs, ttl, xl in (
    (axes[0], curve_T0, np.arange(-10, 21), "A. Aligned on announcement (T0)", "trading days from announcement (T0)"),
    (axes[1], curve_E, np.arange(-10, 21), "B. Aligned on effective date (E)", "trading days from effective date (E)"),
):
    ma, sa, Ma = band(fn("add", key)); md, sd, Md = band(fn("del", key))
    n = min(len(xs), len(ma))
    xs = xs[:n]
    ax.plot(xs, ma[:n], color=BLUE, lw=2, label=f"Additions (n={len(Ma)} events)")
    ax.fill_between(xs, (ma - 1.96 * sa)[:n], (ma + 1.96 * sa)[:n], color=BLUE, alpha=.15)
    ax.plot(xs, md[:n], color=ORANGE, lw=2, label=f"Deletions (n={len(Md)} events)")
    ax.fill_between(xs, (md - 1.96 * sd)[:n], (md + 1.96 * sd)[:n], color=ORANGE, alpha=.15)
    k = min(len(Ma), len(Md))
    ax.plot(xs, (ma - md)[:n], color=GREY, lw=1.5, ls="--", label="Long adds / short dels spread")
    ax.axhline(0, color="k", lw=.6); ax.axvline(0, color="k", lw=.6, ls=":")
    ax.set_title(ttl, loc="left", fontsize=12, fontweight="bold"); ax.set_xlabel(xl)
    ax.set_ylabel("mean cumulative abnormal return (%)"); ax.grid(alpha=.25)
    ax.legend(frameon=False, fontsize=9, loc="best")

# Panel C: abnormal volume around E
ax = axes[2]
for leg, col, lab in (("add", BLUE, "Additions"), ("del", ORANGE, "Deletions")):
    xs = np.arange(-5, 6); ys = []
    for x in xs:
        vals = []
        for _, r in R[R.leg == leg].iterrows():
            rel = r["off"] - r["gap"]; m = rel == x
            if m.any(): vals.append(r["avr"][m][0])
        vals = np.array(vals, float); vals = vals[np.isfinite(vals)]
        ys.append(np.median(vals) if len(vals) else np.nan)
    ax.plot(xs, ys, marker="o", color=col, lw=2, label=lab + " (median)")
ax.axhline(1, color="k", lw=.6); ax.axvline(0, color="k", lw=.6, ls=":")
ax.set_yscale("log")
ax.set_title("C. Volume vs. pre-event norm (median stock)", loc="left", fontsize=12, fontweight="bold")
ax.set_xlabel("trading days from effective date (E)"); ax.set_ylabel("volume / median volume [T0-60, T0-11] (log)")
ax.grid(alpha=.25, which="both"); ax.legend(frameon=False, fontsize=9)
fig.suptitle("PSEi rebalancing event study, 10 reviews with composition changes, 2008-2019 (market-model abnormal returns; bands = 95% CI across events)",
             fontsize=12, x=0.01, ha="left")
fig.tight_layout(rect=[0, 0, 1, .95])
fig.savefig(f"{OUT}/psei_rebalance_car.png", dpi=160)

R.drop(columns=["off", "ar_mm", "ar_ma", "avr"]).to_csv(f"{OUT}/stock_events.csv", index=False)
C.to_csv(f"{OUT}/cars_by_stock_event.csv", index=False)
print("done")
