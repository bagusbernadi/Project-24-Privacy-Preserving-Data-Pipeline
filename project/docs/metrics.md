# Definisi ukuran risiko dan utilitas

## Risiko
| Ukuran | Definisi |
|---|---|
| Baris unik | Persen baris yang kombinasi quasi-identifier-nya muncul tepat satu kali |
| k minimum | Ukuran kelompok terkecil pada kombinasi quasi-identifier; target k >= 5 |
| Kombinasi terketat | tanggal (data asli) atau minggu (data anonim) + shift + stasiun + model + operator (nama dinormalkan di data asli, kode di data anonim) |
| Serangan kamus | Penyerang memegang ±20.000 nama (nama umum + semua nama karyawan), menghitung kode dengan fungsi hash yang sama, dan mencocokkannya; ukuran = persen operator yang namanya pulih |
| Identitas tersisa di teks | Jumlah baris yang memuat nomor telepon, nomor karyawan, nama orang (lengkap atau bagian nama), atau nama customer, dipindai di semua kolom teks |
| Sel satu orang | Sel stasiun x shift yang hanya dikerjakan satu operator |
| Serangan penyambungan | Penyerang memegang daftar jaga (siapa bertugas di stasiun x shift x minggu) dan menyambungkan kode ke orang |

## Utilitas
| Ukuran | Definisi |
|---|---|
| Yield lini | Barang baik di stasiun terakhir / input di stasiun pertama, dijumlahkan seluruh periode |
| NG rate stasiun | NG / input per stasiun; ranking dari tertinggi |
| Pareto defect | Jumlah per kode defect, urut turun lalu kode |
| "Sama persis" | Urutan sama dan selisih nilai di bawah 1e-6 (selisih sisa berasal dari pembulatan indeks 6 desimal) |
| Kemiringan tren | Kemiringan regresi linear yield lini (poin persentase per minggu) |
| Korelasi tren | Korelasi Pearson antara yield mingguan asli dan yield pada tingkat generalisasi tertentu |

## Dampak
Menit manual per file dan jumlah file per tahun adalah asumsi (estimated); waktu pipeline diukur (median 7 kali jalan, dibulatkan ke atas ke detik).
