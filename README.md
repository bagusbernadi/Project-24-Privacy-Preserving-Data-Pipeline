[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 24: Privacy-Preserving Data Sharing Pipeline

**Status: Selesai di branch `project-24-build` (menunggu review sebelum digabung ke `main`).**

Halaman rancangan dan Report: https://bagusbernadi.github.io/project-24-privacy-preserving-data-pipeline/

| | |
|---|---|
| Kategori | Manufaktur (perakitan sepeda motor) / tata kelola data |
| Tingkat | Menengah |
| Data | Data simulasi buatan sendiri dengan identitas palsu (Faker, id_ID): 10 stasiun, 3 model, 2 shift, 75 hari kerja |
| Tools | Python (pandas, hashlib/hmac, Faker, pytest), DuckDB + SQL, Streamlit + Plotly, Jupyter |

## 1. Problem

Bagaimana membagikan data operasional ke pihak luar tanpa membocorkan identitas, sementara hasil analisisnya tetap sama? Dipecah menjadi 12 pertanyaan (8 prioritas utama); jawabannya ada di tab Report pada halaman project.

## 2. Data

- Data simulasi dengan seed tetap (`project/code/1-data-preparation/python/01_generate_data.py`), v3: 4.500 baris produksi, 6.313 baris defect, 39 operator, 12 customer, 450 lot.
- Kebocoran yang sengaja ditanam: 142 catatan bebas memuat nama atau customer (96 di antaranya nomor telepon), 1.500 baris model khusus yang kode lotnya memuat nama customer, 127 baris dengan penulisan nama kotor (115 penulisan untuk 39 orang), dan 1 sel stasiun x shift yang hanya dikerjakan satu orang.
- Data asli, mapping key, dan kunci HMAC **tidak pernah di-commit** (`.gitignore`; dipindai di `secret_scan.csv`). Detail kolom: `project/docs/data_dictionary.md`.

## 3. Analysis

- Pipeline (`project/code/1-data-preparation/python/pipeline/anonymize.py`) menjalankan kebijakan per kolom (`project/config/column_policy.yaml`): Pseudonymization HMAC-SHA256 untuk nama operator, Mapping Key untuk kode lot, generalisasi tanggal ke minggu, skala angka (indeks base 100), dan hapus informasi sensitif (nomor karyawan, nama customer, catatan bebas lewat allowlist).
- Pada kombinasi quasi-identifier terketat, baris unik turun dari 100% ke 0% dan k minimum naik dari 1 ke 5.
- Serangan kamus (19.462 nama kandidat): hash biasa memulihkan 100% nama operator, HMAC dengan kunci 0%.
- Catatan bebas: 142 catatan memuat identitas; pembersihan regex menyisakan 21, allowlist menyisakan 0 (tetapi 142 catatan ikut dihapus).
- Yield lini 88,3% di data asli dan di data anonim (selisih terbesar semua KPI 2e-09); 3 dari 3 stasiun terburuk dan 3 dari 3 defect teratas sama persis.
- Generalisasi mingguan adalah tingkat terendah yang memenuhi k >= 5; titik waktu tren turun dari 75 ke 15. Tingkat lebih kasar tidak menaikkan k pada kombinasi terketat dan hanya menurunkan korelasi tren (bulanan 0,80).
- Risiko sisa: pihak yang punya daftar jaga mingguan lengkap masih bisa menyambungkan 38 dari 39 kode operator ke orangnya; satu sel yang hanya dikerjakan satu orang ditutup (225 baris tanpa kode operator).
- Output sama persis pada dua kali jalan dengan kunci yang sama; kode lot kembali 100% ke nilai asli (4.500 dari 4.500 baris). Tanpa normalisasi nama, 38 dari 39 orang mendapat lebih dari satu kode.
- Cek silang SQL vs pandas: 26 dari 26 pemeriksaan cocok. Pindai berkas rahasia dan identitas: 8 dari 8 pemeriksaan lulus.

## 4. Recommendation

Pakai kombinasi kelima metode sekaligus; tidak ada satu metode yang cukup. Jangan memakai hash tanpa kunci, dan jangan mengandalkan regex saja untuk catatan bebas (nama depan lolos). Pilih generalisasi mingguan, dan tutup kode operator pada sel yang hanya dikerjakan satu orang. Sebelum dipakai pada data kerja: minta izin berbagi data, buat kunci acak yang disimpan di tempat rahasia, dan jalankan ulang seluruh uji pada data nyata.

## 5. Impact

Estimated: anonymization manual 45 menit per file (asumsi, tidak diukur) digantikan pipeline yang berjalan sekitar 1 detik (terukur, dibulatkan ke atas): dengan 24 file per tahun (asumsi) sekitar 18 jam kerja per tahun.

## Batasan

- Data simulasi dengan identitas palsu; hasil membuktikan metode, bukan kondisi pabrik. Kunci HMAC di simulasi dibuat acak lokal; pada data kerja kunci harus disimpan di secret manager.
- Skala angka (indeks) bukan pengaman penuh: bila satu nilai asli diketahui, semua nilai lain dapat dihitung (100% baris pulih pada uji).
- Pseudonymization (HMAC) berbeda dari mapping key: kode HMAC tidak bisa dibalik tanpa daftar karyawan, mapping key sengaja bisa dibalik dan harus disimpan terpisah.
- Anonim di sini belum tentu anonim di tempat lain: digabung dengan data penerima (misalnya daftar jaga) risiko naik. Differential privacy tidak dipakai. Dashboard belum di-deploy. Waktu manual per file adalah asumsi.

## Menjalankan

```
pip install -r project/requirements.txt
cd project
python -m pytest tests -q
cd code/1-data-preparation/python && python 01_generate_data.py && python 02_profile_columns.py && python 03_anonymize.py && python 04_build_db.py
cd ../../2-analysis/python && for s in 05 06 07 08 09 10 11 12 13; do python ${s}_*.py; done
cd ../../3-presentation/python && for s in 14 15 16; do python ${s}_*.py; done
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
