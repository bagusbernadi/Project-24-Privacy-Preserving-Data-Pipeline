"""Tahap 1 / langkah 04: bangun database DuckDB (data asli di tabel raw_*, data anonim di anon_*, kebijakan kolom) dan view seragam."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "2-analysis" / "python"))
import common as C  # noqa: E402
from analysis_lib import load_anon, load_raw  # noqa: E402
from pipeline.anonymize import load_policy  # noqa: E402

raw, rdef = load_raw()
anon, adef = load_anon()
pol = load_policy(C.COLUMN_POLICY)
cp = pd.DataFrame([(t, c, s["class"], s["method"], s["output"] or "", s["why"]) for t, cols in pol["tables"].items() for c, s in cols.items()],
                  columns=["table_name", "column_name", "class", "method", "output_column", "why"])
C.DB_PATH.unlink(missing_ok=True)
con = duckdb.connect(str(C.DB_PATH))
raw = raw.assign(operator_norm=raw["operator"]).drop(columns=["operator", "input", "ng"])
for name, df in (("raw_production", raw), ("raw_defect", rdef), ("anon_production", anon[["week", "shift", "station", "model", "operator_code", "lot_code", "input_index", "ng_index", "ng_rate", "note_clean"]]),
                 ("anon_defect", adef[["week", "shift", "station", "model", "defect_code", "qty_index"]]), ("column_policy", cp)):
    con.register("_t", df)
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM _t")
    con.unregister("_t")
for _, q in C.load_sql(C.SQL_PREP / "01_views.sql").items():
    con.execute(q)
for t in ("raw_production", "raw_defect", "anon_production", "anon_defect", "column_policy"):
    print(t, con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
con.close()
