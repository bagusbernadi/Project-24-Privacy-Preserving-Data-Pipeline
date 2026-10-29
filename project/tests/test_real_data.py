"""Tes pada data simulasi penuh (dilewati bila data/raw belum dibuat): kriteria keberhasilan Design."""
import json

import pandas as pd
import pytest

import common as C
import analysis_lib as A
from pipeline.anonymize import anonymize, get_key, load_policy, restore_lots
from pipeline.scan import from_raw

pytestmark = pytest.mark.skipif(not (C.RAW_DIR / "production_identified.csv").exists(), reason="data/raw belum dibuat")


@pytest.fixture(scope="module")
def full():
    pol = load_policy(C.COLUMN_POLICY)
    raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
    rdef = pd.read_csv(C.RAW_DIR / "defect_log.csv")
    a, ad, m, info = anonymize(raw, rdef, pol, b"kunci-uji-penuh", C.DATA_DATE)
    return raw, rdef, a, ad, m, info


def test_ground_truth_matches_data(full):
    raw, *_ = full
    gt = json.loads(C.GROUND_TRUTH.read_text())
    assert gt["n_rows"] == len(raw) and gt["version"] == C.DATA_VERSION
    assert gt["distinct_name_strings"] == raw.operator_name.nunique()
    assert gt["worst_station_observed"] == gt["worst_station_planted"]


def test_no_identity_left_anywhere(full):
    raw, rdef, a, ad, *_ = full
    sc = from_raw(raw)
    assert sc.scan_frame(a)["rows_hit"] == 0 and sc.scan_frame(ad)["rows_hit"] == 0


def test_k_min_at_least_5_on_tightest_combination(full):
    a = full[2]
    assert a.groupby(["week", "shift", "station", "model", "operator_code"]).size().min() >= C.K_TARGET


def test_kpi_ranking_and_pareto_identical(full):
    raw, rdef, a, ad, *_ = full
    r = raw.assign(input=raw.input_qty, ng=raw.ng_qty, operator=raw.operator_name)
    n = a.assign(input=a.input_index, ng=a.ng_index)
    assert abs(A.line_yield(r) - A.line_yield(n)) < 1e-6
    assert list(A.station_rates(r).index[:3]) == list(A.station_rates(n).index[:3])
    assert list(A.pareto(rdef).defect_code[:3]) == list(A.pareto(ad.assign(qty=ad.qty_index)).defect_code[:3])


def test_mapping_key_restores_all_lots(full):
    raw, _, a, _, m, _ = full
    assert (restore_lots(a, m).values == raw.lot_no.values).all()


def test_dictionary_attack_fails_on_hmac(full):
    import hashlib
    raw, _, a, *_ = full
    names = {" ".join(n.split()).casefold() for n in raw.operator_name}
    plain = {"OP-" + hashlib.sha256(n.encode()).hexdigest()[:8] for n in names}
    assert not (set(a.operator_code) & plain)
