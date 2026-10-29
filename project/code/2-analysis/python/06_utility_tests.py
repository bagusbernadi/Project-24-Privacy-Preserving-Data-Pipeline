"""Tahap 2 / langkah 06: uji utilitas (Q5-Q6): KPI, ranking, Pareto, tren, korelasi, data asli vs anonim. Hasil: results/2-analysis/utility_*.csv."""
import numpy as np
import pandas as pd

import analysis_lib as A
from analysis_lib import C

raw, rdef = A.load_raw()
anon, adef = A.load_anon()
TOL = 1e-6

# --- KPI (Q5)
ly_r, ly_a = A.line_yield(raw), A.line_yield(anon)
kpi = [["Yield lini (seluruh periode)", ly_r, ly_a]]
for key in ("model", "shift"):
    yr, ya = A.line_yield(raw, key), A.line_yield(anon, key)
    for k in yr.index:
        kpi.append([f"Yield lini, {key} = {k}", float(yr[k]), float(ya[k])])
sr, sa = A.station_rates(raw), A.station_rates(anon)
for st in sr.index:
    kpi.append([f"NG rate stasiun {st}", float(sr[st]), float(sa[st])])
kpi = pd.DataFrame(kpi, columns=["kpi", "raw", "anon"])
kpi["abs_diff"] = (kpi.raw - kpi.anon).abs()
kpi["same"] = kpi.abs_diff < TOL
kpi.to_csv(C.RES_ANALYSIS / "utility_kpi.csv", index=False)

# --- ranking stasiun dan Pareto (Q5)
rk = pd.DataFrame({"rank": range(1, len(sr) + 1), "station_raw": sr.index, "ng_rate_raw": sr.values, "station_anon": sa.index, "ng_rate_anon": sa.values})
rk["same_station"] = rk.station_raw == rk.station_anon
rk.to_csv(C.RES_ANALYSIS / "utility_station_ranking.csv", index=False)
pr, pa = A.pareto(rdef), A.pareto(adef)
dim = pd.read_csv(C.RAW_DIR / "dim_defect.csv").set_index("defect_code")["defect_name"]
par = pd.DataFrame({"rank": range(1, len(pr) + 1), "defect_raw": pr.defect_code, "defect_name": pr.defect_code.map(dim), "qty_raw": pr.qty,
                    "share_raw": pr.qty / pr.qty.sum(), "defect_anon": pa.defect_code, "qty_index_anon": pa.qty.round(6), "share_anon": pa.qty / pa.qty.sum()})
par["same_defect"] = par.defect_raw == par.defect_anon
par["share_diff"] = (par.share_raw - par.share_anon).abs()
par.to_csv(C.RES_ANALYSIS / "utility_pareto.csv", index=False)

# --- tren dan korelasi (Q6)
wr, wa = A.line_yield(raw, "week"), A.line_yield(anon, "week")
dr = A.line_yield(raw, "date")
g_r = raw.groupby(["station", "model"]).apply(lambda x: x.ng.sum() / x.input.sum(), include_groups=False)
g_a = anon.groupby(["station", "model"]).apply(lambda x: x.ng.sum() / x.input.sum(), include_groups=False)
tr = pd.DataFrame([
    ["Kemiringan tren yield lini, deret mingguan (poin persentase per minggu)", A.slope(wr), A.slope(wa)],
    ["Kemiringan tren yield lini, deret harian dikali 5 (asli) vs mingguan (anonim)", A.slope(dr) * 5, A.slope(wa)],
    ["Korelasi Pearson yield mingguan (asli mingguan = 1,0)", 1.0, float(np.corrcoef(wr.values, wa.reindex(wr.index).values)[0, 1])],
    ["Korelasi Pearson input vs NG per baris", float(np.corrcoef(raw.input, raw.ng)[0, 1]), float(np.corrcoef(anon.input, anon.ng)[0, 1])],
    ["Korelasi Pearson NG rate stasiun x model (asli = 1,0)", 1.0, float(np.corrcoef(g_r.values, g_a.reindex(g_r.index).values)[0, 1])],
    ["Yield lini terendah (asli: harian, anonim: mingguan)", float(dr.min()), float(wa.min())],
    ["Yield lini tertinggi (asli: harian, anonim: mingguan)", float(dr.max()), float(wa.max())],
    ["Jumlah titik waktu untuk tren", int(len(dr)), int(len(wa))]], columns=["metric", "raw", "anon"])
tr.to_csv(C.RES_ANALYSIS / "utility_trend.csv", index=False)

# --- tren mingguan: seri yield mingguan asli vs anonim (untuk dashboard)
pd.DataFrame({"week": wr.index, "yield_raw": wr.values, "yield_anon": wa.reindex(wr.index).values}).to_csv(C.RES_ANALYSIS / "utility_weekly_yield.csv", index=False)
print(kpi.head(8).to_string(index=False)); print(rk.head(3).to_string(index=False)); print(par.head(4).to_string(index=False)); print(tr.to_string(index=False))
print("semua KPI sama:", bool(kpi.same.all()), "| ranking sama:", bool(rk.same_station.all()), "| top3 pareto sama:", bool(par.head(3).same_defect.all()))
