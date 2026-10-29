"""Tahap 1 / langkah 03: jalankan pipeline anonymization (satu perintah). Hasil: data/anonymized/*.csv, data/private/mapping_key.csv
(tidak di-commit) dan results/1-data-preparation/anonymize_summary.csv (ringkasan tanpa nilai rahasia)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from pipeline.anonymize import run  # noqa: E402

raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
prod, dlog, mapping, info = run(C.ROOT, C.RAW_DIR, C.ANON_DIR, C.PRIVATE_DIR, C.COLUMN_POLICY, C.DATA_DATE)
dropped = sorted(set(raw.columns) - {"date", "shift", "station", "model", "operator_name", "lot_no", "input_qty", "ng_qty", "note"})
summ = [("baris masuk", len(raw)), ("baris keluar", len(prod)), ("kolom masuk", raw.shape[1]), ("kolom keluar", prod.shape[1]),
        ("kolom dihapus", len(dropped)), ("kode operator unik", info["n_operator_codes"]), ("sel operator ditutup", info["masked_cells"]),
        ("baris operator ditutup", info["masked_rows"]), ("lot di mapping key", int((mapping.column == "lot").sum())),
        ("baris mapping key", len(mapping)), ("catatan dihapus", int((prod.note_clean == "[dihapus]").sum())),
        ("catatan dipertahankan", int((prod.note_clean != "[dihapus]").sum()))]
pd.DataFrame(summ, columns=["item", "value"]).to_csv(C.RES_PREP / "anonymize_summary.csv", index=False)
print(pd.DataFrame(summ, columns=["item", "value"]).to_string(index=False))
