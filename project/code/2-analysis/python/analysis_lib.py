"""Fungsi bersama tahap analisis Project 24: memuat data asli/anonim dengan kolom seragam, KPI, dan ukuran risiko (pandas)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "1-data-preparation" / "python"))
import common as C  # noqa: E402
from pipeline.anonymize import iso_week, normalize_name  # noqa: E402

FIRST, LAST = C.STATIONS[0], C.STATIONS[-1]


def load_raw():
    """Data asli (identitas palsu): kolom seragam week, operator (nama dinormalkan), input, ng + date."""
    p = pd.read_csv(C.RAW_DIR / "production_identified.csv")
    p["week"] = iso_week(p["date"])
    p["operator"] = p["operator_name"].map(normalize_name)
    p["input"], p["ng"] = p["input_qty"], p["ng_qty"]
    d = pd.read_csv(C.RAW_DIR / "defect_log.csv")
    d["week"] = iso_week(d["date"])
    return p, d


def load_anon():
    p = pd.read_csv(C.ANON_DIR / "anonymized_production.csv")
    p["operator"], p["input"], p["ng"] = p["operator_code"], p["input_index"], p["ng_index"]
    d = pd.read_csv(C.ANON_DIR / "anonymized_defect_log.csv")
    d["qty"] = d["qty_index"]
    return p, d


def line_yield(df, key=None):
    """Yield lini = barang baik di stasiun terakhir / input di stasiun pertama (opsional per kelompok key)."""
    good = df[df.station == LAST].assign(good=lambda x: x.input - x.ng)
    start = df[df.station == FIRST]
    if key is None:
        return float(good.good.sum() / start.input.sum())
    return (good.groupby(key)["good"].sum() / start.groupby(key)["input"].sum()).sort_index()


def station_rates(df):
    g = df.groupby("station")[["ng", "input"]].sum()
    return (g.ng / g.input).sort_values(ascending=False, kind="stable")


def pareto(d):
    g = d.groupby("defect_code")["qty"].sum().reset_index()
    return g.sort_values(["qty", "defect_code"], ascending=[False, True], kind="stable").reset_index(drop=True)


def group_sizes(df, cols):
    n = df.groupby(cols).size()
    return {"n_rows": int(len(df)), "n_groups": int(len(n)), "k_min": int(n.min()), "k_median": float(n.median()),
            "pct_unique": float((n[n == 1].sum()) / len(df))}


def slope(values):
    """Kemiringan regresi linear deret (poin persentase per titik waktu)."""
    x = np.arange(len(values), dtype=float)
    return float(np.polyfit(x, np.asarray(values, float) * 100, 1)[0])
