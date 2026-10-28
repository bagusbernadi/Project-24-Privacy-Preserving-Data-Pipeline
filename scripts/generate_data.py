"""Project 24: data produksi simulasi dengan identitas palsu (Faker, locale id_ID). Seed tetap.

Hasil (data/sim/): production_identified.csv (data "asli" simulasi, mengandung identitas palsu),
ground_truth.json (kebocoran yang sengaja ditanam). Data ini 100% karangan; HMAC key dan mapping untuk
anonymization dibuat di pipeline/, bukan di sini dan tidak pernah di-commit.
Jalankan: python scripts/generate_data.py   (versi data: v1; butuh Faker)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sim"
START_DATE = "2026-03-02"      # Senin
N_DAYS = 75                    # hari kerja Senin-Jumat
MODELS = ["Basic", "Plus", "Pro"]
SHIFTS = ["Shift 1", "Shift 2"]
STATIONS = ["Solder Paste Printing", "Component Placement", "Reflow Soldering", "AOI Inspection",
            "Board Test (ICT)", "Screen Assembly", "Housing Assembly", "Final Inspection",
            "Functional Test", "Packaging"]
# kode defect: (kode, nama, indeks stasiun, kategori, bobot di stasiun)
DEFECTS = [
    ("SPP-01", "Pasta solder kurang", 0, "Solder", 1.00),
    ("CPL-01", "Missing component", 1, "Komponen", 0.60),
    ("CPL-02", "Komponen terbalik", 1, "Komponen", 0.40),
    ("RFL-01", "Solder bridge", 2, "Solder", 0.68),
    ("RFL-02", "Cold solder", 2, "Solder", 0.32),
    ("AOI-01", "Komponen bergeser", 3, "Komponen", 1.00),
    ("ICT-01", "Short circuit", 4, "Elektrikal", 0.55),
    ("ICT-02", "Open circuit", 4, "Elektrikal", 0.45),
    ("SCR-01", "Layar retak", 5, "Layar", 0.50),
    ("SCR-02", "Dead pixel", 5, "Layar", 0.50),
    ("HSG-01", "Gores casing", 6, "Casing", 0.60),
    ("HSG-02", "Celah casing", 6, "Casing", 0.40),
    ("FIN-01", "Cacat kosmetik", 7, "Kosmetik", 1.00),
    ("FCT-01", "Kamera gagal tes", 8, "Fungsi", 0.40),
    ("FCT-02", "Sensor gagal tes", 8, "Fungsi", 0.35),
    ("FCT-03", "Baterai gagal tes", 8, "Fungsi", 0.25),
    ("PKG-01", "Label salah", 9, "Label", 1.00),
]
BASE_NG = [0.012, 0.011, 0.040, 0.008, 0.013, 0.010, 0.015, 0.012, 0.020, 0.003]
MODEL_FACTOR = {"Basic": 0.85, "Plus": 1.00, "Pro": 1.25}
START_QTY = {"Basic": 460, "Plus": 420, "Pro": 360}
OPERATOR = {(s, sh): f"OP{2 * s + j + 1:02d}" for s in range(len(STATIONS)) for j, sh in enumerate(SHIFTS)}
DATES = pd.bdate_range(START_DATE, periods=N_DAYS)


def make_production(rng, ng_scale=1.0, extra_factor=None):
    """Satu baris per tanggal x shift x model x stasiun (4.500 baris).

    extra_factor(t, station, model, shift) -> pengali peluang NG (untuk kejadian tertanam).
    Hasil: (prod, defect_log) tanpa data kotor.
    """
    by_station = {s: [d for d in DEFECTS if d[2] == s] for s in range(len(STATIONS))}
    prod, dlog = [], []
    for t, day in enumerate(DATES):
        noise = np.exp(rng.normal(0, 0.15, len(STATIONS)))
        for m in MODELS:
            for sh in SHIFTS:
                qty = int(round(START_QTY[m] * rng.normal(1, 0.05)))
                for s, st in enumerate(STATIONS):
                    p = BASE_NG[s] * MODEL_FACTOR[m] * noise[s] * ng_scale
                    if extra_factor:
                        p *= extra_factor(t, s, m, sh)
                    ng = int(rng.binomial(qty, min(p, 0.5)))
                    cds = by_station[s]
                    w = np.array([c[4] for c in cds])
                    split = rng.multinomial(ng, w / w.sum())
                    prod.append([day.date(), sh, st, m, OPERATOR[(s, sh)], qty, qty - ng, ng])
                    for c, q in zip(cds, split):
                        if q:
                            dlog.append([day.date(), sh, st, m, c[0], int(q)])
                    qty -= ng
    prod = pd.DataFrame(prod, columns=["date", "shift", "station", "model", "operator_id",
                                       "input_qty", "ok_first_pass", "ng_qty"])
    dlog = pd.DataFrame(dlog, columns=["date", "shift", "station", "model", "defect_code", "qty"])
    return prod, dlog


def write_reference():
    pd.DataFrame([(d[0], d[1], STATIONS[d[2]], d[3]) for d in DEFECTS],
                 columns=["defect_code", "defect_name", "station", "category"]).to_csv(OUT / "dim_defect.csv", index=False)
    pd.DataFrame({"station": STATIONS, "seq": range(1, len(STATIONS) + 1)}).to_csv(OUT / "dim_station.csv", index=False)
from faker import Faker

SEED = 24260302
DATA_VERSION = "v1"
rng = np.random.default_rng(SEED)
fake = Faker("id_ID")
Faker.seed(SEED)

OUT.mkdir(parents=True, exist_ok=True)
prod, dlog = make_production(rng, ng_scale=0.82)

# identitas palsu: 20 operator (nama), 12 customer (perusahaan), kode lot acak
op_names = {}
for key in sorted(set(OPERATOR.values())):
    op_names[key] = fake.name()
customers = [fake.company() for _ in range(12)]
prod["operator_name"] = prod["operator_id"].map(op_names)
prod["customer"] = [customers[int(i)] for i in rng.integers(0, len(customers), len(prod))]
prod["lot_code"] = [f"LOT-{int(x):06d}" for x in rng.integers(0, 1_000_000, len(prod))]

# catatan bebas: sebagian kecil mengandung nama orang, nomor telepon, atau lot (kebocoran sengaja)
NOTES_PLAIN = ["cek ulang", "sesuai prosedur", "mesin dibersihkan", "material baru", "normal", "tanpa catatan"]
notes, leak_rows = [], []
for i, ng in enumerate(prod["ng_qty"]):
    r = rng.random()
    if ng > 0 and r < 0.06:
        notes.append(f"ditangani {fake.first_name()} dari {fake.company()}, hub {fake.phone_number()}")
        leak_rows.append(i)
    elif ng > 0 and r < 0.12:
        notes.append(f"lot {prod.at[i, 'lot_code']} dikembalikan ke {customers[int(rng.integers(0, len(customers)))]}")
        leak_rows.append(i)
    else:
        notes.append(NOTES_PLAIN[int(rng.integers(0, len(NOTES_PLAIN)))])
prod["note"] = notes

# operator unik: satu operator hanya bertugas di satu stasiun/shift/model tertentu -> mudah diidentifikasi ulang
prod.to_csv(OUT / "production_identified.csv", index=False)
gt = {"seed": SEED, "version": DATA_VERSION, "faker_version": __import__("faker").VERSION, "faker_locale": "id_ID",
      "n_rows": len(prod), "rows_with_leaked_identity_in_note": len(leak_rows),
      "direct_identifier_columns": ["operator_name", "customer", "lot_code", "note"],
      "unique_operator_per_station_shift": True}
(OUT / "ground_truth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"production_identified {len(prod)} baris, catatan bocor {len(leak_rows)}")
