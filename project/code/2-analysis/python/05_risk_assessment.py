"""Tahap 2 / langkah 05: uji risiko identifikasi ulang (Q2-Q4). Hasil: results/2-analysis/risk_*.csv.
Baris unik dan k-anonymity, serangan kamus (hash biasa vs HMAC), sisa nama/telepon di catatan, sel operator tunggal, serangan penyambungan."""
import hashlib
import re
import sys

import pandas as pd
from faker import Faker

import analysis_lib as A
from analysis_lib import C
from pipeline.anonymize import PHONE_RE, get_key, hmac_hex, load_policy, normalize_name
from pipeline.scan import from_raw

raw, rdef = A.load_raw()
anon, adef = A.load_anon()
gt = pd.read_json(C.GROUND_TRUTH, typ="series")
sc = from_raw(raw)

# --- 1. baris unik dan k minimum (Q2)
combos = [("QI dasar", ["shift", "station", "model"]), ("QI + waktu", ["T", "shift", "station", "model"]),
          ("QI + waktu + operator (terketat)", ["T", "shift", "station", "model", "operator"])]
rows = []
for name, cols in combos:
    b = A.group_sizes(raw.assign(T=raw["date"]), cols)
    a = A.group_sizes(anon.assign(T=anon["week"]), cols)
    rows.append([name, " + ".join(c.replace("T", "tanggal/minggu") for c in cols), b["n_rows"], b["n_groups"], b["pct_unique"], b["k_min"],
                 a["n_groups"], a["pct_unique"], a["k_min"], a["k_min"] >= C.K_TARGET])
pd.DataFrame(rows, columns=["combo", "columns", "n_rows", "groups_before", "pct_unique_before", "k_min_before", "groups_after", "pct_unique_after",
                            "k_min_after", "k_target_met"]).to_csv(C.RES_ANALYSIS / "risk_k_anonymity.csv", index=False)

# --- 2. serangan kamus (Q3): penyerang punya daftar nama (direktori karyawan + nama umum) dan mencoba skema pseudonym
fk = Faker("id_ID"); Faker.seed(C.SEED + 1)
cands = {normalize_name(fk.name()) for _ in range(C.N_CANDIDATE_NAMES)}
true_names = sorted(raw["operator"].unique())
cands |= set(true_names)
pol = load_policy(C.COLUMN_POLICY)
hexn = pol["settings"]["code_hex"]
naive = lambda n: "OP-" + hashlib.sha256(n.encode()).hexdigest()[:hexn]
naive_codes = {naive(n): n for n in true_names}
hm_codes = set(anon.loc[anon.operator_code != pol["settings"]["masked_operator_code"], "operator_code"])
dic = {naive(n): n for n in cands}
guess_keys = [b"", b"key", b"secret", b"password", b"admin", b"123456"]
guess_hits = 0
for kk in guess_keys:
    gd = {"OP-" + hmac_hex(kk, "operator", n, hexn): n for n in cands}
    guess_hits += len(hm_codes & set(gd))
att = [["SHA-256 tanpa kunci (hash biasa)", len(cands), len(naive_codes), len(set(naive_codes) & set(dic))],
       ["HMAC-SHA256 dengan kunci rahasia, penyerang memakai hash biasa", len(cands), len(hm_codes), len(hm_codes & set(dic))],
       ["HMAC-SHA256 dengan kunci rahasia, penyerang menebak 6 kunci umum", len(cands) * len(guess_keys), len(hm_codes), guess_hits]]
att = pd.DataFrame(att, columns=["scheme", "candidates", "operators_attacked", "recovered"])
att["recovery_rate"] = att.recovered / att.operators_attacked
att.to_csv(C.RES_ANALYSIS / "risk_dictionary_attack.csv", index=False)

# --- 3. catatan bebas (Q4): tiga cara pembersihan
notes = raw["note"]
full_re = re.compile("|".join(re.escape(n) for n in sorted(sc.full_names, key=len, reverse=True)), re.I)
cust_re = re.compile("|".join(re.escape(c) for c in sorted({normalize_name(c) for c in raw.customer_name.unique()}, key=len, reverse=True)), re.I)


def blacklist(t):
    t = PHONE_RE.sub("[telp]", t)
    t = full_re.sub("[nama]", t)
    return cust_re.sub("[customer]", t)


bl = notes.map(blacklist)
allow = {a.casefold() for a in pol["settings"]["note_allowlist"]}
al = anon["note_clean"]
nr = []
for method, ser in (("Tanpa pembersihan (data asli)", notes), ("Regex: telepon + nama lengkap + customer yang dikenal", bl), ("Allowlist frasa aman (dipakai pipeline)", al)):
    counts, nrows = sc.scan(ser)
    kept = int((ser == notes).sum()) if method != "Tanpa pembersihan (data asli)" else len(ser)
    nr.append([method, int(len(ser)), nrows, counts["phone"], counts["name"], counts["customer"], kept])
nr = pd.DataFrame(nr, columns=["method", "rows", "rows_with_identity", "rows_phone", "rows_name", "rows_customer", "rows_text_unchanged"])
nr.to_csv(C.RES_ANALYSIS / "risk_notes.csv", index=False)

# --- 4. pemindaian semua kolom teks pada data anonim dan data asli (kriteria: tidak ada identitas tersisa)
sr = []
for label, tables in (("sebelum", {"production": pd.read_csv(C.RAW_DIR / "production_identified.csv"), "defect_log": pd.read_csv(C.RAW_DIR / "defect_log.csv")}),
                      ("sesudah", {"production": pd.read_csv(C.ANON_DIR / "anonymized_production.csv"), "defect_log": pd.read_csv(C.ANON_DIR / "anonymized_defect_log.csv")})):
    for t, df in tables.items():
        tot = sc.scan_frame(df)
        sr.append([label, t, ",".join(c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])), tot["name"], tot["phone"], tot["employee_id"], tot["customer"], tot["rows_hit"]])
pd.DataFrame(sr, columns=["stage", "table", "text_columns", "name_hits", "phone_hits", "employee_id_hits", "customer_hits", "rows_hit"]).to_csv(C.RES_ANALYSIS / "risk_text_scan.csv", index=False)

# --- 5. sel stasiun x shift dengan operator tunggal, dan serangan penyambungan dengan daftar jaga
cell = raw.groupby(["station", "shift"])["operator"].nunique().rename("operators_before").reset_index()
vis = anon[anon.operator_code != pol["settings"]["masked_operator_code"]].groupby(["station", "shift"])["operator_code"].nunique().rename("codes_visible_after").reset_index()
cell = cell.merge(vis, how="left").fillna({"codes_visible_after": 0})
cell["codes_visible_after"] = cell["codes_visible_after"].astype(int)
cell["masked"] = cell.codes_visible_after == 0
cell["single_person_identifiable_before"] = cell.operators_before == 1
cell["single_person_identifiable_after"] = (cell.operators_before == 1) & ~cell.masked
cell.to_csv(C.RES_ANALYSIS / "risk_operator_cells.csv", index=False)

n_op = raw["operator"].nunique()
n_visible = anon.loc[anon.operator_code != pol["settings"]["masked_operator_code"], "operator_code"].nunique()
# penyerang yang punya daftar jaga (siapa bertugas di stasiun x shift x minggu) menyambung kode ke orang: tiap sel-minggu hanya satu orang
cw = anon[anon.operator_code != pol["settings"]["masked_operator_code"]].groupby(["week", "station", "shift"])["operator_code"].nunique()
link = [["Tahu satu-satunya orang di sel stasiun x shift (tanpa minggu)", n_op, int(cell.single_person_identifiable_before.sum()), int(cell.single_person_identifiable_after.sum())],
        ["Tahu daftar jaga mingguan lengkap (stasiun x shift x minggu)", n_op, n_op, n_visible if int(cw.max()) == 1 else -1]]
pd.DataFrame(link, columns=["attacker_knowledge", "operators", "codes_linked_before", "codes_linked_after"]).assign(
    rate_before=lambda d: d.codes_linked_before / d.operators, rate_after=lambda d: d.codes_linked_after / d.operators).to_csv(C.RES_ANALYSIS / "risk_linkage.csv", index=False)
for f in ("risk_k_anonymity", "risk_dictionary_attack", "risk_notes", "risk_text_scan", "risk_linkage"):
    print(f); print(pd.read_csv(C.RES_ANALYSIS / f"{f}.csv").to_string(index=False))
