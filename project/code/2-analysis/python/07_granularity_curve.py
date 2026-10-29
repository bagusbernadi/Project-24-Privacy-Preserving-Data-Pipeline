"""Tahap 2 / langkah 07: kurva risiko vs utilitas menurut tingkat generalisasi tanggal (Q7). Hasil: results/2-analysis/granularity_curve.csv."""
import numpy as np
import pandas as pd

import analysis_lib as A
from analysis_lib import C

raw, rdef = A.load_raw()
raw["d"] = pd.to_datetime(raw["date"])
raw["t_idx"] = raw["d"].rank(method="dense").astype(int) - 1        # indeks hari kerja 0..74
keys = {"Harian": raw["date"], "Mingguan": raw["week"], "Dua mingguan": "B" + (raw.t_idx // 10).astype(str).str.zfill(2),
        "Bulanan": raw["d"].dt.strftime("%Y-%m"), "Seluruh periode": pd.Series("ALL", index=raw.index)}
wk = A.line_yield(raw, "week")
rows = []
for name, key in keys.items():
    df = raw.assign(T=key)
    cols = ["T", "shift", "station", "model", "operator"]
    gs = A.group_sizes(df, cols)
    series = A.line_yield(df, "T")
    # utilitas tren: yield tiap minggu diganti nilai periode tempat minggu itu berada; korelasi dengan deret mingguan asli
    wk_to_T = df.groupby("week")["T"].first()
    broadcast = wk_to_T.map(series).reindex(wk.index)
    if name in ("Harian", "Mingguan"):                     # tidak lebih kasar dari minggu: deret mingguan bisa dihitung persis
        corr, err = 1.0, 0.0
    else:
        corr = float(np.corrcoef(wk.values, broadcast.values)[0, 1]) if broadcast.nunique() > 1 else 0.0
        err = float((wk - broadcast).abs().max())
    rows.append([name, int(df["T"].nunique()), gs["pct_unique"], gs["k_min"], gs["k_median"], corr, err, gs["k_min"] >= C.K_TARGET])
cv = pd.DataFrame(rows, columns=["granularity", "time_points", "pct_unique", "k_min", "k_median", "trend_corr_weekly", "max_abs_error_yield", "k_target_met"])
cv.to_csv(C.RES_ANALYSIS / "granularity_curve.csv", index=False)
print(cv.to_string(index=False))
