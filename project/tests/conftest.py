import sys
from pathlib import Path

import pandas as pd
import pytest

CODE = Path(__file__).resolve().parents[1] / "code"
for p in (CODE, CODE / "1-data-preparation" / "python", CODE / "2-analysis" / "python"):
    sys.path.insert(0, str(p))
import common as C  # noqa: E402
from pipeline.anonymize import load_policy  # noqa: E402


@pytest.fixture(scope="session")
def policy():
    return load_policy(C.COLUMN_POLICY)


@pytest.fixture()
def tiny():
    """Data kecil: 2 stasiun x 2 shift; sel (B, Shift 2) hanya satu operator; nama sengaja ditulis kotor."""
    rows = []
    for d in pd.bdate_range("2026-03-02", periods=10):
        for sh in ("Shift 1", "Shift 2"):
            for st in ("A", "B"):
                if st == "B" and sh == "Shift 2":
                    nm, emp = "Budi Santoso", "EMP-1"
                else:
                    wk = (d - pd.Timestamp("2026-03-02")).days // 7
                    nm, emp = (("Ani Lestari", "EMP-2") if wk % 2 == 0 else ("Citra Dewi", "EMP-3")) if st == "A" else (("Dedi Hartono", "EMP-4") if wk % 2 == 0 else ("Eko Wijaya", "EMP-5"))
                rows.append([d.date(), sh, st, "M1", emp, nm, "WIJAYA-000123" if st == "A" else "LOT-000456", "PT Wijaya Tbk", 100, 3, "normal"])
    raw = pd.DataFrame(rows, columns=["date", "shift", "station", "model", "employee_id", "operator_name", "lot_no", "customer_name", "input_qty", "ng_qty", "note"])
    raw.loc[0, "operator_name"] = "  ANI  LESTARI "
    raw.loc[1, "note"] = "dicek ulang oleh Ani Lestari, hub 0812 3456 7890"
    d = pd.DataFrame({"date": [raw.date[0]], "shift": ["Shift 1"], "station": ["A"], "model": ["M1"], "defect_code": ["X-01"], "qty": [3]})
    return raw, d
