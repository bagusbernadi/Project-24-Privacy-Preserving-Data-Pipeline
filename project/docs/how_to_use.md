# Cara menyamarkan file baru

1. Pastikan kunci ada: `export ANON_HMAC_KEY=<kunci acak panjang>` (atau biarkan pipeline membuat `project/data/private/hmac_key.txt`). Simpan kunci di tempat rahasia; jangan di kode atau repo. Satu kunci untuk satu periode berbagi data.
2. Letakkan file di `project/data/raw/` dengan kolom seperti `docs/data_dictionary.md`, atau sesuaikan `config/column_policy.yaml`.
3. Jalankan dari `project/code/1-data-preparation/python`: `python 03_anonymize.py`. Hasil ada di `project/data/anonymized/`; `project/data/private/mapping_key.csv` berisi pemetaan (pegang sendiri, jangan dibagikan).
4. Periksa sebelum membagikan: `python -m pytest project/tests -q`, lalu `python 05_risk_assessment.py` dan `python 10_secret_scan.py` di `code/2-analysis/python`. Syaratnya: tidak ada identitas tersisa, k minimum >= 5, KPI sama.
5. Bagikan hanya isi `data/anonymized/`. Minta izin berbagi data lebih dulu.

File berikutnya: mapping key yang sudah ada dipakai ulang sehingga lot lama tetap mendapat kode lama.
