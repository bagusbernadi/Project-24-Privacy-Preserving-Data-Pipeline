# Data

Semua data di project ini simulasi (karangan), dibuat oleh generator dengan seed tetap. Tidak ada dataset publik atau data perusahaan, jadi tidak ada masalah lisensi.

| | |
|---|---|
| Versi data | v3 |
| Tanggal dibuat | 29 Okt 2026 |
| Seed | 24260302 |
| Cara membuat ulang | `python3 project/code/1-data-preparation/python/01_generate_data.py` (dari root repo) |
| Hasil v3 | 4.500 baris produksi, 6.313 baris defect_log, 39 operator, 12 customer, 450 lot; 142 catatan dengan identitas bocor; identitas palsu dari Faker 40.43.0 (id_ID) |

`raw/` (data identitas), `private/` (kunci HMAC dan mapping key), dan `anonymized/` tidak di-commit (lihat `.gitignore`). Yang di-commit hanya `ground_truth.json` (tanpa nama). Jejak pembuatan (seed, commit, SHA-256 hasil) dicatat di repo `DataCenter`, folder `simulasi/`. Jika generator, seed, atau versi library berubah, hasil berubah dan versi data harus dinaikkan.
