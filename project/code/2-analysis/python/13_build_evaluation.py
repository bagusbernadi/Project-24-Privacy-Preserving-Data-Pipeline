"""Tahap 2 / langkah 13: gabungkan ukuran risiko dan utilitas menjadi satu tabel evaluation.csv (metric, scope, before, after, method_set)."""
import pandas as pd

import analysis_lib as A
from analysis_lib import C

R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
k, att, notes, cells, link = R("risk_k_anonymity.csv"), R("risk_dictionary_attack.csv"), R("risk_notes.csv"), R("risk_operator_cells.csv"), R("risk_linkage.csv")
kpi, rk, par, tr, val = R("utility_kpi.csv"), R("utility_station_ranking.csv"), R("utility_pareto.csv"), R("utility_trend.csv"), R("validation_checks.csv")
imp, prof = R("impact_time.csv").set_index("item")["value"], pd.read_csv(C.RES_PREP / "data_profile.csv").set_index("item")["value"]
t = k.iloc[-1]
rows = [
    ("Baris unik (rasio)", "kombinasi terketat", t.pct_unique_before, t.pct_unique_after, "Generalisasi + Pseudonymization"),
    ("k minimum", "kombinasi terketat", t.k_min_before, t.k_min_after, "Generalisasi + Pseudonymization"),
    ("Nama operator pulih lewat serangan kamus (rasio)", "39 operator", att.recovery_rate[0], att.recovery_rate[1], "Pseudonymization HMAC"),
    ("Catatan bebas dengan identitas (baris)", "4500 catatan", notes.rows_with_identity[0], notes.rows_with_identity[2], "Hapus info sensitif (allowlist)"),
    ("Sel stasiun x shift yang menunjuk satu orang", "20 sel", cells.single_person_identifiable_before.sum(), cells.single_person_identifiable_after.sum(), "Tutup kode operator"),
    ("Kode lot yang memuat nama customer (baris)", "model khusus", prof["baris model khusus dengan nama customer di kode lot"], 0, "Mapping key"),
    ("Yield lini", "seluruh periode", kpi.raw[0], kpi.anon[0], "Skala angka + Generalisasi"),
    ("Stasiun dengan ranking NG sama (dari 3 terburuk)", "3 terburuk", 3, int(rk.head(3).same_station.sum()), "Skala angka"),
    ("Kode defect dengan peringkat sama (dari 3 teratas)", "Pareto 3 teratas", 3, int(par.head(3).same_defect.sum()), "Skala angka"),
    ("Kemiringan tren yield (poin persentase per minggu)", "mingguan", tr.raw[0], tr.anon[0], "Generalisasi + Skala angka"),
    ("Titik waktu untuk tren", "periode data", tr.raw[7], tr.anon[7], "Generalisasi"),
    ("Kode lot kembali ke nilai asli (baris dari 4500)", "mapping key", 4500, int(val[val.check.str.startswith("Kode lot dikembalikan")].n_pass.iloc[0]), "Mapping key"),
    ("Menit anonymization per file", "per file", imp["Waktu anonymization manual di Excel per file"], round(imp.iloc[0] / 60, 2), "Pipeline otomatis"),
]
ev = pd.DataFrame(rows, columns=["metric", "scope", "before", "after", "method_set"])
ev.to_csv(C.RES_ANALYSIS / "evaluation.csv", index=False)
print(ev.to_string(index=False))
