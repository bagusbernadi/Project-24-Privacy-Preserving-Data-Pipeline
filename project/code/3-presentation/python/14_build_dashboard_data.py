"""Tahap 3 / langkah 14: siapkan CSV ringkas untuk dashboard (results/3-presentation/dash_*.csv). Dashboard tidak membaca data asli.
Contoh baris anonim memakai pola pada kolom kode (kode asli bergantung pada kunci rahasia, jadi tidak ikut di-commit)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
out = C.RES_PRESENT
R("granularity_curve.csv").to_csv(out / "dash_granularity.csv", index=False)
R("method_tradeoff.csv").to_csv(out / "dash_tradeoff.csv", index=False)
R("risk_dictionary_attack.csv").to_csv(out / "dash_attack.csv", index=False)
R("risk_notes.csv").to_csv(out / "dash_notes.csv", index=False)
R("utility_weekly_yield.csv").to_csv(out / "dash_weekly_yield.csv", index=False)
R("utility_pareto.csv").head(8).drop(columns=["qty_index_anon"]).to_csv(out / "dash_pareto.csv", index=False)
R("utility_station_ranking.csv").to_csv(out / "dash_ranking.csv", index=False)
R("validation_checks.csv").to_csv(out / "dash_validation.csv", index=False)
R("evaluation.csv").to_csv(out / "dash_evaluation.csv", index=False)
pd.read_csv(C.RES_PREP / "column_classification.csv").to_csv(out / "dash_policy.csv", index=False)
kpi = R("utility_kpi.csv")
kpi[~kpi.kpi.str.startswith("NG rate")].to_csv(out / "dash_kpi.csv", index=False)

a = pd.read_csv(C.ANON_DIR / "anonymized_production.csv")
a = a[(a.week == a.week.iloc[0]) & (a["shift"] == "Shift 1") & (a.model == "Matic 110")].head(10).copy()
a["operator_code"] = a.operator_code.map(lambda v: "OP-MASKED" if v == "OP-MASKED" else "OP-xxxxxxxx")
a["lot_code"] = "LOT-xxxxx"
a.to_csv(out / "dash_anon_sample.csv", index=False)
print("dash_*.csv:", len(list(out.glob("dash_*.csv"))))
