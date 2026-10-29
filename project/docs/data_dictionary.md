# Kamus data

## Data asli simulasi (`data/raw/`, tidak di-commit)
**production_identified.csv** (1 baris = tanggal x shift x model x stasiun)
`date`, `shift`, `station`, `model`, `employee_id` (nomor karyawan palsu), `operator_name` (nama palsu, sebagian kotor), `lot_no` (model khusus: awalan nama customer), `customer_name` (palsu), `input_qty` (input stasiun, mengalir dari stasiun ke stasiun), `ng_qty`, `note` (catatan bebas, sebagian memuat nama/telepon/customer).

**defect_log.csv** (1 baris = tanggal x shift x model x stasiun x kode defect): `date`, `shift`, `station`, `model`, `defect_code`, `qty`. **dim_defect.csv**: kode, nama, stasiun, kategori.

## Data anonim (`data/anonymized/`, boleh dibagikan, dibuat ulang oleh pipeline)
**anonymized_production.csv**: `week` (ISO, mis. 2026-W10), `shift`, `station`, `model`, `operator_code` (OP- + 8 hex HMAC, atau OP-MASKED), `lot_code` (LOT- + 5 digit dari mapping key), `input_index`, `ng_index` (indeks, rata-rata input = 100), `ng_rate`, `note_clean` (frasa aman atau [dihapus]).
**anonymized_defect_log.csv**: `week`, `shift`, `station`, `model`, `defect_code`, `qty_index`.

## Rahasia (`data/private/`, tidak di-commit)
**mapping_key.csv**: `column` (lot, operator, scale_base), `code`, `original_value`, `created_at`. `hmac_key.txt`: kunci HMAC (atau lewat environment `ANON_HMAC_KEY`).

## Database (`privacy_pipeline.duckdb`, tidak di-commit)
Tabel `raw_production`, `raw_defect`, `anon_production`, `anon_defect`, `column_policy`; view seragam `v_raw_prod`, `v_anon_prod`, `v_raw_defect`, `v_anon_defect` (kolom sama, jadi query yang sama dipakai di keduanya).

## ground_truth.json (di-commit, tanpa nama)
Seed, versi, jumlah baris dan operator, sel satu orang, jumlah kebocoran tertanam per jenis, stasiun terburuk yang ditanam, dan nomor baris catatan bocor.
