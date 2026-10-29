"""Tahap 2 / langkah 08: tabel trade-off antar metode (Q8), disusun dari hasil uji risiko dan utilitas. Hasil: results/2-analysis/method_tradeoff.csv."""
import numpy as np
import pandas as pd

import analysis_lib as A
from analysis_lib import C

R = lambda f: pd.read_csv(C.RES_ANALYSIS / f)
raw, _ = A.load_raw()
anon, _ = A.load_anon()
att, k, notes, cells = R("risk_dictionary_attack.csv"), R("risk_k_anonymity.csv"), R("risk_notes.csv"), R("risk_operator_cells.csv")
gran, trend, prof = R("granularity_curve.csv"), R("utility_trend.csv"), pd.read_csv(C.RES_PREP / "data_profile.csv").set_index("item")["value"]
tight = k.iloc[-1]
# skala: penyerang tahu satu nilai asli -> sisanya terhitung
known = raw.input_qty.iloc[0]
factor = known / anon.input_index.iloc[0]
scale_recovered = float((np.rint(anon.input_index * factor) == raw.input_qty).mean())
lot_after = int((anon.lot_code.str.split("-").str[0] != "LOT").sum())

summ = pd.read_csv(C.RES_PREP / "anonymize_summary.csv").set_index("item")["value"]
n_persons = raw.operator.nunique()
changed_regex = 1 - notes.rows_text_unchanged[1] / notes.rows[1]
# (metode, kolom, ukuran risiko, sebelum, sesudah, ukuran utilitas, nilai utilitas, bisa dibalik, kelemahan)
rows = [
    ["Pseudonymization HMAC-SHA256 + kunci", "operator_name", "Operator yang namanya pulih lewat serangan kamus (rasio)", att.recovery_rate[0], att.recovery_rate[1],
     "Orang yang punya tepat satu kode (rasio)", float(summ["kode operator unik"]) / n_persons, "Tidak tanpa daftar kode",
     "Tetap bisa disambungkan oleh pihak yang punya daftar jaga"],
    ["Hash biasa SHA-256 tanpa kunci (pembanding)", "operator_name", "Operator yang namanya pulih lewat serangan kamus (rasio)", att.recovery_rate[0], att.recovery_rate[0],
     "Orang yang punya tepat satu kode (rasio)", 1.0, "Tidak", "Tidak aman: daftar nama umum cukup untuk menebak"],
    ["Mapping key", "lot_no", "Baris model khusus yang kode lotnya memuat nama customer", float(prof["baris model khusus dengan nama customer di kode lot"]), lot_after,
     "Lot yang tetap bisa dibedakan (rasio)", float(anon.lot_code.nunique() / raw.lot_no.nunique()), "Ya, oleh pemegang kunci",
     "Tabel pemetaan harus disimpan terpisah dan tidak ikut dibagikan"],
    ["Generalisasi tanggal ke minggu", "date", "Baris unik pada kombinasi terketat (rasio)", tight.pct_unique_before, tight.pct_unique_after,
     "Titik waktu tren yang tersisa (rasio terhadap harian)", float(gran.time_points[1] / gran.time_points[0]), "Tidak",
     "Kejadian singkat dalam satu minggu tidak terlihat"],
    ["Skala angka (indeks base 100)", "input_qty, ng_qty", "Nilai asli yang terhitung bila satu nilai asli diketahui (rasio)", 1.0, scale_recovered,
     "Selisih yield lini (poin)", float(abs(A.line_yield(raw) - A.line_yield(anon))), "Ya, dengan nilai dasar",
     "Hanya menyamarkan nilai absolut, bukan pengaman penuh"],
    ["Hapus kolom identitas", "employee_id, customer_name", "Nilai identitas langsung yang tersisa (jumlah baris x kolom)", float(len(raw) * 2), 0.0,
     "Kolom yang dihapus (jumlah)", 2.0, "Tidak", "Kolom lain bisa bocor lewat teks bebas bila tidak dibersihkan"],
    ["Bersihkan catatan: allowlist frasa aman", "note", "Catatan dengan nama, telepon, atau customer (baris)", float(notes.rows_with_identity[0]), float(notes.rows_with_identity[2]),
     "Catatan yang berubah (rasio baris)", float(1 - notes.rows_text_unchanged[2] / notes.rows[2]), "Tidak",
     "Catatan bermanfaat yang tidak ada di daftar ikut terhapus"],
    ["Bersihkan catatan: regex nama dan telepon (pembanding)", "note", "Catatan dengan nama, telepon, atau customer (baris)", float(notes.rows_with_identity[0]), float(notes.rows_with_identity[1]),
     "Catatan yang berubah (rasio baris)", float(changed_regex), "Tidak", "Nama depan saja dan variasi penulisan lolos dari regex"],
    ["Tutup kode operator di sel satu orang", "operator_code", "Sel stasiun x shift yang menunjuk satu orang", float(cells.single_person_identifiable_before.sum()),
     float(cells.single_person_identifiable_after.sum()), "Baris tanpa kode operator (rasio)", float((anon.operator_code == "OP-MASKED").mean()), "Tidak",
     "Analisis per operator di sel itu hilang"],
]
tr = pd.DataFrame(rows, columns=["method", "applied_to", "risk_measure", "risk_before", "risk_after", "utility_measure", "utility_value", "reversible", "weakness"])
tr.to_csv(C.RES_ANALYSIS / "method_tradeoff.csv", index=False)
print(tr[["method", "risk_before", "risk_after", "utility_value"]].to_string(index=False))
