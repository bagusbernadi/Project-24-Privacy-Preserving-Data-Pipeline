"""Tahap 1 / langkah 01: data produksi simulasi lini perakitan sepeda motor dengan identitas palsu (Faker, id_ID). Seed tetap.

Hasil (data/raw/): production_identified.csv (data "asli" simulasi, berisi identitas palsu), defect_log.csv,
dim_defect.csv; data/ground_truth.json (kebocoran yang sengaja ditanam, tanpa nama).
Data ini 100% karangan. Kunci HMAC dan mapping key dibuat oleh pipeline, bukan di sini, dan tidak pernah di-commit.
Jalankan dari folder project/:  python3 code/1-data-preparation/python/01_generate_data.py   (versi data: v3; butuh Faker)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

DATES = pd.bdate_range(C.START_DATE, periods=C.N_DAYS)
rng = np.random.default_rng(C.SEED)
fake = Faker("id_ID")
Faker.seed(C.SEED)


def cust_token(name):
    """Kata khas dari nama perusahaan, dipakai pada kode lot model khusus (mis. 'PT Wijaya Tbk' -> 'WIJAYA')."""
    words = [w for w in re.sub(r"[^A-Za-z ]", "", name).split() if w.upper() not in {"PT", "CV", "UD", "TBK", "PERUM", "PERSERO"}]
    return (words[0] if words else "CUST").upper()[:10]


# --- identitas palsu: operator per (stasiun, shift), 2 orang bergantian per minggu, kecuali satu sel hanya 1 orang
pool = {}
emp_no = 1000
for s in range(len(C.STATIONS)):
    for j in range(len(C.SHIFTS)):
        n = 1 if (s, j) == C.SINGLETON_CELL else 2
        pool[(s, j)] = []
        for _ in range(n):
            emp_no += 1
            pool[(s, j)].append((f"EMP-{emp_no}", fake.name()))
customers = [fake.company() for _ in range(12)]
n_operators = sum(len(v) for v in pool.values())

# --- produksi harian: satu baris per tanggal x shift x model x stasiun; qty mengalir antar stasiun
by_station = {s: [d for d in C.DEFECTS if d[2] == s] for s in range(len(C.STATIONS))}
lot_ids = iter(rng.permutation(1_000_000)[: C.N_DAYS * len(C.SHIFTS) * len(C.MODELS)])
rows, dlog = [], []
for t, day in enumerate(DATES):
    noise = np.exp(rng.normal(0, 0.15, len(C.STATIONS)))
    week = t // 5
    for m in C.MODELS:
        for j, sh in enumerate(C.SHIFTS):
            cust = customers[int(rng.integers(0, len(customers)))]
            lot_no = (f"{cust_token(cust)}-{int(next(lot_ids)):06d}" if m == C.SPECIAL_MODEL else f"LOT-{int(next(lot_ids)):06d}")
            qty = int(round(C.START_QTY[m] * rng.normal(1, 0.05)))
            for s, st in enumerate(C.STATIONS):
                p = C.BASE_NG[s] * C.MODEL_FACTOR[m] * noise[s] * C.NG_SCALE
                ng = int(rng.binomial(qty, min(p, 0.5)))
                cds = by_station[s]
                w = np.array([c[4] for c in cds])
                split = rng.multinomial(ng, w / w.sum())
                emp, name = pool[(s, j)][week % len(pool[(s, j)])]
                rows.append([day.date(), sh, st, m, emp, name, lot_no, cust, qty, ng])
                for c, q in zip(cds, split):
                    if q:
                        dlog.append([day.date(), sh, st, m, c[0], int(q)])
                qty -= ng
prod = pd.DataFrame(rows, columns=["date", "shift", "station", "model", "employee_id", "operator_name",
                                   "lot_no", "customer_name", "input_qty", "ng_qty"])
defects = pd.DataFrame(dlog, columns=["date", "shift", "station", "model", "defect_code", "qty"])

# --- catatan bebas: sebagian kecil memuat nama operator + telepon, nama depan + telepon, atau nama customer
notes, kind = [], []
for i in range(len(prod)):
    r, ng = rng.random(), prod.at[i, "ng_qty"]
    full = prod.at[i, "operator_name"]
    if ng > 0 and r < C.P_NOTE_FULLNAME_PHONE:
        notes.append(f"dicek ulang oleh {full}, hub {fake.phone_number()}"); kind.append("fullname_phone")
    elif ng > 0 and r < C.P_NOTE_FULLNAME_PHONE + C.P_NOTE_FIRSTNAME_PHONE:
        notes.append(f"{full.split()[0]} yang menangani, telp {fake.phone_number()}"); kind.append("firstname_phone")
    elif ng > 0 and r < C.P_NOTE_FULLNAME_PHONE + C.P_NOTE_FIRSTNAME_PHONE + C.P_NOTE_CUSTOMER:
        notes.append(f"lot dikembalikan ke {prod.at[i, 'customer_name']}"); kind.append("customer")
    else:
        notes.append(C.SAFE_NOTES[int(rng.integers(0, len(C.SAFE_NOTES)))]); kind.append("safe")
prod["note"] = notes
kind = np.array(kind)

# --- data kotor: penulisan nama operator berbeda (spasi ekstra, huruf besar/kecil)
dirty_idx = np.where(rng.random(len(prod)) < C.P_DIRTY_NAME)[0]
for i in dirty_idx:
    nm, v = prod.at[i, "operator_name"], int(rng.integers(0, 3))
    prod.at[i, "operator_name"] = ("  " + nm.replace(" ", "  ") + " ") if v == 0 else (nm.upper() if v == 1 else nm.lower())

C.RAW_DIR.mkdir(parents=True, exist_ok=True)
prod.to_csv(C.RAW_DIR / "production_identified.csv", index=False)
defects.to_csv(C.RAW_DIR / "defect_log.csv", index=False)
pd.DataFrame([(d[0], d[1], C.STATIONS[d[2]], d[3]) for d in C.DEFECTS],
             columns=["defect_code", "defect_name", "station", "category"]).to_csv(C.RAW_DIR / "dim_defect.csv", index=False)

stn = prod.groupby("station").agg(ng=("ng_qty", "sum"), inp=("input_qty", "sum"))
stn["rate"] = stn.ng / stn.inp
top3 = stn.sort_values("rate", ascending=False).index[:3].tolist()
gt = {"seed": C.SEED, "version": C.DATA_VERSION, "faker_version": __import__("faker").VERSION, "faker_locale": "id_ID",
      "n_rows": len(prod), "n_days": C.N_DAYS, "n_operators": n_operators, "n_customers": len(customers),
      "n_lots": int(prod.lot_no.nunique()),
      "direct_identifier_columns": ["employee_id", "operator_name", "customer_name"],
      "singleton_cell": {"station": C.STATIONS[C.SINGLETON_CELL[0]], "shift": C.SHIFTS[C.SINGLETON_CELL[1]]},
      "rows_note_fullname_phone": int((kind == "fullname_phone").sum()),
      "rows_note_firstname_phone": int((kind == "firstname_phone").sum()),
      "rows_note_customer": int((kind == "customer").sum()),
      "rows_lot_contains_customer": int((prod.model == C.SPECIAL_MODEL).sum()), "special_model": C.SPECIAL_MODEL,
      "worst_station_planted": C.STATIONS[int(np.argmax(C.BASE_NG))], "worst_station_observed": top3[0], "top3_worst_stations": top3,
      "dirty_name_rows": int(len(dirty_idx)), "distinct_name_strings": int(prod.operator_name.nunique()),
      "note_leak_row_ids": [int(i) for i in np.where(kind != "safe")[0]]}
C.GROUND_TRUTH.write_text(json.dumps(gt, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"production_identified {len(prod)} baris, {n_operators} operator, catatan bocor {int((kind != 'safe').sum())}, "
      f"nama kotor {len(dirty_idx)}, string nama berbeda {gt['distinct_name_strings']}, stasiun terburuk {top3[0]}")
