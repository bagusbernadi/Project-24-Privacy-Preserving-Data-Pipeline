"""Tahap 2 / langkah 09: uji deterministik (Q9), uji pemulihan mapping key (Q12), dan uji normalisasi nama. Hasil: results/2-analysis/validation_*.csv."""
import hashlib
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import analysis_lib as A
from analysis_lib import C
from pipeline.anonymize import anonymize, get_key, hmac_hex, load_policy, restore_lots, run

pol = load_policy(C.COLUMN_POLICY)
key = get_key(pol, C.ROOT)
raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
rdef = pd.read_csv(C.RAW_DIR / "defect_log.csv")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
checks = []

# --- Q9: deterministik dengan kunci yang sama (dua kali jalan di folder sementara, bandingkan SHA-256 file)
with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
    for t in (t1, t2):
        run(C.ROOT, C.RAW_DIR, Path(t) / "anon", Path(t) / "private", C.COLUMN_POLICY, C.DATA_DATE)
    names = ["anonymized_production.csv", "anonymized_defect_log.csv"]
    same_files = sum(sha(Path(t1) / "anon" / n) == sha(Path(t2) / "anon" / n) for n in names)
    same_map = int(sha(Path(t1) / "private" / "mapping_key.csv") == sha(Path(t2) / "private" / "mapping_key.csv"))
checks.append(["Q9", "Output sama persis pada dua kali jalan dengan kunci yang sama (file anonim)", len(names), same_files])
checks.append(["Q9", "Mapping key sama persis pada dua kali jalan dengan kunci yang sama", 1, same_map])

# --- kunci berbeda: kode berubah, hasil analisis sama
a1, d1, m1, _ = anonymize(raw, rdef, pol, key, C.DATA_DATE)
a2, d2, m2, _ = anonymize(raw, rdef, pol, b"kunci-lain-untuk-uji", C.DATA_DATE)
vis = a1.operator_code != pol["settings"]["masked_operator_code"]
checks.append(["Q9", "Kode operator berubah semua saat kunci diganti (baris dengan kode berbeda)", int(vis.sum()), int((a1.operator_code[vis] != a2.operator_code[vis]).sum())])
checks.append(["Q9", "Yield lini sama saat kunci diganti (selisih di bawah 1e-6)", 1, int(abs(A.line_yield(a1.assign(input=a1.input_index, ng=a1.ng_index)) - A.line_yield(a2.assign(input=a2.input_index, ng=a2.ng_index))) < 1e-6)])

# --- Q12: pemulihan oleh pemegang mapping key
lots_back = restore_lots(a1, m1)
checks.append(["Q12", "Kode lot dikembalikan ke nilai asli (baris)", len(raw), int((lots_back.values == raw.lot_no.values).sum())])
op_map = m1[m1.column == "operator"].set_index("code")["original_value"]
op_back = a1.operator_code.map(op_map)
checks.append(["Q12", "Kode operator terlihat dikembalikan ke nomor karyawan asli (baris)", int(vis.sum()), int((op_back[vis].values == raw.employee_id[vis].values).sum())])
base = float(m1[m1.column == "scale_base"].original_value.iloc[0])
checks.append(["Q12", "Indeks produksi dikembalikan ke jumlah asli dengan nilai dasar (baris x kolom)", len(raw) * 2,
               int((np.rint(a1.input_index * base / 100) == raw.input_qty).sum() + (np.rint(a1.ng_index * base / 100) == raw.ng_qty).sum())])
checks.append(["Q12", "Indeks defect dikembalikan ke jumlah asli (baris)", len(rdef), int((np.rint(d1.qty_index * base / 100) == rdef.qty).sum())])

# --- file baru: lot lama tetap memakai kode lama, lot baru mendapat kode baru yang belum terpakai
ex = {"lot": dict(zip(m1[m1.column == "lot"].original_value, m1[m1.column == "lot"].code))}
extra = raw.iloc[:1].assign(lot_no="LOT-999999")
a3, _, m3, _ = anonymize(pd.concat([raw, extra], ignore_index=True), rdef, pol, key, C.DATA_DATE, ex)
lm3 = dict(zip(m3[m3.column == "lot"].original_value, m3[m3.column == "lot"].code))
checks.append(["Q12", "Lot lama tetap memakai kode lama saat ada file baru (lot)", len(ex["lot"]), sum(lm3[k] == v for k, v in ex["lot"].items())])
checks.append(["Q12", "Lot baru mendapat kode baru yang tidak bentrok (lot)", 1, int(lm3["LOT-999999"] not in set(ex["lot"].values()))])
v = pd.DataFrame(checks, columns=["question", "check", "n_tested", "n_pass"])
v["result"] = np.where(v.n_tested == v.n_pass, "lulus", "gagal")
v.to_csv(C.RES_ANALYSIS / "validation_checks.csv", index=False)

# --- normalisasi nama: satu orang satu kode
norm = raw.operator_name.map(lambda s: " ".join(s.split()).casefold())
by_raw = raw.assign(code=raw.operator_name.map(lambda s: hmac_hex(key, "operator", s, pol["settings"]["code_hex"])))
by_norm = raw.assign(code=norm.map(lambda s: hmac_hex(key, "operator", s, pol["settings"]["code_hex"])))
nn = []
for label, d in (("HMAC pada nama apa adanya", by_raw), ("HMAC pada nama yang dinormalkan (dipakai pipeline)", by_norm)):
    per = d.assign(person=raw.employee_id).groupby("person")["code"].nunique()
    nn.append([label, int(d.code.nunique()), int(raw.employee_id.nunique()), int((per > 1).sum()), int(per.max())])
pd.DataFrame(nn, columns=["scheme", "distinct_codes", "persons", "persons_with_multiple_codes", "max_codes_per_person"]).to_csv(C.RES_ANALYSIS / "validation_name_normalization.csv", index=False)
print(v.to_string(index=False)); print(pd.read_csv(C.RES_ANALYSIS / "validation_name_normalization.csv").to_string(index=False))
