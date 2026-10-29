"""Tahap 2 / langkah 11: dampak waktu (Q10-Q11). Waktu otomatis diukur; waktu manual dan jumlah file per tahun adalah asumsi (estimated).
Hasil: results/2-analysis/impact_time.csv, impact_scenarios.csv. impact_time.csv memuat waktu terukur sehingga nilainya sedikit berbeda tiap kali dijalankan."""
import math
import statistics
import time

import pandas as pd

import analysis_lib as A
from analysis_lib import C
from pipeline.anonymize import get_key, load_policy, anonymize

pol = load_policy(C.COLUMN_POLICY)
key = get_key(pol, C.ROOT)
raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
rdef = pd.read_csv(C.RAW_DIR / "defect_log.csv")
anonymize(raw, rdef, pol, key, C.DATA_DATE)                      # pemanasan
runs = []
for _ in range(7):
    t0 = time.perf_counter()
    anonymize(raw, rdef, pol, key, C.DATA_DATE)
    runs.append(time.perf_counter() - t0)
sec = max(1, math.ceil(statistics.median(runs)))          # dibulatkan ke atas ke detik penuh supaya hasil stabil antar-run
auto_min = sec / 60
saved_min = C.MANUAL_MINUTES_PER_FILE - auto_min
imp = [["Waktu pipeline per file (median 7 kali jalan, dibulatkan ke atas)", sec, "detik", "measured"],
       ["Baris yang diproses per file", len(raw), "baris", "measured"],
       ["Waktu anonymization manual di Excel per file", C.MANUAL_MINUTES_PER_FILE, "menit", "estimated"],
       ["Menit yang digantikan per file", round(saved_min, 1), "menit", "estimated"],
       ["File yang dibagikan per tahun", C.FILES_PER_YEAR, "file", "estimated"],
       ["Jam kerja dihemat per tahun", round(C.FILES_PER_YEAR * saved_min / 60, 1), "jam", "estimated"]]
pd.DataFrame(imp, columns=["item", "value", "unit", "label"]).to_csv(C.RES_ANALYSIS / "impact_time.csv", index=False)
sc = [[m, f, round(f * (m - auto_min) / 60, 1)] for m in (30, C.MANUAL_MINUTES_PER_FILE, 60) for f in (12, C.FILES_PER_YEAR, 48)]
pd.DataFrame(sc, columns=["manual_minutes_per_file", "files_per_year", "hours_saved_per_year"]).assign(label="estimated").to_csv(C.RES_ANALYSIS / "impact_scenarios.csv", index=False)
print(pd.read_csv(C.RES_ANALYSIS / "impact_time.csv").to_string(index=False))
