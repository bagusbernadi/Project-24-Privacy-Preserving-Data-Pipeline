"""Pemindai identitas di teks: nomor telepon, nomor karyawan, nama orang (lengkap atau bagian nama), nama customer.
Dipakai tes dan uji risiko; pemindai ini terpisah dari pembersih catatan (allowlist) supaya hasilnya bisa menjadi pemeriksaan independen."""
import re

import pandas as pd

from .anonymize import PHONE_RE, normalize_name

EMP_RE = re.compile(r"\bEMP-\d{3,}\b", re.I)
TITLE_TOKENS = {"drs", "dra", "prof", "hj", "haji", "tbk", "persero", "perum"}


def _tokens(text, min_len=4):
    return {t for t in re.findall(r"[a-z]+", normalize_name(text)) if len(t) >= min_len and t not in TITLE_TOKENS}


class Scanner:
    def __init__(self, operator_names, customers):
        names = {normalize_name(n) for n in operator_names}
        self.full_names = names
        self.name_tokens = set().union(*(_tokens(n) for n in names))
        self.customers = {normalize_name(c) for c in customers}
        self.customer_tokens = set().union(*(_tokens(c) for c in customers)) - self.name_tokens

    def kinds(self, text):
        t = normalize_name(text)
        out = set()
        if PHONE_RE.search(str(text)):
            out.add("phone")
        if EMP_RE.search(str(text)):
            out.add("employee_id")
        words = set(re.findall(r"[a-z]+", t))
        if any(n in t for n in self.full_names) or (words & self.name_tokens):
            out.add("name")
        if any(c in t for c in self.customers) or (words & self.customer_tokens):
            out.add("customer")
        return out

    def scan(self, series):
        """Hitung baris yang memuat tiap jenis identitas; kembalikan (dict hitungan, jumlah baris terkena)."""
        k = series.fillna("").astype(str).map(self.kinds)
        counts = {x: int(k.map(lambda s: x in s).sum()) for x in ("phone", "employee_id", "name", "customer")}
        return counts, int(k.map(bool).sum())

    def scan_frame(self, df):
        """Pindai semua kolom teks (object) pada DataFrame; kembalikan total hitungan per jenis."""
        tot = {"phone": 0, "employee_id": 0, "name": 0, "customer": 0, "rows_hit": 0}
        for c in df.columns:
            if not pd.api.types.is_numeric_dtype(df[c]):
                counts, rows = self.scan(df[c])
                for k2, v in counts.items():
                    tot[k2] += v
                tot["rows_hit"] += rows
        return tot


def from_raw(raw):
    return Scanner(raw["operator_name"].unique(), raw["customer_name"].unique())
