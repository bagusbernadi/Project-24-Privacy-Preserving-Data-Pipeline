"""Tahap 1 / langkah 02: klasifikasi kolom (Q1) dan profil data asli (jumlah baris, operator, nama kotor, kebocoran).
Hasil: results/1-data-preparation/column_classification.csv, data_profile.csv, name_variants.csv."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from pipeline.anonymize import load_policy, normalize_name  # noqa: E402
from pipeline.scan import from_raw  # noqa: E402

pol = load_policy(C.COLUMN_POLICY)
raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
defects = pd.read_csv(C.RAW_DIR / "defect_log.csv")
sc = from_raw(raw)
frames = {"production": raw, "defect_log": defects}

rows = []
for tbl, cols in pol["tables"].items():
    df = frames[tbl]
    for col, spec in cols.items():
        s = df[col]
        hits = ""
        if col in ("operator_name", "employee_id", "customer_name", "lot_no", "note"):
            counts, nrows = sc.scan(s)
            hits = nrows if col != "lot_no" else int((s.str.split("-").str[0] != "LOT").sum())   # lot: awalan kode bukan LOT = memuat nama customer
        rows.append([tbl, col, spec["class"], spec["method"], spec["output"] or "(dihapus)", spec["why"], int(s.nunique()),
                     round(float(s.isna().mean()), 6), hits])
cc = pd.DataFrame(rows, columns=["table", "column", "class", "method", "output", "why", "n_unique", "pct_null", "rows_with_identity"])
cc.to_csv(C.RES_PREP / "column_classification.csv", index=False)

# varian penulisan nama operator: satu orang bisa punya beberapa penulisan
raw["_n"] = raw["operator_name"].map(normalize_name)
var = raw.groupby("_n")["operator_name"].agg(n_strings="nunique", n_rows="size").reset_index(drop=True)
var.to_csv(C.RES_PREP / "name_variants.csv", index=False)
canon = raw.groupby("_n")["operator_name"].agg(lambda x: x.value_counts().index[0])
dirty_rows = int((raw["operator_name"] != raw["_n"].map(canon)).sum())
special = raw[raw.model == C.SPECIAL_MODEL]
lot_with_cust = int((special.lot_no.str.split("-").str[0] != "LOT").sum())   # kode lot model khusus berawalan nama customer, bukan LOT
note_counts, note_rows = sc.scan(raw["note"])
prof = [("baris produksi", len(raw)), ("baris defect_log", len(defects)), ("hari kerja", raw["date"].nunique()),
        ("operator (orang)", raw["_n"].nunique()), ("string nama operator berbeda", raw["operator_name"].nunique()),
        ("baris dengan penulisan nama kotor", dirty_rows), ("customer", raw["customer_name"].nunique()), ("lot", raw["lot_no"].nunique()),
        ("baris model khusus", len(special)), ("baris model khusus dengan nama customer di kode lot", lot_with_cust),
        ("catatan bebas dengan identitas", note_rows), ("catatan dengan nomor telepon", note_counts["phone"]),
        ("stasiun", raw["station"].nunique()), ("sel stasiun x shift", raw.groupby(["station", "shift"]).ngroups),
        ("sel dengan satu operator", int((raw.groupby(["station", "shift"])["_n"].nunique() == 1).sum()))]
pd.DataFrame(prof, columns=["item", "value"]).to_csv(C.RES_PREP / "data_profile.csv", index=False)
print(pd.DataFrame(prof, columns=["item", "value"]).to_string(index=False))
