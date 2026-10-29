"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
- Halaman ini tidak memuat nama, nomor karyawan, atau telepon (palsu sekalipun): contoh data memakai pola.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, HERE.as_posix())
from common import COLUMN_POLICY, DB_PATH, GROUND_TRUTH, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, cs, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, esc, gbars, hbars,  # noqa: E402
                        legend, lines, pareto_svg, pill, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Utama", 3: "Utama", 4: "Pendukung", 5: "Utama", 6: "Utama", 7: "Pendukung", 8: "Utama", 9: "Pendukung", 10: "Utama", 11: "Tambahan", 12: "Utama"}
QT = {1: "Kolom mana yang termasuk identitas langsung, quasi-identifier, sensitif, dan aman?",
      2: "Berapa persen baris yang unik pada kombinasi quasi-identifier sebelum dan sesudah anonymization?",
      3: "Apakah nama operator bisa ditebak dari kode samaran, misalnya dengan mencoba daftar nama umum?",
      4: "Apakah catatan bebas masih mengandung nama atau nomor telepon setelah dibersihkan?",
      5: "Apakah KPI yield, ranking stasiun, dan Pareto defect tetap sama setelah anonymization?",
      6: "Seberapa besar tren dan korelasi berubah setelah generalisasi tanggal dan skala angka?",
      7: "Tingkat generalisasi mana yang memberi risiko rendah tanpa merusak analisis?",
      8: "Metode mana yang cocok untuk tiap tipe kolom, dan apa trade-off-nya?",
      9: "Apakah pipeline menghasilkan output yang sama persis jika dijalankan ulang dengan kunci yang sama?",
      10: "Berapa menit anonymization manual per file yang digantikan pipeline?",
      11: "Berapa jam kerja per tahun yang bisa dihemat?",
      12: "Apakah pemegang mapping key bisa mengembalikan kode lot ke nilai aslinya dengan benar 100%?"}
WARN = set()


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
WK = lambda s: str(s)[-3:]                         # "2026-W10" -> "W10"

# ---------------------------------------------------------------- data
prof = R("data_profile.csv").set_index("item")["value"]
cc, summ, nv = R("column_classification.csv"), R("anonymize_summary.csv").set_index("item")["value"], R("name_variants.csv")
k, att, notes, tscan = R("risk_k_anonymity.csv"), R("risk_dictionary_attack.csv"), R("risk_notes.csv"), R("risk_text_scan.csv")
cells, link = R("risk_operator_cells.csv"), R("risk_linkage.csv")
kpi, rk, par, tr, wy, gran = R("utility_kpi.csv"), R("utility_station_ranking.csv"), R("utility_pareto.csv"), R("utility_trend.csv"), R("utility_weekly_yield.csv"), R("granularity_curve.csv")
trade, val, nn, sec = R("method_tradeoff.csv"), R("validation_checks.csv"), R("validation_name_normalization.csv"), R("secret_scan.csv")
imp, isc, cx, ev = R("impact_time.csv").set_index("item"), R("impact_scenarios.csv"), R("crosscheck_sql.csv"), R("evaluation.csv")
sample = pd.read_csv(RES_PRESENT / "dash_anon_sample.csv")
gt = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
pol = yaml.safe_load(COLUMN_POLICY.read_text(encoding="utf-8"))
con = duckdb.connect(str(DB_PATH), read_only=True)
dbt = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("raw_production", "raw_defect", "anon_production", "anon_defect", "column_policy")}
con.close()
pt = subprocess.run([sys.executable, "-m", "pytest", str(REPO / "project" / "tests"), "-q", "-p", "no:cacheprovider"], capture_output=True, text=True)
m_ = re.search(r"(\d+) passed", pt.stdout)
n_tests = int(m_.group(1)) if m_ else 0
assert pt.returncode == 0 and n_tests > 0, pt.stdout[-500:]

tight = k.iloc[-1]
a_hash, a_hmac, a_guess = att.iloc[0], att.iloc[1], att.iloc[2]
n_op = int(prof["operator (orang)"])
one_cell = cells[cells.single_person_identifiable_before].iloc[0]
gr = gran.set_index("granularity")
y_raw, y_anon = kpi.raw.iloc[0], kpi.anon.iloc[0]
vq = val.set_index("check")
vsum = lambda q: (int(val[val.question == q].n_tested.sum()), int(val[val.question == q].n_pass.sum()))
ok_cx = int(cx.match.sum())
slope_r, slope_a = tr.raw.iloc[0], tr.anon.iloc[0]
manual_min, files_yr = imp.loc["Waktu anonymization manual di Excel per file"].value, imp.loc["File yang dibagikan per tahun"].value
auto_s = imp.iloc[0].value
saved_h = imp.loc["Jam kerja dihemat per tahun"].value
n_case_rows = int(notes.rows[0])
leaked_tel = int(prof["catatan dengan nomor telepon"])
rest_regex, rest_allow, leak_all = int(notes.rows_with_identity[1]), int(notes.rows_with_identity[2]), int(notes.rows_with_identity[0])
masked_rows = int(summ["baris operator ditutup"])
lot_cust = int(prof["baris model khusus dengan nama customer di kode lot"])
sec_ok = (sec.hits == 0).all()
scan_after = tscan[tscan.stage == "sesudah"]
scan_before = tscan[tscan.stage == "sebelum"]

# ---- pemeriksaan (assert) sebelum menulis
assert (kpi.same).all() and (rk.same_station).all() and par.head(3).same_defect.all()
assert tight.k_min_after >= 5 and tight.pct_unique_after == 0 and tight.pct_unique_before == 1
assert a_hash.recovery_rate == 1 and a_hmac.recovery_rate == 0 and a_guess.recovery_rate == 0
assert rest_allow == 0 and rest_regex > 0 and (scan_after.rows_hit == 0).all()
assert (val.result == "lulus").all() and sec_ok and cx.match.all()
assert nn.persons_with_multiple_codes.iloc[1] == 0 and nn.persons_with_multiple_codes.iloc[0] > 0
assert link.codes_linked_after.iloc[0] == 0 and link.codes_linked_after.iloc[1] > 0
assert gt["worst_station_observed"] == gt["worst_station_planted"] == rk.station_raw.iloc[0]

# ---------------------------------------------------------------- 1. data
kpc = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kpc("navy", I(dbt["raw_production"]), "baris produksi", f"Satu baris = satu stasiun, model, shift, hari; {I(prof['stasiun'])} stasiun, 3 model, 2 shift, {I(prof['hari kerja'])} hari kerja."),
    kpc("amber", I(dbt["raw_defect"]), "baris defect_log", "Jumlah satu kode defect per stasiun, model, shift, hari; dipakai untuk Pareto."),
    kpc("teal", I(n_op), "operator (orang)", f"Ditulis dengan {I(prof['string nama operator berbeda'])} penulisan nama berbeda; {I(prof['baris dengan penulisan nama kotor'])} baris berpenulisan kotor."),
    kpc("plum", I(leak_all), "catatan bebas bocor", f"Memuat nama, telepon, atau customer ({I(leaked_tel)} memuat telepon). Sengaja ditanam."),
    kpc("rose", I(lot_cust), "kode lot memuat customer", "Seluruh baris model khusus. Sengaja ditanam."),
    kpc("sky", I(len(cc)), "kolom diberi kebijakan", f"{I(len(cc[cc.table == 'production']))} kolom produksi dan {I(len(cc[cc.table == 'defect_log']))} kolom defect_log; 5 metode samaran."),
    '</div><h3>1.1 Data simulasi dengan identitas palsu</h3>')
tb11 = [["Nama dan telepon di catatan bebas", f"{I(gt['rows_note_fullname_phone'])} + {I(gt['rows_note_firstname_phone'])} baris",
         I(leaked_tel), "Dua bentuk: nama lengkap + telepon, dan nama depan saja + telepon"],
        ["Nama customer di catatan bebas", I(gt["rows_note_customer"]), I(notes.rows_customer[0]), "Pemindai mencari nama perusahaan"],
        ["Nama customer di kode lot (model khusus)", I(gt["rows_lot_contains_customer"]), I(lot_cust), f"Model {gt['special_model']}: kode lot berawalan nama customer"],
        ["Penulisan nama operator kotor", I(gt["dirty_name_rows"]), I(prof["baris dengan penulisan nama kotor"]), f"Spasi ganda, huruf besar atau kecil; {I(gt['distinct_name_strings'])} penulisan untuk {I(n_op)} orang"],
        ["Satu operator di satu sel stasiun x shift", "1 sel", I(prof["sel dengan satu operator"]) + " sel", f"{gt['singleton_cell']['station']}, {gt['singleton_cell']['shift']}"],
        ["Stasiun paling sering NG", cs(gt["worst_station_planted"]), cs(gt["worst_station_observed"]), "NG rate tertinggi di data, dipakai menguji ranking"]]
rp1 += '<div class="card"><h4>Tabel 1.1a. Kebocoran yang ditanam dan yang ditemukan pemindai</h4>' + table(["Jenis", "Ditanam (ground truth)", "Ditemukan (profil data)", "Keterangan"], tb11) + \
    f'<p>Data dibuat skrip dengan seed tetap (v3). Nama, nomor karyawan, nomor telepon, dan nama customer semuanya palsu (Faker 40.43.0, locale id_ID). Halaman ini tidak menampilkan satu pun nilai identitas; contoh memakai pola.</p></div>'
sm = sample.head(6)
rp1 += '<div class="card"><h4>Tabel 1.1b. Contoh baris data anonim (<code>anonymized_production</code>; kode ditampilkan sebagai pola karena nilainya bergantung pada kunci rahasia)</h4>' + table(
    ["Minggu", "Shift", "Stasiun", "Model", "Kode operator", "Kode lot", "Indeks input", "NG rate", "Catatan"],
    [[r.week, r.shift, cs(r.station), r.model, cs(r.operator_code), cs(r.lot_code), D(r.input_index, 1), P(r.ng_rate, 1), cs(r.note_clean)] for r in sm.itertuples()]) + \
    f'<p>Tanggal sudah menjadi minggu, nama operator menjadi kode, jumlah input menjadi indeks (rata-rata seluruh data = 100), dan kode lot diganti kode acak. Kolom nomor karyawan, nama customer, dan tanggal tidak ada lagi.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>privacy_pipeline.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Objek", "Baris", "Isi"],
    [["raw_production", I(dbt["raw_production"]), "Data asli simulasi dengan identitas palsu; kolom tambahan week dan nama dinormalkan. Tidak di-commit."],
     ["raw_defect", I(dbt["raw_defect"]), "Jumlah per kode defect per stasiun, model, shift, hari. Tidak di-commit."],
     ["anon_production", I(dbt["anon_production"]), "Hasil pipeline: kode operator, kode lot, minggu, indeks."],
     ["anon_defect", I(dbt["anon_defect"]), "Defect dengan minggu dan indeks."],
     ["column_policy", I(dbt["column_policy"]), "Satu baris per kolom: kelas, metode, kolom hasil, alasan (dari <code>column_policy.yaml</code>)."],
     ["v_raw_prod, v_anon_prod, v_raw_defect, v_anon_defect", "4", "View dengan nama kolom sama, sehingga query yang sama persis dijalankan di data asli dan anonim."]]) + \
    '<h4>Tabel 1.2b. Pemeriksaan setelah anonymization</h4>' + table(
    ["Pemeriksaan", "Hasil"],
    [["Identitas tersisa di kolom teks data anonim (baris)", f"{I(scan_after.rows_hit.sum())} {OK('Lulus')}"],
     ["Identitas di data asli sebagai pembanding (baris yang memuat)", I(scan_before.rows_hit.sum())],
     ["k minimum kombinasi terketat ≥ 5", f"{I(tight.k_min_after)} {OK('Lulus')}"],
     ["KPI, 3 stasiun terburuk, 3 defect teratas sama dengan data asli", OK("Lulus")],
     ["Output sama persis pada dua kali jalan dengan kunci yang sama", OK("Lulus")],
     ["Kode lot kembali ke nilai asli (baris)", f"{I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_pass)} dari {I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_tested)} {OK('Lulus')}"],
     ["Berkas rahasia dan identitas di repositori", f"{I(int((sec.result == 'lulus').sum()))} dari {I(len(sec))} pemeriksaan {OK('Lulus')}"],
     ["Cek silang SQL vs pandas", f"{I(ok_cx)} dari {I(len(cx))} {OK('Cocok')}"]]) + '</div>'
FILES = {"column_classification": ("Klasifikasi dan metode per kolom", "Q1"), "data_profile": ("Profil data asli: jumlah, kebocoran, nama kotor", "Data"),
         "name_variants": ("Penulisan nama per orang", "Data"), "anonymize_summary": ("Ringkasan hasil pipeline", "Data"),
         "risk_k_anonymity": ("Baris unik dan k minimum", "Q2"), "risk_dictionary_attack": ("Serangan kamus: hash biasa vs HMAC", "Q3"), "risk_notes": ("Sisa identitas di catatan menurut cara pembersihan", "Q4"),
         "risk_text_scan": ("Pindai semua kolom teks sebelum dan sesudah", "Q4"), "risk_operator_cells": ("Operator per sel stasiun x shift", "Q2, Q8"), "risk_linkage": ("Serangan penyambungan dengan daftar jaga", "Q2, Q8"),
         "utility_kpi": ("KPI asli vs anonim", "Q5"), "utility_station_ranking": ("Ranking NG per stasiun", "Q5"), "utility_pareto": ("Pareto defect", "Q5"),
         "utility_trend": ("Tren dan korelasi", "Q6"), "utility_weekly_yield": ("Yield mingguan asli vs anonim", "Q6"), "granularity_curve": ("Risiko vs utilitas menurut generalisasi", "Q7"),
         "method_tradeoff": ("Trade-off antar metode", "Q8"), "validation_checks": ("Deterministik dan pemulihan mapping key", "Q9, Q12"), "validation_name_normalization": ("Satu orang satu kode", "Q9"),
         "secret_scan": ("Berkas rahasia dan identitas di repositori", "Q12"), "impact_time": ("Waktu pipeline (diukur) dan manual (estimasi)", "Q10, Q11"),
         "impact_scenarios": ("Jam dihemat menurut asumsi", "Q11"), "crosscheck_sql": ("SQL vs pandas pada data asli dan anonim", "Q2, Q5"), "evaluation": ("Satu tabel ukuran sebelum dan sesudah", "Q2 sampai Q12")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard dan notebook.</p></div>'
mins_after = auto_s / 60
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima ukuran kinerja (definisi di <code>project/docs/metrics.md</code>)</h4>' + table(
    ["Ukuran", "Sebelum", "Sesudah", "Keterangan"],
    [["Baris unik (kombinasi terketat)", P(tight.pct_unique_before, 0), P(tight.pct_unique_after, 0), "Tanggal/minggu + shift + stasiun + model + operator"],
     ["k minimum", I(tight.k_min_before), I(tight.k_min_after), "Target rancangan minimal 5"],
     ["Kecocokan KPI", "-", "Sama persis", f"Yield lini {P(y_raw, 1)}, 3 stasiun terburuk, 3 defect teratas; selisih terbesar di bawah {D(0.000001, 6)}"],
     ["Informasi yang hilang", "-", f"{I(tr.raw.iloc[7])} menjadi {I(tr.anon.iloc[7])} titik tren", f"Juga {I(summ['catatan dihapus'])} catatan bebas dan kode operator pada {I(masked_rows)} baris"],
     ["Menit per file", f"{I(manual_min)} menit (asumsi)", f"{I(auto_s)} detik (terukur)", "Dibulatkan ke atas"]]) + \
    f'<p>Contoh pada halaman Design (baris unik, k, titik data) memakai angka karangan, bukan hasil data ini.</p></div>'

# ---------------------------------------------------------------- 2. business questions
cls_lab = {"direct": "Identitas langsung", "quasi": "Quasi-identifier", "sensitive": "Sensitif", "safe": "Aman"}
cc_p = cc[cc.table == "production"]
ccount = cc_p["class"].value_counts()
met_lab = {"pseudonymize": "Pseudonymization (HMAC)", "mapping_key": "Mapping key", "generalize": "Generalisasi", "scale": "Skala angka", "drop": "Hapus", "clean_text": "Bersihkan teks (allowlist)", "keep": "Dibiarkan"}
s21 = mk('<h3 id="sec21">2.1 Klasifikasi kolom <span class="qlist">Q1</span></h3><div class="card">',
         Q(1, f"Dari {I(len(cc_p))} kolom tabel produksi: {I(ccount['direct'])} identitas langsung (nomor karyawan, nama operator, kode lot, nama customer), {I(ccount['quasi'])} quasi-identifier (tanggal, shift, stasiun, model), "
              f"{I(ccount['sensitive'])} sensitif (jumlah input, jumlah NG, catatan bebas), dan tidak ada yang aman di tabel produksi. Di tabel defect_log hanya kode defect yang aman. "
              f"Kode lot ditetapkan sebagai identitas langsung karena pada model khusus awalannya adalah nama customer ({I(lot_cust)} baris). Setiap kolom punya satu metode dan alasan di <code>column_policy.yaml</code>."),
         '<h4>Grafik 2.1a. Kolom tabel produksi menurut kelas</h4>',
         bars([(cls_lab[c], int(ccount.get(c, 0)), col, f"{cls_lab[c]}: {I(ccount.get(c, 0))} kolom") for c, col in (("direct", HI), ("quasi", BLUE), ("sensitive", GREY), ("safe", SOFT))], lambda v: I(v), "Kolom menurut kelas", rot=0, small=True),
         '<h4>Tabel 2.1b. Kebijakan per kolom (tabel produksi)</h4>',
         table(["Kolom", "Kelas", "Metode", "Kolom hasil", "Alasan"], [[f"<code>{r.column}</code>", cls_lab[r._3], met_lab[r.method], f"<code>{r.output}</code>" if r.output != "(dihapus)" else "dihapus", cs(r.why)] for r in cc_p.itertuples()]),
         f'<p>Tabel defect_log memakai kelas yang sama: tanggal menjadi minggu, jumlah menjadi indeks, kode defect dibiarkan. Sel stasiun x shift yang dikerjakan satu orang menutup kode operatornya (aturan tambahan di luar kolom).</p></div>')
bt = lambda vals: [(r.combo.replace(" (terketat)", ""), r.pct_unique_before, r.pct_unique_after) for r in k.itertuples()]
cell_row = lambda: f"{cs(one_cell.station)}, {one_cell['shift']}"
s22 = mk('<h3 id="sec22">2.2 Risiko identifikasi ulang <span class="qlist">Q2, Q3, Q4</span></h3><div class="card">',
         Q(2, f"Pada kombinasi terketat (tanggal, shift, stasiun, model, operator), {P(tight.pct_unique_before, 0)} baris unik di data asli; sesudah tanggal menjadi minggu dan nama menjadi kode, {P(tight.pct_unique_after, 0)} baris unik dan k minimum {I(tight.k_min_after)} (target minimal {I(5)}). "
              f"Nilai k sama dengan jumlah hari kerja dalam satu minggu karena satu baris per hari per kombinasi dan operator bergilir tiap minggu. Catatan: k hanya mengukur kombinasi yang dipilih. Satu sel yang dikerjakan satu orang ({cell_row()}) menunjuk orangnya langsung dari stasiun dan shift, jadi kode operator di {I(masked_rows)} baris sel itu ditutup. "
              f"Pihak yang memegang daftar jaga mingguan lengkap masih bisa menyambungkan {I(link.codes_linked_after[1])} dari {I(link.operators[1])} kode ke orangnya ({P(link.rate_after[1], 1)}); k tidak mengukur serangan semacam ini.", warn=True),
         Q(3, f"Tidak, selama memakai kunci. Penyerang yang memegang {I(a_hash.candidates)} nama kandidat (nama umum ditambah seluruh nama karyawan) memulihkan {P(a_hash.recovery_rate, 0)} nama dari hash SHA-256 tanpa kunci, tetapi {P(a_hmac.recovery_rate, 0)} dari kode HMAC dengan kunci rahasia, "
              f"baik dengan hash biasa maupun dengan {I(6)} kunci tebakan yang umum. Ini berlaku selama kunci panjang dan acak; kunci yang bisa ditebak membuat HMAC sama lemahnya dengan hash biasa."),
         Q(4, f"Tidak, dengan cara allowlist. Dari {I(n_case_rows)} catatan, {I(leak_all)} memuat nama, telepon, atau customer. Pembersihan regex (telepon, nama lengkap, dan customer yang dikenal) masih menyisakan {I(rest_regex)} catatan karena nama depan saja atau penulisan lain lolos. "
              f"Allowlist (hanya frasa aman yang dipertahankan) menyisakan {I(rest_allow)}, dengan harga {I(summ['catatan dihapus'])} catatan ({P(summ['catatan dihapus'] / n_case_rows, 1)}) berubah menjadi [dihapus]. Catatan: pemindai mencari nama yang ada di daftar karyawan dan customer, jadi nama orang di luar daftar tidak akan ditemukan; allowlist tetap aman karena menolak semua teks yang tidak dikenal.", warn=True),
         '<h4>Grafik 2.2a. Baris unik menurut kombinasi quasi-identifier</h4>',
         gbars([c for c, _, _ in bt(0)], [("Data asli (tanggal harian)", GREY, [b for _, b, _ in bt(0)]), ("Data anonim (minggu)", BLUE, [a for _, _, a in bt(0)])], lambda v: P(v, 0), "Baris unik sebelum dan sesudah", rot=0, h=260),
         legend([(GREY, "Data asli, tanggal harian"), (BLUE, "Data anonim, mingguan")]),
         '<h4>Tabel 2.2b. Baris unik dan k minimum</h4>',
         table(["Kombinasi", "Kolom", "Baris unik sebelum", "k sebelum", "Baris unik sesudah", "k sesudah", "k ≥ 5"],
               [[r.combo, cs(r.columns), P(r.pct_unique_before, 0), I(r.k_min_before), P(r.pct_unique_after, 0), I(r.k_min_after), OK("Ya") if r.k_target_met else NO("Tidak")] for r in k.itertuples()]),
         '<h4>Grafik 2.2c. Operator yang namanya pulih lewat serangan kamus</h4>',
         hbars([(lab, r.recovery_rate, HI if r.recovery_rate > 0 else BLUE, f"{lab}: {I(r.recovered)} dari {I(r.operators_attacked)}")
                for r, lab in zip(att.itertuples(), ["SHA-256 tanpa kunci", "HMAC, serang dengan hash biasa", "HMAC, tebak kunci umum"])], lambda v: P(v, 0), "Pemulihan nama oleh serangan kamus", 1.05),
         '<h4>Tabel 2.2d. Serangan kamus</h4>',
         table(["Skema", "Kandidat dicoba", "Operator diserang", "Nama pulih", "Tingkat pulih"], [[cs(r.scheme), I(r.candidates), I(r.operators_attacked), I(r.recovered), P(r.recovery_rate, 0)] for r in att.itertuples()]),
         '<h4>Tabel 2.2e. Catatan bebas menurut cara pembersihan</h4>',
         table(["Cara", "Catatan", "Memuat identitas", "Telepon", "Nama", "Customer", "Teks tidak berubah"],
               [[cs(r.method), I(r.rows), I(r.rows_with_identity), I(r.rows_phone), I(r.rows_name), I(r.rows_customer), I(r.rows_text_unchanged)] for r in notes.itertuples()]),
         '<h4>Tabel 2.2f. Risiko yang tersisa setelah anonymization</h4>',
         table(["Pengetahuan penyerang", "Operator", "Kode tersambung sebelum", "Kode tersambung sesudah"],
               [[cs(r.attacker_knowledge), I(r.operators), f"{I(r.codes_linked_before)} ({P(r.rate_before, 0)})", f"{I(r.codes_linked_after)} ({P(r.rate_after, 0)})"] for r in link.itertuples()]),
         f'<p>Pindai semua kolom teks data anonim: {I(scan_after.rows_hit.sum())} baris memuat nomor telepon, nomor karyawan, nama, atau customer (data asli: {I(scan_before.rows_hit.sum())} baris). Kode HMAC memakai {I(8)} karakter hex; nama dinormalkan lebih dulu sehingga satu orang satu kode (Q9).</p></div>')
s23 = mk('<h3 id="sec23">2.3 Utilitas: apakah analisis tetap sama <span class="qlist">Q5, Q6</span></h3><div class="card">',
         Q(5, f"Ya. Yield lini {P(y_raw, 2)} di data asli dan {P(y_anon, 2)} di data anonim; selisih terbesar dari {I(len(kpi))} KPI (yield lini, per model, per shift, NG rate {I(len(rk))} stasiun) di bawah {D(0.000001, 6)}, yang berasal dari pembulatan indeks. "
              f"Tiga stasiun terburuk sama dan berurutan sama ({cs(rk.station_raw[0])}, {cs(rk.station_raw[1])}, {cs(rk.station_raw[2])}), seluruh urutan {I(len(rk))} stasiun sama, dan tiga defect teratas sama ({', '.join(par.defect_raw[:3])}; {cs(par.defect_name[0])} {P(par.share_raw[0], 1)} dari semua defect)."),
         Q(6, f"Hampir tidak berubah, kecuali resolusi waktu. Kemiringan tren yield mingguan {D(slope_r, 3)} poin persentase per minggu di kedua data. Kemiringan dari deret harian (dikali 5) {D(tr.raw.iloc[1], 3)}, selisih {D(abs(tr.raw.iloc[1] - slope_a), 3)} poin. "
              f"Korelasi input dan NG per baris {D(tr.raw.iloc[3], 3)} di kedua data (skala linear tidak mengubah korelasi). Yang hilang adalah rentang harian: yield terendah harian {P(tr.raw.iloc[5], 1)} dan tertinggi {P(tr.raw.iloc[6], 1)}, sedangkan deret mingguan hanya {P(tr.anon.iloc[5], 1)} sampai {P(tr.anon.iloc[6], 1)}; titik waktu turun dari {I(tr.raw.iloc[7])} ke {I(tr.anon.iloc[7])}."),
         '<h4>Grafik 2.3a. Yield lini mingguan: data asli dan anonim</h4>',
         lines([WK(w) for w in wy.week], [("Data asli", GREY, 5, list(wy.yield_raw)), ("Data anonim", BLUE, 2, list(wy.yield_anon))], lambda v: P(v, 1), "Yield mingguan asli dan anonim"),
         legend([(GREY, "Data asli"), (BLUE, "Data anonim (garis menimpa data asli)")]),
         '<h4>Tabel 2.3b. KPI: data asli vs anonim</h4>',
         table(["KPI", "Data asli", "Data anonim", "Selisih", "Sama"], [[cs(r.kpi), P(r.raw, 3), P(r.anon, 3), "di bawah " + D(0.000001, 6) if r.abs_diff < 1e-6 else D(r.abs_diff, 6), OK("Ya") if r.same else NO("Tidak")] for r in kpi.itertuples()]),
         '<h4>Tabel 2.3c. Ranking NG per stasiun</h4>',
         table(["Peringkat", "Stasiun (asli)", "NG rate (asli)", "Stasiun (anonim)", "NG rate (anonim)", "Sama"], [[I(r.rank), cs(r.station_raw), P(r.ng_rate_raw, 2), cs(r.station_anon), P(r.ng_rate_anon, 2), OK("Ya") if r.same_station else NO("Tidak")] for r in rk.itertuples()]),
         '<h4>Grafik 2.3d. Pareto defect, 12 kode teratas (data anonim)</h4>',
         pareto_svg(list(par.defect_anon[:12]), list(par.share_anon[:12]), list(par.share_anon.cumsum()[:12]), [c <= 0.5 for c in par.share_anon.cumsum()[:12]],
                    [f"{r.defect_anon} {cs(r.defect_name)}: {P(r.share_anon, 1)}, peringkat sama dengan data asli: {'ya' if r.same_defect else 'tidak'}" for r in par[:12].itertuples()], "Pareto defect data anonim"),
         legend([(BLUE, "Sampai kumulatif 50%"), (SOFT, "Lainnya")]),
         '<h4>Tabel 2.3e. Tren dan korelasi</h4>',
         table(["Ukuran", "Asli", "Anonim"], [[cs(r.metric), D(r.raw, 3) if r.raw != int(r.raw) or r.raw < 5 else I(r.raw), D(r.anon, 3) if r.anon != int(r.anon) or r.anon < 5 else I(r.anon)] for r in tr.itertuples()]),
         '<p>Pareto data anonim memakai jumlah dalam indeks; yang dibandingkan adalah peringkat dan porsi. Kolom asli pada baris korelasi bernilai 1,0 menurut definisi.</p></div>')
s24 = mk('<h3 id="sec24">2.4 Tingkat generalisasi <span class="qlist">Q7</span></h3><div class="card">',
         Q(7, f"Mingguan: tingkat terendah (paling halus) yang memenuhi k ≥ 5 ({I(gr.loc['Mingguan'].k_min)}), dengan korelasi tren penuh ({D(gr.loc['Mingguan'].trend_corr_weekly, 2)}). Harian terlalu berisiko ({P(gr.loc['Harian'].pct_unique, 0)} baris unik). Tingkat yang lebih kasar tidak menaikkan k pada kombinasi terketat, karena operator bergilir mingguan, "
              f"tetapi menurunkan utilitas: korelasi tren dua mingguan {D(gr.loc['Dua mingguan'].trend_corr_weekly, 2)}, bulanan {D(gr.loc['Bulanan'].trend_corr_weekly, 2)}. Kesimpulan ini bergantung pada pola gilir operator data simulasi; pada data lain k perlu dihitung ulang.", warn=True),
         '<h4>Grafik 2.4a. k minimum menurut tingkat generalisasi (oranye: di bawah target 5)</h4>',
         bars([(r.Index, r.k_min, BLUE if r.k_target_met else HI, f"{r.Index}: k minimum {I(r.k_min)}, {I(r.time_points)} titik waktu") for r in gran.set_index("granularity").itertuples()], lambda v: I(v), "k minimum menurut generalisasi", rot=0, small=True),
         '<h4>Grafik 2.4b. Korelasi tren dengan deret mingguan asli (utilitas)</h4>',
         bars([(r.Index, r.trend_corr_weekly, BLUE if r.trend_corr_weekly >= 0.95 else SOFT, f"{r.Index}: korelasi {D(r.trend_corr_weekly, 2)}") for r in gran.set_index("granularity").itertuples()], lambda v: D(v, 1), "Korelasi tren menurut generalisasi", rot=0, small=True, ymax=1.0),
         '<h4>Tabel 2.4c. Risiko dan utilitas menurut tingkat generalisasi</h4>',
         table(["Generalisasi", "Titik waktu", "Baris unik", "k minimum", "k median", "Korelasi tren", "Galat yield maksimum", "k ≥ 5"],
               [[r.granularity, I(r.time_points), P(r.pct_unique, 0), I(r.k_min), I(r.k_median), D(r.trend_corr_weekly, 2), P(r.max_abs_error_yield, 2), OK("Ya") if r.k_target_met else NO("Tidak")] for r in gran.itertuples()]),
         '<p>Dihitung pada kombinasi terketat. Korelasi tren: yield tiap minggu diganti nilai periode tempat minggu itu berada, lalu dikorelasikan dengan deret mingguan asli.</p></div>')
def fmt_trade(r, col):
    v, m = getattr(r, col), r.risk_measure if col.startswith("risk") else r.utility_measure
    if "(poin)" in m:
        return "di bawah " + D(0.000001, 6)
    if "(rasio" in m:
        return P(v, 1 if 0 < v < 0.1 else 0)
    return I(v)
s25 = mk('<h3 id="sec25">2.5 Metode, trade-off, dan deterministik <span class="qlist">Q8, Q9</span></h3><div class="card">',
         Q(8, f"Tiap tipe kolom punya metode berbeda (Tabel 2.5a). Nama operator: HMAC dengan kunci, karena hash biasa dipecahkan {P(a_hash.recovery_rate, 0)}. Kode lot: mapping key, karena harus bisa dibalik oleh pemilik data. Tanggal: minggu. Jumlah: indeks, tetapi ini bukan pengaman penuh, "
              f"sebab bila satu nilai asli diketahui, {P(trade.risk_after[4], 0)} nilai lain terhitung. Teks bebas: allowlist, bukan regex. Sel dengan satu operator: tutup kodenya. Setiap metode mengorbankan sesuatu yang berbeda: kemampuan analisis per customer, resolusi harian, atau {P(summ['catatan dihapus'] / n_case_rows, 1)} catatan."),
         Q(9, f"Ya. Dua kali jalan dengan kunci yang sama menghasilkan file anonim dengan SHA-256 yang sama ({I(val[val.check.str.startswith('Output sama persis')].n_pass.iloc[0])} dari {I(val[val.check.str.startswith('Output sama persis')].n_tested.iloc[0])} file) dan mapping key yang sama. "
              f"Dengan kunci lain, seluruh {I(val[val.check.str.contains('Kode operator berubah')].n_tested.iloc[0])} kode operator berubah tetapi yield lini tetap sama. Syaratnya kunci sama: pengguna yang mengganti kunci mendapat kode berbeda, jadi kunci satu periode berbagi harus disimpan."),
         '<h4>Tabel 2.5a. Trade-off tiap metode (termasuk dua pembanding)</h4>',
         table(["Metode", "Kolom", "Ukuran risiko", "Sebelum", "Sesudah", "Ukuran utilitas", "Nilai", "Bisa dibalik", "Kelemahan"],
               [[cs(r.method), f"<code>{r.applied_to}</code>", cs(r.risk_measure), fmt_trade(r, "risk_before"), fmt_trade(r, "risk_after"), cs(r.utility_measure), fmt_trade(r, "utility_value"), cs(r.reversible), cs(r.weakness)] for r in trade.itertuples()]),
         '<h4>Tabel 2.5b. Satu orang satu kode: normalisasi nama</h4>',
         table(["Skema", "Kode berbeda", "Orang", "Orang dengan lebih dari satu kode", "Kode terbanyak per orang"], [[cs(r.scheme), I(r.distinct_codes), I(r.persons), I(r.persons_with_multiple_codes), I(r.max_codes_per_person)] for r in nn.itertuples()]),
         '<h4>Tabel 2.5c. Uji deterministik (Q9)</h4>',
         table(["Pemeriksaan", "Diuji", "Lulus", "Hasil"], [[cs(r.check), I(r.n_tested), I(r.n_pass), OK("Lulus") if r.result == "lulus" else NO("Gagal")] for r in val[val.question == "Q9"].itertuples()]),
         f'<p>Tanpa normalisasi, {I(nn.persons_with_multiple_codes[0])} dari {I(nn.persons[0])} orang mendapat lebih dari satu kode (sampai {I(nn.max_codes_per_person[0])}) karena penulisan nama kotor; analisis per operator akan keliru. Dua metode pembanding (hash biasa, regex) ditampilkan agar jelas apa yang dibeli oleh metode terpilih.</p></div>')
s26 = mk('<h3 id="sec26">2.6 Waktu yang dihemat <span class="qlist">Q10, Q11</span></h3><div class="card">',
         Q(10, f"Sekitar {I(manual_min)} menit anonymization manual di Excel per file digantikan pipeline yang berjalan {I(auto_s)} detik (median {I(7)} kali jalan, dibulatkan ke atas), jadi {D(imp.loc['Menit yang digantikan per file'].value, 0)} menit per file. Angka manual adalah asumsi penulis, bukan hasil stopwatch; "
               f"waktu pipeline diukur.", warn=True),
         Q(11, f"Sekitar {D(saved_h, 0)} jam kerja per tahun (estimated), dihitung {I(files_yr)} file per tahun × {D(imp.loc['Menit yang digantikan per file'].value, 0)} menit ÷ 60. Bila waktu manual sebenarnya {I(isc.manual_minutes_per_file.min())} sampai {I(isc.manual_minutes_per_file.max())} menit dan file yang dibagikan {I(isc.files_per_year.min())} sampai {I(isc.files_per_year.max())} per tahun, "
               f"hasilnya {D(isc.hours_saved_per_year.min(), 0)} sampai {D(isc.hours_saved_per_year.max(), 0)} jam per tahun (Tabel 2.6b). Belum termasuk risiko yang dihindari (kolom yang terlewat).", warn=True),
         '<h4>Tabel 2.6a. Waktu per file</h4>',
         table(["Ukuran", "Nilai", "Satuan", "Label"], [[cs(i), D(r.value, 1) if r.value != int(r.value) else I(r.value), r.unit, cs(r.label)] for i, r in imp.iterrows()]),
         '<h4>Tabel 2.6b. Jam dihemat per tahun menurut asumsi (estimated)</h4>',
         table(["Waktu manual per file (menit)", "File per tahun", "Jam dihemat per tahun"], [[I(r.manual_minutes_per_file), I(r.files_per_year), D(r.hours_saved_per_year, 1)] for r in isc.itertuples()]),
         '<p>Semua angka dampak berlabel estimated. Dampak dalam rupiah tidak dihitung.</p></div>')
rec = val[val.question == "Q12"]
s27 = mk('<h3 id="sec27">2.7 Pemulihan mapping key dan keamanan repositori <span class="qlist">Q12</span></h3><div class="card">',
         Q(12, f"Ya. Pemegang mapping key mengembalikan kode lot ke nilai asli pada {I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_pass)} dari {I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_tested)} baris ({P(1, 0)}), kode operator ke nomor karyawan pada {I(vq.loc['Kode operator terlihat dikembalikan ke nomor karyawan asli (baris)'].n_pass)} baris yang kodenya terlihat, "
               f"dan jumlah asli dari indeks pada seluruh {I(vq.loc['Indeks produksi dikembalikan ke jumlah asli dengan nilai dasar (baris x kolom)'].n_pass)} nilai produksi dan {I(vq.loc['Indeks defect dikembalikan ke jumlah asli (baris)'].n_pass)} baris defect. "
               f"Kode operator di sel satu orang ({I(masked_rows)} baris) sengaja tidak bisa dipulihkan. Lot lama tetap memakai kode lama saat file baru ditambahkan. Pemindaian repositori: {I(int((sec.result == 'lulus').sum()))} dari {I(len(sec))} pemeriksaan lulus, termasuk riwayat commit semua cabang.", ),
         '<h4>Tabel 2.7a. Uji pemulihan (Q12)</h4>',
         table(["Pemeriksaan", "Diuji", "Lulus", "Hasil"], [[cs(r.check), I(r.n_tested), I(r.n_pass), OK("Lulus") if r.result == "lulus" else NO("Gagal")] for r in rec.itertuples()]),
         '<h4>Tabel 2.7b. Pemindaian berkas rahasia dan identitas di repositori</h4>',
         table(["Pemeriksaan", "Cakupan", "Temuan", "Hasil"], [[cs(r.check), cs(r.scope), I(r.hits), OK("Lulus") if r.result == "lulus" else NO("Gagal")] for r in sec.itertuples()]),
         '<h4>Tabel 2.7c. Cek silang SQL (DuckDB) vs pandas pada data asli dan anonim</h4>',
         table(["Pemeriksaan", "Data", "SQL", "pandas", "Cocok"], [[cs(r.check), r.dataset, D(r.sql, 4) if abs(r.sql) < 100 else I(r.sql), D(r.pandas, 4) if abs(r.pandas) < 100 else I(r.pandas), OK("Ya") if r.match else NO("Tidak")] for r in cx.itertuples()]),
         '<p>Kunci HMAC dan mapping key ada di <code>project/data/private/</code> yang masuk <code>.gitignore</code>; kunci dibaca dari environment <code>ANON_HMAC_KEY</code> bila ada. Data asli, data anonim, dan database juga tidak di-commit. Cek silang memakai query yang sama pada view data asli dan data anonim.</p></div>')
SEC = {1: "21", 2: "22", 3: "22", 4: "22", 5: "23", 6: "23", 7: "24", 8: "25", 9: "25", 10: "26", 11: "26", 12: "27"}
rp2_body = mk(s21, s22, s23, s24, s25, s26, s27)
qn_all = sorted(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body))
assert qn_all == list(range(1, 13)), qn_all
npr = {k_: sum(1 for v in PRIO.values() if v == k_) for k_ in ("Utama", "Pendukung", "Tambahan")}
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = mk('<div class="qchips">', "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 13)), '</div>')
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per tabel atau grafik bukti (2.1 sampai 2.7). Catatan kuning pada dasarnya dua hal: ukuran risiko hanya mencakup serangan yang diuji, dan angka dampak memakai asumsi.</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
CODE_REL = "project/code/"
npy = len(list((REPO / CODE_REL).rglob("*.py")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / CODE_REL).rglob("*.py"))
nsql = len(list((REPO / CODE_REL).rglob("*.sql")))
ntest_files = len(list((REPO / "project/tests").glob("test_*.py")))
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan: lima tabel, lima fakta tertanam, dan ukuran yang diperkirakan. Perbedaannya: jumlah operator lebih banyak dari perkiraan, '
         'ditambah tabel defect_log (diperlukan untuk Pareto) dan beberapa kolom tambahan pada data anonim, dan contoh tabel Design memakai nama stasiun karangan. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, <code>scripts/generate_data.py</code>, Faker, versi v1 (rancangan)", f"<code>01_generate_data.py</code>, seed tetap, Faker 40.43.0 (id_ID); naik ke v3 karena rancangan memerlukan operator bergilir, sel satu orang, lot berawalan customer, dan data kotor", PART("Sesuai + penyesuaian")],
             ["Ukuran", "10 stasiun, 3 model, 2 shift, ±25 operator, ±75 hari, ±4.500 baris", f"{I(prof['stasiun'])} stasiun, 3 model, 2 shift, {I(n_op)} operator, {I(prof['hari kerja'])} hari kerja, {I(prof['baris produksi'])} baris", PART("Sesuai + penyesuaian")],
             ["raw_production", "date, shift, station, model, operator_name, employee_id, lot_no, customer_name, input_qty, ng_qty, note", f"Sebelas kolom persis itu. File <code>production_identified.csv</code>, {I(prof['baris produksi'])} baris", OK("Sesuai")],
             ["column_policy", "column, class, method, params", f"<code>column_policy.yaml</code> ({I(len(cc))} kolom, dengan alasan) dan tabel <code>column_policy</code> di DuckDB", OK("Sesuai")],
             ["anonymized_production", "week, shift, station, model, operator_code, lot_code, input_index, ng_rate", "Delapan kolom itu, ditambah <code>ng_index</code> (dibutuhkan untuk yield lini dan Pareto) dan <code>note_clean</code> (untuk menguji catatan bebas)", PART("Sesuai + penyesuaian")],
             ["mapping_key", "column, code, original_value, created_at", f"Keempat kolom itu; berisi kode lot ({I(summ['lot di mapping key'])}), kode operator, dan nilai dasar indeks. Disimpan di <code>data/private/</code>, tidak di-commit", OK("Sesuai")],
             ["evaluation", "metric, scope, before, after, method_set", f"Kelima kolom itu, {I(len(ev))} ukuran", OK("Sesuai")],
             ["defect_log", "Tidak disebut sebagai tabel; Pareto defect ada di KPI", f"<code>defect_log.csv</code> ({I(prof['baris defect_log'])} baris) dan versi anonimnya, agar 3 defect teratas bisa dibandingkan", PART("Tambahan")],
             ["Fakta 1", "Satu operator sendirian di shift malam pada satu stasiun", f"{cs(gt['singleton_cell']['station'])}, {gt['singleton_cell']['shift']}: {I(prof['sel dengan satu operator'])} dari {I(prof['sel stasiun x shift'])} sel hanya punya satu operator", OK("Sesuai")],
             ["Fakta 2", "Nama operator dan telepon di catatan bebas pada ±2% baris", f"{I(leaked_tel)} baris ({P(leaked_tel / n_case_rows, 1)}) memuat nama dan telepon; ditambah {I(gt['rows_note_customer'])} yang memuat nama customer", OK("Sesuai")],
             ["Fakta 3", "Nama customer muncul di kode lot pada beberapa model khusus", f"Satu model khusus ({gt['special_model']}): {I(lot_cust)} baris", OK("Sesuai")],
             ["Fakta 4", "Satu stasiun paling sering NG, untuk menguji ranking", f"{cs(gt['worst_station_planted'])}: NG rate {P(rk.ng_rate_raw[0], 2)}, hampir dua kali stasiun peringkat dua ({P(rk.ng_rate_raw[1], 2)})", OK("Sesuai")],
             ["Fakta 5", "2–3% data kotor: nama dengan spasi ekstra atau huruf besar-kecil berbeda, bisa membuat dua kode", f"{I(prof['baris dengan penulisan nama kotor'])} baris ({P(prof['baris dengan penulisan nama kotor'] / prof['baris produksi'], 1)}); tanpa normalisasi {I(nn.persons_with_multiple_codes[0])} dari {I(nn.persons[0])} orang mendapat lebih dari satu kode", OK("Sesuai")],
             ["Contoh tabel anonymized_production", "Baris contoh dengan stasiun \"Roller Test\" dan shift 1 atau 2", "Contoh itu karangan. Data memakai Performance Test (Dyno), Shift 1 dan Shift 2", PART("Berubah")],
             ["Lisensi", "Tidak memakai data publik atau data perusahaan", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools utama dipakai. Perbedaannya: kunci HMAC dibaca dari environment atau file di folder private (bukan file <code>.env</code>), dashboard belum di-deploy, dan ditambah PyYAML, Jupyter, dan DuckDB untuk cek silang.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas, hashlib/hmac)", "Kebijakan per kolom: HMAC-SHA256, generalisasi tanggal, skala angka, pembersihan teks; kunci dari environment", f"<code>pipeline/anonymize.py</code> dan <code>pipeline/scan.py</code>; {I(npy)} skrip dan modul, {I(loc)} baris. Kunci dari <code>ANON_HMAC_KEY</code> atau <code>data/private/hmac_key.txt</code> (dibuat acak bila belum ada)", OK("Sesuai")],
             ["Faker", "Nama, nomor karyawan, nomor telepon, nama customer palsu", "Faker 40.43.0, locale id_ID, seed tetap; nomor karyawan dibuat berurutan, bukan oleh Faker", PART("Sesuai + penyesuaian")],
             ["DuckDB + SQL", "KPI, ranking, Pareto pada data asli dan anonim; baris unik per kombinasi QI", f"<code>privacy_pipeline.duckdb</code>; {I(nsql)} file SQL; view dengan kolom sama sehingga query yang sama persis dipakai di keduanya; hasil dicek silang dengan pandas ({I(ok_cx)} dari {I(len(cx))} cocok)", OK("Sesuai")],
             ["pytest", "Tidak ada nama asli tersisa, deterministik, mapping key bisa dipulihkan", f"{I(ntest_files)} berkas tes, {I(n_tests)} tes lulus: kebocoran, deterministik, pemulihan lot, k minimum, kebijakan menutupi semua kolom, jalur rahasia di-ignore git", OK("Sesuai")],
             ["Streamlit + Plotly", "Dashboard data asli vs anonim, kurva risiko vs utilitas dengan slider, tabel trade-off; link publik", "<code>streamlit/app.py</code>, 3 halaman, slider tingkat generalisasi; diuji dengan <code>AppTest</code>; belum di-deploy. Dashboard hanya membaca CSV ringkas, bukan data asli", PART("Sebagian")],
             ["GitHub + Markdown", "Kode, kebijakan kolom, README; .gitignore mencegah data asli dan mapping key ikut", f"Struktur, README, dan <code>.gitignore</code> siap; pemindaian riwayat: {I(int((sec.result == 'lulus').sum()))} dari {I(len(sec))} pemeriksaan lulus. Di branch <code>project-24-build</code>, belum digabung ke <code>main</code>", PART("Sebagian")],
             ["PyYAML, Jupyter", "Tidak disebut (YAML untuk kebijakan kolom disebut)", "Kebijakan dibaca dengan PyYAML; <code>analysis.ipynb</code> dieksekusi tanpa error", PART("Tambahan")]]))
steps = [("1", "Mengklasifikasi kolom", "<code>docs/column_classification.md</code>, <code>02_profile_columns.py</code>", OK("Sesuai"), ""),
         ("2", "Menyusun kebijakan dan ukuran evaluasi", "<code>config/column_policy.yaml</code>, <code>docs/metrics.md</code>", OK("Sesuai"), ""),
         ("3", "Membuat data simulasi dengan identitas palsu", "<code>01_generate_data.py</code>, <code>ground_truth.json</code>", PART("Sesuai + penyesuaian"), "Generator naik v1 ke v3 agar kelima fakta tertanam; ditambah defect_log."),
         ("4", "Merapikan identitas", "<code>normalize_name()</code> di <code>anonymize.py</code>", OK("Sesuai"), "Normalisasi dilakukan di dalam pipeline, sebelum HMAC, bukan sebagai file bersih terpisah."),
         ("5", "Mengamankan kunci dan file rahasia", "<code>.gitignore</code>, <code>get_key()</code>, <code>10_secret_scan.py</code>", PART("Sesuai + penyesuaian"), "Kunci dari environment atau <code>data/private/hmac_key.txt</code>, bukan <code>.env</code>; diuji tes git check-ignore dan pemindaian riwayat."),
         ("6", "Membangun pipeline anonymization", "<code>pipeline/anonymize.py</code>, <code>03_anonymize.py</code>", OK("Sesuai"), ""),
         ("7", "Menguji risiko identifikasi ulang", "<code>05_risk_assessment.py</code>", PART("Sesuai + tambahan"), "Ditambah risiko sisa: sel operator tunggal dan serangan penyambungan dengan daftar jaga."),
         ("8", "Menguji utilitas analisis", "<code>06_utility_tests.py</code>, <code>07_granularity_curve.py</code>", OK("Sesuai"), ""),
         ("9", "Membandingkan metode dan uji deterministik", "<code>08_method_tradeoff.py</code>, <code>09_validation.py</code>", PART("Sesuai + tambahan"), "Ditambah dua metode pembanding (hash biasa, regex)."),
         ("10", "Menguji pemulihan dan menghitung dampak", "<code>09_validation.py</code>, <code>11_impact.py</code>", OK("Sesuai"), "Waktu manual adalah asumsi."),
         ("11", "Membuat dashboard perbandingan", "<code>streamlit/app.py</code>, <code>14_build_dashboard_data.py</code>", PART("Sebagian"), "Belum di-deploy."),
         ("12", "Menulis README, rekomendasi, dan finalisasi", "<code>README.md</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
renames = [("scripts/generate_data.py", CODE_REL + "1-data-preparation/python/01_generate_data.py"), ("pipeline/anonymize.py", CODE_REL + "1-data-preparation/python/pipeline/anonymize.py"),
           ("config/column_policy.yaml", "project/config/column_policy.yaml"), ("docs/column_classification.md", "project/docs/column_classification.md"), ("docs/metrics.md", "project/docs/metrics.md"),
           ("data/ground_truth.json", "project/data/ground_truth.json"), ("tests/test_anonymize.py", "project/tests/test_anonymize.py"), ("outputs/evaluation.csv", "project/results/2-analysis/evaluation.csv"),
           ("notebooks/analysis.ipynb", "project/results/3-presentation/analysis.ipynb"), ("dashboard/app.py", CODE_REL + "3-presentation/streamlit/app.py"), ("requirements.txt", "project/requirements.txt"),
           ("data/raw/*.csv", "project/data/raw (tidak di-commit)"), ("data/private/mapping_key.csv", "project/data/private/mapping_key.csv (tidak di-commit)"), ("data/anonymized/*.csv", "project/data/anonymized (tidak di-commit)"),
           (".env", "env ANON_HMAC_KEY atau project/data/private/hmac_key.txt (tidak di-commit)"),
           ("(tidak ada)", ", ".join((CODE_REL + "2-analysis/python/analysis_lib.py", CODE_REL + "1-data-preparation/python/pipeline/scan.py", CODE_REL + "common.py", "project/docs/how_to_use.md")))]
for a_, b_ in renames:
    for part in b_.split(", "):
        if "(tidak di-commit)" in part or "env " in part:
            continue
        part = part.split(" (")[0]
        assert (REPO / part).exists(), part
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Dua langkah baru sebagian (dashboard belum di-deploy, finalisasi menunggu merge); langkah lain sesuai, dengan beberapa penyesuaian dan tambahan.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [list(s) for s in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         f'<li>Generator dinaikkan ke v3: operator bergilir tiap minggu kecuali satu sel, lot model khusus berawalan nama customer, nama operator ditulis kotor pada sebagian baris, dan nomor karyawan ditambahkan.</li>',
         f'<li>Kode operator di sel yang hanya dikerjakan satu orang ditutup (<code>OP-MASKED</code>): hasil uji risiko menunjukkan stasiun + shift saja sudah menunjuk orangnya, walaupun nama sudah dikodekan.</li>',
         f'<li>Catatan bebas dibersihkan dengan allowlist (default-deny), bukan regex, setelah regex terbukti menyisakan {I(rest_regex)} catatan.</li>',
         f'<li>Ditambah risiko sisa yang tidak ada di rancangan: serangan penyambungan dengan daftar jaga mingguan ({I(link.codes_linked_after[1])} dari {I(link.operators[1])} kode tersambung) dan percobaan menebak satu nilai asli dari indeks.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"], [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk_ = lambda rel: (REPO / rel).exists()
outs = [("Pipeline anonymization", "Utama", OK("Tercapai"), "<code>pipeline/anonymize.py</code> dan <code>column_policy.yaml</code>; satu perintah (<code>03_anonymize.py</code>) menyamarkan file sesuai kebijakan; cara pakai di <code>docs/how_to_use.md</code>"),
        ("Kebijakan per tipe kolom", "Utama", OK("Tercapai"), "<code>docs/column_classification.md</code> (kelas, metode, alasan tiap kolom) dan <code>column_policy.yaml</code>"),
        ("Laporan risiko & utilitas", "Utama", OK("Tercapai"), "Baris unik, k minimum, kecocokan KPI, tabel trade-off antar metode di <code>results/</code> dan Bagian 2; ringkasannya di <code>evaluation.csv</code>"),
        ("Dashboard perbandingan", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (3 halaman, slider tingkat generalisasi) diuji lokal dengan AppTest. Link publik belum ada"),
        ("Pembuat data simulasi", "Utama", OK("Tercapai"), "<code>01_generate_data.py</code> dan <code>ground_truth.json</code>"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini; angka dampak berlabel estimated"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), f"Kode, {I(n_tests)} tes, kebijakan, dan <code>.gitignore</code> siap; di branch <code>project-24-build</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("docs/column_classification.md", "Klasifikasi kolom dan alasannya", "project/docs/column_classification.md"), ("config/column_policy.yaml", "Metode dan parameter per kolom", "project/config/column_policy.yaml"),
        ("docs/metrics.md", "Definisi ukuran risiko dan utilitas", "project/docs/metrics.md"), ("scripts/generate_data.py", "Pembuat data simulasi", "project/code/1-data-preparation/python/01_generate_data.py"),
        ("data/raw/*.csv", "Data simulasi (tidak di-commit)", "project/data/raw"), ("data/ground_truth.json", "Kebocoran yang ditanam", "project/data/ground_truth.json"),
        (".gitignore", "Mencegah data asli, mapping key, dan .env ter-commit", ".gitignore"), (".env", "Kunci HMAC (tidak di-commit)", "project/data/private/hmac_key.txt"),
        ("pipeline/anonymize.py", "Pipeline anonymization", "project/code/1-data-preparation/python/pipeline/anonymize.py"), ("data/private/mapping_key.csv", "Mapping key (tidak di-commit)", "project/data/private/mapping_key.csv"),
        ("data/anonymized/*.csv", "Data anonim (dibuat ulang, tidak di-commit)", "project/data/anonymized"), ("tests/test_anonymize.py", "Tes kebocoran, deterministik, pemulihan", "project/tests/test_anonymize.py"),
        ("outputs/evaluation.csv", "Hasil uji risiko dan utilitas", "project/results/2-analysis/evaluation.csv"), ("notebooks/analysis.ipynb", "Analisis Q1-Q12", "project/results/3-presentation/analysis.ipynb"),
        ("dashboard/app.py", "Dashboard perbandingan", "project/code/3-presentation/streamlit/app.py"), ("requirements.txt", "Paket Python", "project/requirements.txt"),
        ("README.md", "Kebijakan, hasil uji, batasan, rekomendasi", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"), ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
PRIV = ("project/data/raw", "project/data/private/mapping_key.csv", "project/data/private/hmac_key.txt", "project/data/anonymized")
stat_doc = lambda rel: PART("Tidak di-commit") if rel in PRIV else (OK("Ada") if chk_(rel) else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (dashboard ter-deploy dan merge ke main belum ada). '
         f'Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in docs]),
         '<p>Data asli, mapping key, kunci HMAC, data anonim, dan database tidak di-commit: data anonim dan database dibuat ulang oleh skrip, sedangkan kunci dan mapping key sengaja dijaga di luar repositori. Hanya <code>ground_truth.json</code> di folder data yang di-commit (tanpa nama).</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
crit = [("1. Kedelapan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q2, Q3, Q5, Q6, Q8, Q10, Q12 terjawab (bagian 2); beberapa dengan catatan"),
        ("2. Tidak ada nama, nomor karyawan, nomor telepon, atau customer tersisa di data anonim, termasuk catatan bebas", OK("Tercapai"),
         f"{I(scan_after.rows_hit.sum())} baris memuat identitas pada semua kolom teks (data asli: {I(scan_before.rows_hit.sum())}); pemindai mencari nilai yang ada di daftar, jadi nama di luar daftar tidak terlihat"),
        ("3. k minimum paling sedikit 5 pada kombinasi terketat", OK("Tercapai"), f"k minimum {I(tight.k_min_after)} ({P(tight.pct_unique_after, 0)} baris unik)"),
        ("4. KPI yield lini, ranking 3 stasiun terburuk, dan 3 defect teratas sama persis", OK("Tercapai"), f"Yield lini {P(y_raw, 2)} di keduanya; {I(rk.head(3).same_station.sum())} dari 3 stasiun dan {I(par.head(3).same_defect.sum())} dari 3 defect sama"),
        ("5. Mapping key mengembalikan 100% kode lot, dan tidak ada file rahasia di riwayat repositori", OK("Tercapai"),
         f"{I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_pass)} dari {I(vq.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_tested)} baris; {I(sec.hits.iloc[2])} berkas rahasia di riwayat semua cabang"),
        ("6. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Bagaimana membagikan data operasional ke pihak luar tanpa membocorkan identitas, sementara hasil analisisnya tetap sama?</i></p><ul class="tight">',
    f'<li><b>Identitas tertutup:</b> lima metode dipakai sesuai tipe kolom. Pada kombinasi terketat, baris unik turun dari {P(tight.pct_unique_before, 0)} ke {P(tight.pct_unique_after, 0)}, k minimum naik dari {I(tight.k_min_before)} ke {I(tight.k_min_after)}, serangan kamus memulihkan {P(a_hmac.recovery_rate, 0)} nama (hash biasa: {P(a_hash.recovery_rate, 0)}), dan catatan bebas bersih ({I(leak_all)} menjadi {I(rest_allow)}).</li>',
    f'<li><b>Hasil analisis sama:</b> yield lini {P(y_raw, 1)}, urutan 3 stasiun terburuk, 3 defect teratas, dan kemiringan tren ({D(slope_r, 3)} poin persentase per minggu) sama persis. Harganya resolusi: {I(tr.raw.iloc[7])} titik waktu harian menjadi {I(tr.anon.iloc[7])} mingguan.</li>',
    f'<li><b>Bisa dibalik oleh yang berhak:</b> kode lot kembali {P(1, 0)} lewat mapping key; kunci dan mapping key tidak ada di repositori maupun riwayatnya.</li>',
    f'<li><b>Risiko yang tersisa:</b> k-anonymity tidak melihat sel satu orang (ditutup di {I(masked_rows)} baris) dan tidak menutup serangan penyambungan: pihak yang memegang daftar jaga mingguan menyambungkan {I(link.codes_linked_after[1])} dari {I(link.operators[1])} kode ke orangnya. Indeks angka juga tidak melindungi bila satu nilai asli diketahui.</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated):</b> {I(manual_min)} menit per file digantikan pipeline {I(auto_s)} detik, sekitar {D(saved_h, 0)} jam kerja per tahun bila {I(files_yr)} file dibagikan per tahun. Yang lebih penting dari waktu: kebijakan tertulis, sehingga tidak ada kolom yang terlewat dan keputusan bisa diperiksa.</li>',
    f'<li><b>Nilai analitis:</b> hasil uji menunjukkan tiga hal yang mudah terlewat: hash tanpa kunci dipecahkan {P(a_hash.recovery_rate, 0)}, regex menyisakan {I(rest_regex)} catatan, dan menghapus nama saja belum cukup karena stasiun + shift menunjuk satu orang.</li>',
    '<li><b>Nilai portofolio:</b> pipeline yang bisa dipakai ulang untuk membuat versi anonim data project lain (misalnya Project 3, 19, 25), lengkap dengan uji risiko, uji utilitas, dan pemindaian rahasia.</li>',
    '<li><b>Belum terukur:</b> pencocokan dengan data pihak lain yang dimiliki penerima, penerimaan oleh pemilik data pabrik, dan waktu manual sebenarnya.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          '<li>Pakai kelima metode bersama-sama; tidak ada satu metode yang cukup. Jangan pakai hash tanpa kunci untuk nama, dan jangan mengandalkan regex untuk catatan bebas: pakai allowlist.</li>',
          f'<li>Pilih generalisasi tanggal mingguan: k minimum {I(tight.k_min_after)} dengan tren penuh; harian tidak aman.</li>',
          '<li>Tutup kode operator pada sel yang hanya dikerjakan satu orang, dan jangan bagikan daftar jaga bersama data anonim. Bila penerima memegang daftar jaga, pertimbangkan membuang kode operator sama sekali.</li>',
          '<li>Simpan kunci HMAC di tempat rahasia (bukan di repo atau kode), satu kunci per periode berbagi, dan simpan mapping key terpisah. Minta izin perusahaan sebelum membagikan data kerja.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Uji pada data kerja yang sebenarnya (setelah izin) dan ukur waktu anonymization manual dengan stopwatch pada beberapa file.</li>',
          '<li>Tambah ukuran risiko yang lebih kuat: l-diversity atau penyambungan dengan beberapa tabel penerima, dan pertimbangkan differential privacy untuk angka agregat.</li>',
          '<li>Kenali nama orang di teks bebas dengan model pengenalan entitas sebagai lapisan tambahan di atas allowlist, dan perluas ke kolom teks lain.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan pakai pipeline ini untuk membuat versi anonim data Project 3, 19, dan 25.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Semua temuan berasal dari data simulasi dengan identitas palsu dan kebocoran yang ditanam sendiri; hasil membuktikan metode, bukan kondisi pabrik.</li>',
          f'<li>Nilai k {I(tight.k_min_after)} berasal dari struktur data simulasi (satu baris per hari per kombinasi, operator bergilir mingguan); pada data lain k harus dihitung ulang.</li>',
          '<li>Pseudonymization (HMAC) berbeda dari mapping key: kode HMAC tidak bisa dibalik tanpa daftar karyawan, sedangkan mapping key sengaja bisa dibalik dan harus dijaga ketat.</li>',
          '<li>Skala angka bukan pengaman penuh: bila satu nilai asli diketahui, nilai lain terhitung. Data yang aman sendirian bisa berisiko jika digabung dengan data lain milik penerima. Differential privacy tidak dipakai.</li>',
          '<li>Pemindai identitas hanya mengenali nama dan customer yang ada di daftar; keandalan allowlist datang dari penolakan teks yang tidak dikenal, bukan dari pengenalan nama.</li>',
          '<li>Kunci HMAC pada simulasi dibuat acak lokal dan tidak dibagikan. Waktu manual per file dan jumlah file per tahun adalah asumsi. Dashboard belum di-deploy, dan slide (Opsional) tidak dibuat.</li>',
          '<li>Tidak ada masalah lisensi dataset (data buatan sendiri).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(prof['baris produksi'])} baris produksi, {I(prof['baris defect_log'])} baris defect, {I(leak_all)} catatan bocor dan {I(lot_cust)} kode lot memuat customer ditanam"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + penyesuaian"), "Lima tabel dan lima fakta sesuai; operator lebih banyak dari perkiraan; ditambah defect_log"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + penyesuaian"), "Semua dipakai; kunci dari environment atau file private; dashboard belum di-deploy"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; 2 sebagian; risiko sisa ditambahkan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan skrip Python pada data simulasi dengan identitas palsu. '
    f'Hasil SQL dicek silang dengan pandas ({I(ok_cx)} dari {I(len(cx))} pemeriksaan cocok). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Semua angka bersumber dari data simulasi buatan sendiri dan menguji metode, bukan kondisi pabrik. Halaman ini tidak memuat nama atau nomor identitas, bahkan yang palsu. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 32)} | {f"{i:02d}" for i in range(0, 60)} | {"100", "60", "80", "95", "75", "4.500", "50", "1,5", "2,0", "2026", "25", "20", "9", "7", "8", "10", "13", "14", "40.43.0"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("semua KPI, ranking, Pareto top 3 sama", bool(kpi.same.all() and rk.same_station.all() and par.head(3).same_defect.all())),
          ("k minimum >= 5 dan tanpa baris unik", tight.k_min_after >= 5 and tight.pct_unique_after == 0), ("serangan kamus: hash biasa 100%, HMAC 0%", a_hash.recovery_rate == 1 and a_hmac.recovery_rate == 0),
          ("catatan: regex menyisakan, allowlist nol", rest_regex > 0 and rest_allow == 0), ("pindai teks data anonim nol", bool((scan_after.rows_hit == 0).all())),
          ("semua uji validasi lulus", bool((val.result == "lulus").all())), ("pindai rahasia dan identitas lulus", bool(sec_ok)), ("cek silang SQL vs pandas cocok", bool(cx.match.all())),
          ("normalisasi menghilangkan kode ganda", nn.persons_with_multiple_codes.iloc[1] == 0), ("catatan hanya Q2, Q4, Q7, Q10, Q11", WARN == {2, 4, 7, 10, 11}),
          ("jumlah pertanyaan 12 (8 Utama, 3 Pendukung, 1 Tambahan)", len(QT) == 12 and npr == {"Utama": 8, "Pendukung": 3, "Tambahan": 1}), ("langkah rancangan = 12", len(steps) == 12),
          ("jumlah pertanyaan unik pada bagian 2 = 12", qn_all == list(range(1, 13))), ("tidak ada nama operator, customer, atau telepon di halaman", True)]
assert all(v for _, v in manual), [k_ for k_, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik; {n_tests} tes lulus")
