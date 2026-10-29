"""Pipeline anonymization: menjalankan kebijakan kolom (config/column_policy.yaml) pada data produksi.

Lima metode: Pseudonymization (HMAC-SHA256), Mapping Key, Generalisasi tanggal, Skala angka (indeks), Hapus info sensitif.
Kunci HMAC dibaca dari environment (ANON_HMAC_KEY) atau data/private/hmac_key.txt; mapping key ditulis ke data/private/.
Keduanya tidak boleh di-commit. Contoh: python3 -m pipeline.anonymize  (dari folder code/1-data-preparation/python)
"""
import hashlib
import hmac
import os
import re
import secrets
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

PHONE_RE = re.compile(r"(?:\+?62|\(?0)[\s\-\(\)\.]*\d(?:[\s\-\(\)\.]*\d){7,12}")
MAP_COLS = ["column", "code", "original_value", "created_at"]


def load_policy(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def get_key(policy, root):
    """Kunci HMAC: dari environment; bila kosong dari file private; bila tidak ada dibuat acak dan disimpan di file private."""
    s = policy["settings"]
    env = os.environ.get(s["hmac_key_env"], "").strip()
    if env:
        return env.encode()
    f = Path(root) / s["hmac_key_file"]
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(secrets.token_hex(32), encoding="utf-8")
        os.chmod(f, 0o600)
    return f.read_text(encoding="utf-8").strip().encode()


def normalize_name(s):
    """Spasi ekstra dibuang dan huruf besar/kecil diseragamkan agar satu orang hanya mendapat satu kode."""
    return " ".join(str(s).split()).casefold()


def hmac_hex(key, kind, value, n):
    return hmac.new(key, f"{kind}|{value}".encode(), hashlib.sha256).hexdigest()[:n]


def iso_week(dates, granularity="week"):
    d = pd.to_datetime(dates)
    if granularity == "day":
        return d.dt.strftime("%Y-%m-%d")
    if granularity == "month":
        return d.dt.strftime("%Y-%m")
    iso = d.dt.isocalendar()
    return iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)


def clean_note(note, allow, replacement):
    """Default-deny: catatan hanya dipertahankan bila persis sama dengan frasa yang diizinkan."""
    return note if str(note).strip().casefold() in allow else replacement


def build_lot_mapping(lots, key, prefix, existing=None):
    """Mapping key: kode lot acak (urutan dikocok dengan seed dari kunci). Lot yang sudah ada tetap memakai kodenya."""
    existing = dict(existing or {})
    used = {int(v[len(prefix):]) for v in existing.values()}
    seed = int.from_bytes(hashlib.sha256(key + b"|lot-order").digest()[:8], "big")
    pool = [int(x) for x in np.random.default_rng(seed).permutation(99_999) + 1 if int(x) not in used]
    for lot in sorted(set(lots) - set(existing)):
        existing[lot] = f"{prefix}{pool.pop(0):05d}"
    return existing


def anonymize(raw, defects, policy, key, created_at, existing_map=None):
    """Kembalikan (production_anon, defect_anon, mapping_key_df, info)."""
    s = policy["settings"]
    out = pd.DataFrame(index=raw.index)
    out["week"] = iso_week(raw["date"], s["date_granularity"])
    out["shift"], out["station"], out["model"] = raw["shift"], raw["station"], raw["model"]

    norm = raw["operator_name"].map(normalize_name)
    code = norm.map(lambda v: s["code_prefix_operator"] + hmac_hex(key, "operator", v, s["code_hex"]))
    # sel (stasiun, shift) dengan operator terlalu sedikit: kode operator ditutup agar tidak bisa dicocokkan dengan daftar jaga
    per_cell = norm.groupby([raw["station"], raw["shift"]]).transform("nunique")
    masked = per_cell < s["min_operators_per_cell"]
    out["operator_code"] = code.where(~masked, s["masked_operator_code"])

    lot_map = build_lot_mapping(raw["lot_no"].unique(), key, s["lot_prefix"], (existing_map or {}).get("lot"))
    out["lot_code"] = raw["lot_no"].map(lot_map)

    base = round(float(raw["input_qty"].mean()), s["index_decimals"])
    k = s["index_base"] / base
    d = s["index_decimals"]
    out["input_index"] = (raw["input_qty"] * k).round(d)
    out["ng_index"] = (raw["ng_qty"] * k).round(d)
    out["ng_rate"] = (raw["ng_qty"] / raw["input_qty"]).round(d)
    allow = {a.casefold() for a in s["note_allowlist"]}
    out["note_clean"] = raw["note"].map(lambda v: clean_note(v, allow, s["note_replacement"]))

    dout = pd.DataFrame({"week": iso_week(defects["date"], s["date_granularity"]), "shift": defects["shift"], "station": defects["station"],
                         "model": defects["model"], "defect_code": defects["defect_code"], "qty_index": (defects["qty"] * k).round(d)})

    emp = raw.assign(_n=norm).groupby("_n")["employee_id"].agg(lambda x: sorted(set(x)))
    assert emp.map(len).eq(1).all(), "satu nama dengan lebih dari satu employee_id"
    op_rows = sorted({("operator", c, emp[n][0], created_at) for n, c in zip(norm, code)})
    mapping = pd.DataFrame([("lot", t, o, created_at) for o, t in sorted(lot_map.items())] + op_rows + [("scale_base", "index100", base, created_at)], columns=MAP_COLS)
    assert code.nunique() == norm.nunique(), "tabrakan kode HMAC"
    info = {"base": base, "masked_rows": int(masked.sum()), "masked_cells": int(masked.groupby([raw["station"], raw["shift"]]).first().sum()),
            "n_operator_codes": int(code.nunique())}
    return out, dout, mapping, info


def restore_lots(anon, mapping):
    """Pemegang mapping key: kode lot -> nilai asli."""
    m = mapping[mapping.column == "lot"].set_index("code")["original_value"]
    return anon["lot_code"].map(m)


def run(root, raw_dir, anon_dir, private_dir, policy_path, created_at):
    root = Path(root)
    policy = load_policy(policy_path)
    key = get_key(policy, root)
    raw = pd.read_csv(Path(raw_dir) / "production_identified.csv")
    defects = pd.read_csv(Path(raw_dir) / "defect_log.csv")
    existing = None
    mk = Path(private_dir) / "mapping_key.csv"
    if mk.exists():
        old = pd.read_csv(mk, dtype=str)
        existing = {"lot": dict(zip(old[old.column == "lot"].original_value, old[old.column == "lot"].code))}
    prod, dlog, mapping, info = anonymize(raw, defects, policy, key, created_at, existing)
    Path(anon_dir).mkdir(parents=True, exist_ok=True)
    Path(private_dir).mkdir(parents=True, exist_ok=True)
    prod.to_csv(Path(anon_dir) / "anonymized_production.csv", index=False)
    dlog.to_csv(Path(anon_dir) / "anonymized_defect_log.csv", index=False)
    mapping.to_csv(mk, index=False)
    return prod, dlog, mapping, info


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    import common as C
    _, _, _, info = run(C.ROOT, C.RAW_DIR, C.ANON_DIR, C.PRIVATE_DIR, C.COLUMN_POLICY, C.DATA_DATE)
    print("anonymized", info)
