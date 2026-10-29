"""Tahap 3 / langkah 16: buat README.md (root repo) dan docs/*.md; semua angka dibaca dari CSV hasil."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

R = lambda n: pd.read_csv(C.result(n))
f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
n = lambda v: f"{int(round(v)):,}".replace(",", ".")
pc = lambda v, d=0: f(v * 100, d) + "%"

prof = R("data_profile.csv").set_index("item")["value"]
cc, summ = R("column_classification.csv"), R("anonymize_summary.csv").set_index("item")["value"]
k, att, notes, cells, link = R("risk_k_anonymity.csv"), R("risk_dictionary_attack.csv"), R("risk_notes.csv"), R("risk_operator_cells.csv"), R("risk_linkage.csv")
kpi, rk, par, tr, gran = R("utility_kpi.csv"), R("utility_station_ranking.csv"), R("utility_pareto.csv"), R("utility_trend.csv"), R("granularity_curve.csv")
val, nn, sec, cx = R("validation_checks.csv"), R("validation_name_normalization.csv"), R("secret_scan.csv"), R("crosscheck_sql.csv")
imp = R("impact_time.csv").set_index("item")["value"]
t = k.iloc[-1]
sc_fail = int((sec.result != "lulus").sum())
q = val.set_index("check")

md = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 24: Privacy-Preserving Data Sharing Pipeline

**Status: Selesai di branch `project-24-build` (menunggu review sebelum digabung ke `main`).**

Halaman rancangan dan Report: https://bagusbernadi.github.io/project-24-privacy-preserving-data-pipeline/

| | |
|---|---|
| Kategori | Manufaktur (perakitan sepeda motor) / tata kelola data |
| Tingkat | Menengah |
| Data | Data simulasi buatan sendiri dengan identitas palsu (Faker, id_ID): {n(prof['stasiun'])} stasiun, 3 model, 2 shift, {n(prof['hari kerja'])} hari kerja |
| Tools | Python (pandas, hashlib/hmac, Faker, pytest), DuckDB + SQL, Streamlit + Plotly, Jupyter |

## 1. Problem

Bagaimana membagikan data operasional ke pihak luar tanpa membocorkan identitas, sementara hasil analisisnya tetap sama? Dipecah menjadi 12 pertanyaan (8 prioritas utama); jawabannya ada di tab Report pada halaman project.

## 2. Data

- Data simulasi dengan seed tetap (`project/code/1-data-preparation/python/01_generate_data.py`), v3: {n(prof['baris produksi'])} baris produksi, {n(prof['baris defect_log'])} baris defect, {n(prof['operator (orang)'])} operator, 12 customer, {n(prof['lot'])} lot.
- Kebocoran yang sengaja ditanam: {n(prof['catatan bebas dengan identitas'])} catatan bebas memuat nama atau customer ({n(prof['catatan dengan nomor telepon'])} di antaranya nomor telepon), {n(prof['baris model khusus dengan nama customer di kode lot'])} baris model khusus yang kode lotnya memuat nama customer, {n(prof['baris dengan penulisan nama kotor'])} baris dengan penulisan nama kotor ({n(prof['string nama operator berbeda'])} penulisan untuk {n(prof['operator (orang)'])} orang), dan {n(prof['sel dengan satu operator'])} sel stasiun x shift yang hanya dikerjakan satu orang.
- Data asli, mapping key, dan kunci HMAC **tidak pernah di-commit** (`.gitignore`; dipindai di `secret_scan.csv`). Detail kolom: `project/docs/data_dictionary.md`.

## 3. Analysis

- Pipeline (`project/code/1-data-preparation/python/pipeline/anonymize.py`) menjalankan kebijakan per kolom (`project/config/column_policy.yaml`): Pseudonymization HMAC-SHA256 untuk nama operator, Mapping Key untuk kode lot, generalisasi tanggal ke minggu, skala angka (indeks base 100), dan hapus informasi sensitif (nomor karyawan, nama customer, catatan bebas lewat allowlist).
- Pada kombinasi quasi-identifier terketat, baris unik turun dari {pc(t.pct_unique_before)} ke {pc(t.pct_unique_after)} dan k minimum naik dari {n(t.k_min_before)} ke {n(t.k_min_after)}.
- Serangan kamus ({n(att.candidates[0])} nama kandidat): hash biasa memulihkan {pc(att.recovery_rate[0])} nama operator, HMAC dengan kunci {pc(att.recovery_rate[1])}.
- Catatan bebas: {n(notes.rows_with_identity[0])} catatan memuat identitas; pembersihan regex menyisakan {n(notes.rows_with_identity[1])}, allowlist menyisakan {n(notes.rows_with_identity[2])} (tetapi {n(summ['catatan dihapus'])} catatan ikut dihapus).
- Yield lini {f(kpi.raw[0] * 100, 1)}% di data asli dan di data anonim (selisih terbesar semua KPI {kpi.abs_diff.max():.0e}); {int(rk.head(3).same_station.sum())} dari 3 stasiun terburuk dan {int(par.head(3).same_defect.sum())} dari 3 defect teratas sama persis.
- Generalisasi mingguan adalah tingkat terendah yang memenuhi k >= 5; titik waktu tren turun dari {n(tr.raw[7])} ke {n(tr.anon[7])}. Tingkat lebih kasar tidak menaikkan k pada kombinasi terketat dan hanya menurunkan korelasi tren (bulanan {f(gran.trend_corr_weekly[3], 2)}).
- Risiko sisa: pihak yang punya daftar jaga mingguan lengkap masih bisa menyambungkan {n(link.codes_linked_after[1])} dari {n(link.operators[1])} kode operator ke orangnya; satu sel yang hanya dikerjakan satu orang ditutup ({n(summ['baris operator ditutup'])} baris tanpa kode operator).
- Output sama persis pada dua kali jalan dengan kunci yang sama; kode lot kembali 100% ke nilai asli ({n(q.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_pass)} dari {n(q.loc['Kode lot dikembalikan ke nilai asli (baris)'].n_tested)} baris). Tanpa normalisasi nama, {n(nn.persons_with_multiple_codes[0])} dari {n(nn.persons[0])} orang mendapat lebih dari satu kode.
- Cek silang SQL vs pandas: {int(cx.match.sum())} dari {len(cx)} pemeriksaan cocok. Pindai berkas rahasia dan identitas: {int((sec.result == 'lulus').sum())} dari {len(sec)} pemeriksaan lulus.

## 4. Recommendation

Pakai kombinasi kelima metode sekaligus; tidak ada satu metode yang cukup. Jangan memakai hash tanpa kunci, dan jangan mengandalkan regex saja untuk catatan bebas (nama depan lolos). Pilih generalisasi mingguan, dan tutup kode operator pada sel yang hanya dikerjakan satu orang. Sebelum dipakai pada data kerja: minta izin berbagi data, buat kunci acak yang disimpan di tempat rahasia, dan jalankan ulang seluruh uji pada data nyata.

## 5. Impact

Estimated: anonymization manual {n(imp['Waktu anonymization manual di Excel per file'])} menit per file (asumsi, tidak diukur) digantikan pipeline yang berjalan sekitar {n(imp.iloc[0])} detik (terukur, dibulatkan ke atas): dengan {n(imp['File yang dibagikan per tahun'])} file per tahun (asumsi) sekitar {f(imp['Jam kerja dihemat per tahun'], 0)} jam kerja per tahun.

## Batasan

- Data simulasi dengan identitas palsu; hasil membuktikan metode, bukan kondisi pabrik. Kunci HMAC di simulasi dibuat acak lokal; pada data kerja kunci harus disimpan di secret manager.
- Skala angka (indeks) bukan pengaman penuh: bila satu nilai asli diketahui, semua nilai lain dapat dihitung ({pc(R('method_tradeoff.csv').risk_after[4])} baris pulih pada uji).
- Pseudonymization (HMAC) berbeda dari mapping key: kode HMAC tidak bisa dibalik tanpa daftar karyawan, mapping key sengaja bisa dibalik dan harus disimpan terpisah.
- Anonim di sini belum tentu anonim di tempat lain: digabung dengan data penerima (misalnya daftar jaga) risiko naik. Differential privacy tidak dipakai. Dashboard belum di-deploy. Waktu manual per file adalah asumsi.

## Menjalankan

```
pip install -r project/requirements.txt
cd project
python -m pytest tests -q
cd code/1-data-preparation/python && python 01_generate_data.py && python 02_profile_columns.py && python 03_anonymize.py && python 04_build_db.py
cd ../../2-analysis/python && for s in 05 06 07 08 09 10 11 12 13; do python ${{s}}_*.py; done
cd ../../3-presentation/python && for s in 14 15 16; do python ${{s}}_*.py; done
streamlit run ../streamlit/app.py
python design-and-report/src/build_report.py   # dari root repo
```

Kunci HMAC dibaca dari environment `ANON_HMAC_KEY` atau `project/data/private/hmac_key.txt` (dibuat acak bila belum ada). Menyamarkan file baru: lihat `project/docs/how_to_use.md`.

## Struktur repository

```
index.html                 Pengalihan ke design-and-report/
design-and-report/         Halaman Design dan Report (src/ berisi generator)
project/
  code/1-data-preparation  Generator, profil kolom, pipeline (python/pipeline), database (sql)
  code/2-analysis          Uji risiko dan utilitas, trade-off, validasi, pindai rahasia, dampak (python, sql)
  code/3-presentation      Data dashboard, notebook, README, Streamlit
  config/                  Kebijakan kolom (column_policy.yaml)
  results/                 CSV hasil per tahap, notebook
  docs/                    Klasifikasi kolom, ukuran, kamus data, log cleaning, cara pakai
  tests/                   pytest
  data/                    README, ground_truth.json (data asli, private, dan anonim tidak di-commit)
```
"""
(C.ROOT.parent / "README.md").write_text(md, encoding="utf-8")

# --- docs/column_classification.md
rows = "\n".join(f"| {r['table']} | `{r['column']}` | {r['class']} | {r['method']} | {r['output'] if r['output'] != '(dihapus)' else 'dihapus'} | {r['why']} |" for _, r in cc.iterrows())
(C.DOCS_DIR / "column_classification.md").write_text(f"""# Klasifikasi kolom dan kebijakan (Q1)

Kelas: **direct** = identitas langsung; **quasi** = quasi-identifier (kombinasinya bisa menunjuk satu baris atau orang); **sensitive** = nilai bisnis atau teks bebas; **safe** = aman.
Metode: pseudonymize (HMAC-SHA256), mapping_key, generalize, scale, drop, clean_text (allowlist), keep. Sumber kebenaran: `config/column_policy.yaml`.

| Tabel | Kolom | Kelas | Metode | Kolom hasil | Alasan |
|---|---|---|---|---|---|
{rows}

Tambahan di luar kolom: sel stasiun x shift dengan operator kurang dari {C.MIN_OPERATORS_PER_CELL} orang menutup kode operatornya (`OP-MASKED`), karena stasiun + shift saja sudah menunjuk orangnya.
""", encoding="utf-8")

# --- docs/cleaning_log.md
(C.DOCS_DIR / "cleaning_log.md").write_text(f"""# Log perapian identitas (`02_profile_columns.py`, `anonymize.py`)

| Masalah | Ditemukan | Perlakuan |
|---|---|---|
| Penulisan nama operator berbeda (spasi ekstra, huruf besar/kecil) | {n(prof['baris dengan penulisan nama kotor'])} baris; {n(prof['string nama operator berbeda'])} penulisan untuk {n(prof['operator (orang)'])} orang | Nama dinormalkan (spasi dirapikan, huruf kecil) sebelum HMAC; hasilnya {n(nn.distinct_codes[1])} kode untuk {n(nn.persons[1])} orang |
| Tanpa normalisasi | {n(nn.persons_with_multiple_codes[0])} dari {n(nn.persons[0])} orang mendapat lebih dari satu kode (maksimum {n(nn.max_codes_per_person[0])}) | Tidak dipakai; hanya sebagai pembanding (`validation_name_normalization.csv`) |
| Catatan bebas memuat nama, telepon, atau customer | {n(prof['catatan bebas dengan identitas'])} catatan | Default-deny: hanya frasa pada allowlist yang dipertahankan, selain itu `[dihapus]` |
| Kode lot model khusus memuat nama customer | {n(prof['baris model khusus dengan nama customer di kode lot'])} baris | Seluruh kode lot diganti kode acak lewat mapping key |
| Sel stasiun x shift dengan satu operator | {n(prof['sel dengan satu operator'])} sel | Kode operator di sel itu ditutup |

Satu nama selalu cocok dengan tepat satu nomor karyawan (dicek dengan assert), sehingga mapping key operator tidak ambigu.
""", encoding="utf-8")
print("README.md dan docs ditulis")
