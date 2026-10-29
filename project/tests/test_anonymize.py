"""Tes pipeline anonymization: kebocoran, deterministik, pemulihan mapping key, kebijakan kolom, berkas rahasia."""
import subprocess

import pandas as pd
import pytest

import common as C
from pipeline.anonymize import (PHONE_RE, anonymize, build_lot_mapping, clean_note, hmac_hex, iso_week, normalize_name, restore_lots)
from pipeline.scan import from_raw

KEY = b"kunci-uji"


def test_normalize_name_unifies_variants():
    v = ["Ani Lestari", "  ani  lestari ", "ANI LESTARI", "ani lestari"]
    assert len({normalize_name(x) for x in v}) == 1


def test_hmac_depends_on_key_and_is_deterministic():
    a = hmac_hex(KEY, "operator", "ani lestari", 8)
    assert a == hmac_hex(KEY, "operator", "ani lestari", 8)
    assert a != hmac_hex(b"kunci-lain", "operator", "ani lestari", 8)
    import hashlib
    assert a != hashlib.sha256(b"ani lestari").hexdigest()[:8]


def test_iso_week_and_granularity():
    s = pd.Series(["2026-03-02", "2026-03-06", "2026-03-09"])
    assert list(iso_week(s)) == ["2026-W10", "2026-W10", "2026-W11"]
    assert list(iso_week(s, "month")) == ["2026-03"] * 3


@pytest.mark.parametrize("t", ["hub 0812 3456 7890", "telp (0451) 345 3216", "hubungi +62 812-3456-7890", "wa 081234567890"])
def test_phone_regex_matches(t):
    assert PHONE_RE.search(t)


@pytest.mark.parametrize("t", ["2026-W10", "LOT-12345", "normal", "ng 12 pcs", "tanggal 2026-03-02"])
def test_phone_regex_ignores_other_numbers(t):
    assert not PHONE_RE.search(t)


def test_clean_note_is_default_deny():
    allow = {"normal", "cek ulang"}
    assert clean_note("Normal", allow, "[x]") == "Normal"
    assert clean_note("normal, hub Budi 0812 3456 7890", allow, "[x]") == "[x]"
    assert clean_note("Budi yang menangani", allow, "[x]") == "[x]"


def test_lot_mapping_unique_deterministic_and_extendable():
    m1 = build_lot_mapping(["A", "B", "C"], KEY, "LOT-")
    assert len(set(m1.values())) == 3 and m1 == build_lot_mapping(["C", "B", "A"], KEY, "LOT-")
    m2 = build_lot_mapping(["A", "B", "C", "D"], KEY, "LOT-", m1)
    assert all(m2[k] == v for k, v in m1.items()) and m2["D"] not in m1.values()
    assert m1 != build_lot_mapping(["A", "B", "C"], b"kunci-lain", "LOT-")


def test_anonymize_removes_identity_and_columns(tiny, policy):
    raw, d = tiny
    a, ad, m, info = anonymize(raw, d, policy, KEY, "2026-10-29")
    assert not ({"employee_id", "operator_name", "customer_name", "date", "lot_no", "note"} & set(a.columns))
    assert list(a.columns) == ["week", "shift", "station", "model", "operator_code", "lot_code", "input_index", "ng_index", "ng_rate", "note_clean"]
    sc = from_raw(raw)
    assert sc.scan_frame(a)["rows_hit"] == 0 and sc.scan_frame(ad)["rows_hit"] == 0
    assert sc.scan(raw["note"])[1] == 1                      # catatan asli memang bocor, catatan anonim tidak
    assert a.note_clean.iloc[1] == "[dihapus]"


def test_one_person_one_code_despite_dirty_names(tiny, policy):
    raw, d = tiny
    a, _, _, info = anonymize(raw, d, policy, KEY, "2026-10-29")
    assert raw.operator_name.nunique() == 6 and info["n_operator_codes"] == 5     # 5 orang; satu penulisan kotor
    assert a.loc[0, "operator_code"] == a.loc[a.index[(raw.operator_name == "Ani Lestari")][0], "operator_code"]


def test_single_person_cell_is_masked(tiny, policy):
    raw, d = tiny
    a, _, _, info = anonymize(raw, d, policy, KEY, "2026-10-29")
    cell = (raw["station"] == "B") & (raw["shift"] == "Shift 2")
    assert (a.loc[cell, "operator_code"] == "OP-MASKED").all() and not (a.loc[~cell, "operator_code"] == "OP-MASKED").any()
    assert info["masked_cells"] == 1


def test_scale_keeps_ratios_and_mean_is_100(tiny, policy):
    raw, d = tiny
    a, ad, m, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    assert abs(a.input_index.mean() - 100) < 1e-3
    assert ((a.ng_index / a.input_index) - raw.ng_qty / raw.input_qty).abs().max() < 1e-5
    base = float(m[m.column == "scale_base"].original_value.iloc[0])
    assert (round(a.input_index * base / 100) == raw.input_qty).all()


def test_deterministic_same_key_and_different_key_changes_codes(tiny, policy):
    raw, d = tiny
    a1, _, m1, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    a2, _, m2, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    pd.testing.assert_frame_equal(a1, a2)
    pd.testing.assert_frame_equal(m1, m2)
    a3, _, _, _ = anonymize(raw, d, policy, b"kunci-lain", "2026-10-29")
    vis = a1.operator_code != "OP-MASKED"
    assert (a1.operator_code[vis] != a3.operator_code[vis]).all()


def test_mapping_key_restores_all_lots(tiny, policy):
    raw, d = tiny
    a, _, m, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    assert (restore_lots(a, m).values == raw.lot_no.values).all()
    assert list(m.columns) == ["column", "code", "original_value", "created_at"]


def test_customer_name_in_special_lot_code_is_gone(tiny, policy):
    raw, d = tiny
    a, _, _, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    assert raw.lot_no.str.contains("WIJAYA").any() and not a.lot_code.str.contains("WIJAYA", case=False).any()
    assert a.lot_code.str.startswith("LOT-").all()


def test_k_anonymity_after_weekly_generalization(tiny, policy):
    raw, d = tiny
    a, _, _, _ = anonymize(raw, d, policy, KEY, "2026-10-29")
    k = a.groupby(["week", "shift", "station", "model", "operator_code"]).size().min()
    assert k >= 5


def test_policy_covers_every_raw_column(policy):
    raw_cols = pd.read_csv(C.RAW_DIR / "production_identified.csv", nrows=1).columns if (C.RAW_DIR / "production_identified.csv").exists() else None
    if raw_cols is None:
        pytest.skip("data/raw belum dibuat")
    assert set(raw_cols) == set(policy["tables"]["production"])
    assert set(pd.read_csv(C.RAW_DIR / "defect_log.csv", nrows=1).columns) == set(policy["tables"]["defect_log"])
    for t in policy["tables"].values():
        for spec in t.values():
            assert spec["class"] in {"direct", "quasi", "sensitive", "safe"} and spec["method"] in {"pseudonymize", "mapping_key", "generalize", "scale", "drop", "clean_text", "keep"}


@pytest.mark.parametrize("path", ["project/data/raw/x.csv", "project/data/private/mapping_key.csv", "project/data/private/hmac_key.txt", "project/data/anonymized/a.csv", ".env", "project/privacy_pipeline.duckdb"])
def test_secret_paths_are_gitignored(path):
    r = subprocess.run(["git", "-C", str(C.ROOT.parent), "check-ignore", "-q", path])
    assert r.returncode == 0, f"{path} tidak diabaikan .gitignore"


def test_ground_truth_and_policy_not_ignored():
    for path in ("project/data/ground_truth.json", "project/config/column_policy.yaml"):
        assert subprocess.run(["git", "-C", str(C.ROOT.parent), "check-ignore", "-q", path]).returncode == 1
