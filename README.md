[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 24: Privacy-Preserving Data Sharing Pipeline

**Status: Design (rancangan).**

**Tujuan:** Membangun pipeline yang menyamarkan identitas di data produksi (nama operator, kode lot, customer, catatan bebas) dengan metode yang sesuai tiap jenis kolom, lalu membuktikan dengan angka bahwa risiko identifikasi ulang turun sementara hasil analisis (KPI, ranking, Pareto) tetap sama, sehingga data bisa dibagikan ke pihak luar dengan aman.


| | |
|---|---|
| Kategori | Manufaktur (perakitan sepeda motor) / tata kelola data |
| Tingkat | Menengah |
| Data | Simulasi: data produksi dengan identitas palsu (Faker) |
| Tools | Python (pandas, hashlib/hmac, Faker, pytest), DuckDB + SQL, Streamlit + Plotly |

## 1. Problem
Bagaimana membagikan data operasional ke pihak luar tanpa membocorkan identitas, sementara hasil analisisnya tetap sama?

## 2. Data
Data produksi simulasi dibuat oleh `scripts/generate_data.py` dengan identitas palsu dari Faker (seed tetap). Perkiraan ±4.500 baris. Kebocoran (nama di catatan, operator unik) sengaja ditanam. Data asli, mapping key, dan kunci HMAC tidak pernah di-commit.

Versi data: v2. Tanggal dibuat: 28 Okt 2026. Seed: 24260302. Generator: `scripts/generate_data.py`. Hasil v2: 4.500 baris, 462 catatan dengan identitas bocor; identitas palsu dari Faker 40.43.0 (id_ID).

## 3. Analysis
Rencana: klasifikasi kolom, 5 metode anonymization, uji risiko (baris unik, k minimum, serangan kamus), uji utilitas (KPI, ranking, Pareto, tren). Belum dikerjakan.

## 4. Recommendation
Belum dikerjakan.

## 5. Impact
Belum dikerjakan. Angka dampak akan diberi label `estimated` / `simulated`.

## Batasan yang sudah diketahui
- Pseudonymization (HMAC) berbeda dari mapping key yang memang bisa dibalik.
- Skala angka hanya menyamarkan nilai absolut, bukan keamanan penuh.
- Data yang aman sendirian bisa berisiko jika digabung dengan data lain.
- Izin perusahaan tetap diperlukan untuk data kerja.

## Struktur repository (rencana)
```
docs/            # klasifikasi kolom, definisi ukuran
config/          # kebijakan per kolom
scripts/         # generator data simulasi
pipeline/        # anonymization
tests/           # tes kebocoran dan pemulihan
notebooks/       # analisis risiko dan utilitas
dashboard/       # dashboard perbandingan
index.html       # halaman rancangan (GitHub Pages)
README.md
```
