# Log perapian identitas (`02_profile_columns.py`, `anonymize.py`)

| Masalah | Ditemukan | Perlakuan |
|---|---|---|
| Penulisan nama operator berbeda (spasi ekstra, huruf besar/kecil) | 127 baris; 115 penulisan untuk 39 orang | Nama dinormalkan (spasi dirapikan, huruf kecil) sebelum HMAC; hasilnya 39 kode untuk 39 orang |
| Tanpa normalisasi | 38 dari 39 orang mendapat lebih dari satu kode (maksimum 4) | Tidak dipakai; hanya sebagai pembanding (`validation_name_normalization.csv`) |
| Catatan bebas memuat nama, telepon, atau customer | 142 catatan | Default-deny: hanya frasa pada allowlist yang dipertahankan, selain itu `[dihapus]` |
| Kode lot model khusus memuat nama customer | 1.500 baris | Seluruh kode lot diganti kode acak lewat mapping key |
| Sel stasiun x shift dengan satu operator | 1 sel | Kode operator di sel itu ditutup |

Satu nama selalu cocok dengan tepat satu nomor karyawan (dicek dengan assert), sehingga mapping key operator tidak ambigu.
