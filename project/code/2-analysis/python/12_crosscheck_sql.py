"""Tahap 2 / langkah 12: cek silang SQL (DuckDB) vs pandas, pada data asli dan data anonim dengan query yang sama persis.
Hasil: results/2-analysis/crosscheck_sql.csv. KPI dihitung lewat view v_raw_* dan v_anon_* (code/2-analysis/sql)."""
import duckdb
import pandas as pd

import analysis_lib as A
from analysis_lib import C

con = duckdb.connect(str(C.DB_PATH), read_only=True)
kq, pq = C.load_sql(C.SQL_ANALYSIS / "02_kpi.sql"), C.load_sql(C.SQL_ANALYSIS / "03_privacy.sql")
raw, rdef = A.load_raw()
anon, adef = A.load_anon()
sets = {"asli": ("v_raw_prod", "v_raw_defect", raw, rdef, "date"), "anonim": ("v_anon_prod", "v_anon_defect", anon, adef, "week")}
rows = []
for name, (t, d, df, dd, tcol) in sets.items():
    fm = dict(t=t, d=d, first=A.FIRST, last=A.LAST)
    sql_ly = con.execute(kq["line_yield"].format(**fm)).fetchone()[0]
    rows.append(["yield lini", name, sql_ly, A.line_yield(df)])
    s = con.execute(kq["station_ng_rate"].format(**fm)).df().set_index("station")
    p = A.station_rates(df)
    rows.append(["NG rate stasiun (selisih terbesar, 10 stasiun)", name, 0.0, float((s.ng_rate - p.reindex(s.index)).abs().max())])
    rows.append(["urutan 10 stasiun (sama = 1)", name, 1.0, float(list(s.index) == list(p.index))])
    pa = con.execute(kq["pareto"].format(**fm)).df()
    pp = A.pareto(dd)
    rows.append(["urutan 20 kode defect (sama = 1)", name, 1.0, float(list(pa.defect_code) == list(pp.defect_code))])
    rows.append(["total qty defect", name, float(pa.qty.sum()), float(pp.qty.sum())])
    w = con.execute(kq["weekly_yield"].format(**fm)).df().set_index("week").line_yield
    rows.append(["yield mingguan (selisih terbesar, 15 minggu)", name, 0.0, float((w - A.line_yield(df, "week")).abs().max())])
    for key_ in ("model", "shift"):
        y = con.execute(kq[f"yield_by_{key_}"].format(**fm)).df().set_index(key_).line_yield
        rows.append([f"yield per {key_} (selisih terbesar)", name, 0.0, float((y - A.line_yield(df, key_)).abs().max())])
    for label, cols in (("terketat", [tcol, "shift", "station", "model", "operator"]), ("QI dasar", ["shift", "station", "model"])):
        r = con.execute(pq["k_anonymity"].format(t=t, cols=", ".join(cols))).fetchone()
        g = A.group_sizes(df, cols)
        rows.append([f"k minimum, kombinasi {label}", name, float(r[2]), float(g["k_min"])])
        rows.append([f"baris unik, kombinasi {label}", name, float(r[4]), g["pct_unique"]])
    ops = con.execute(pq["operators_per_cell"].format(t=t)).df()
    rows.append(["sel stasiun x shift dengan satu nilai operator", name, float((ops.n_operators == 1).sum()), float((df.groupby(["station", "shift"]).operator.nunique() == 1).sum())])
con.close()
cx = pd.DataFrame(rows, columns=["check", "dataset", "sql", "pandas"])
cx["abs_diff"] = (cx.sql - cx.pandas).abs()
cx["match"] = cx.abs_diff < 1e-9
cx.to_csv(C.RES_ANALYSIS / "crosscheck_sql.csv", index=False)
print(cx.to_string(index=False)); print("semua cocok:", bool(cx.match.all()))
