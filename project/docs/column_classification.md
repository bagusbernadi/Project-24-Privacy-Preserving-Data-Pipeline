# Klasifikasi kolom dan kebijakan (Q1)

Kelas: **direct** = identitas langsung; **quasi** = quasi-identifier (kombinasinya bisa menunjuk satu baris atau orang); **sensitive** = nilai bisnis atau teks bebas; **safe** = aman.
Metode: pseudonymize (HMAC-SHA256), mapping_key, generalize, scale, drop, clean_text (allowlist), keep. Sumber kebenaran: `config/column_policy.yaml`.

| Tabel | Kolom | Kelas | Metode | Kolom hasil | Alasan |
|---|---|---|---|---|---|
| production | `date` | quasi | generalize | week | Tanggal harian + shift + stasiun + model menunjuk satu baris; mingguan memberi k minimum 5. |
| production | `shift` | quasi | keep | shift | Dibutuhkan untuk analisis shift; tidak cukup menunjuk orang bila operator ditutup. |
| production | `station` | quasi | keep | station | Dibutuhkan untuk KPI dan ranking stasiun. |
| production | `model` | quasi | keep | model | Dibutuhkan untuk analisis per model. |
| production | `employee_id` | direct | drop | dihapus | Nomor karyawan menunjuk orang langsung; kode operator sudah cukup. |
| production | `operator_name` | direct | pseudonymize | operator_code | Perlu kode konsisten per orang agar analisis per operator tetap bisa; HMAC-SHA256 dengan kunci rahasia, nama dinormalkan dulu. |
| production | `lot_no` | direct | mapping_key | lot_code | Lot harus bisa ditelusuri balik oleh pemilik data; pada model khusus kode lot memuat nama customer. |
| production | `customer_name` | direct | drop | dihapus | Tidak dibutuhkan analisis; menyebut pelanggan langsung. |
| production | `input_qty` | sensitive | scale | input_index | Volume absolut itu rahasia bisnis; rasio dan tren cukup untuk analisis. |
| production | `ng_qty` | sensitive | scale | ng_index | Sama dengan input_qty; ng_rate (rasio) ikut dihitung. |
| production | `note` | sensitive | clean_text | note_clean | Teks bebas bisa memuat nama, telepon, customer; hanya frasa yang diizinkan (allowlist) yang dipertahankan. |
| defect_log | `date` | quasi | generalize | week | Sama dengan production. |
| defect_log | `shift` | quasi | keep | shift | Sama dengan production. |
| defect_log | `station` | quasi | keep | station | Sama dengan production. |
| defect_log | `model` | quasi | keep | model | Sama dengan production. |
| defect_log | `defect_code` | safe | keep | defect_code | Kode cacat bukan identitas; dibutuhkan untuk Pareto. |
| defect_log | `qty` | sensitive | scale | qty_index | Skala yang sama dengan production. |

Tambahan di luar kolom: sel stasiun x shift dengan operator kurang dari 2 orang menutup kode operatornya (`OP-MASKED`), karena stasiun + shift saja sudah menunjuk orangnya.
