"""Tahap 2 / langkah 10: pindai berkas rahasia dan kebocoran identitas di repo (kriteria: tidak ada file rahasia di riwayat repositori).
Hasil: results/2-analysis/secret_scan.csv. Butuh git; dijalankan dari dalam repositori."""
import re
import subprocess

import pandas as pd

import analysis_lib as A
from analysis_lib import C
from pipeline.anonymize import PHONE_RE, get_key, load_policy, normalize_name

repo = subprocess.run(["git", "-C", str(C.ROOT), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
git = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
SECRET_PATH = re.compile(r"(^|/)(data/(raw|private|anonymized)/|\.env($|\.)|hmac_key|mapping_key|[^/]+\.duckdb$)")
tracked = git("ls-files").splitlines() + git("ls-files", "-o", "--exclude-standard").splitlines()   # termasuk berkas baru yang akan ikut di-commit
tracked = sorted({f for f in tracked if (C.ROOT.parent / f).exists()})
hist = {f for f in git("log", "--all", "--name-only", "--pretty=format:").splitlines() if f}
n_commits = len(git("log", "--all", "--pretty=format:%H").splitlines())

raw = pd.read_csv(C.RAW_DIR / "production_identified.csv")
pol = load_policy(C.COLUMN_POLICY)
key = get_key(pol, C.ROOT).decode()
tokens = {"nama operator": sorted({normalize_name(n) for n in raw.operator_name.unique()}),
          "nomor karyawan": sorted(raw.employee_id.unique()),
          "nama customer": sorted({normalize_name(c) for c in raw.customer_name.unique()}),
          "nomor telepon": sorted({m.group(0) for n in raw.note for m in PHONE_RE.finditer(n)}),
          "kunci HMAC": [key]}
private_files = [C.RAW_DIR / "production_identified.csv", C.PRIVATE_DIR / "mapping_key.csv", C.PRIVATE_DIR / "hmac_key.txt", C.DB_PATH, C.ANON_DIR / "anonymized_production.csv"]
ignored = [f for f in private_files if f.exists() and subprocess.run(["git", "-C", repo, "check-ignore", "-q", str(f)]).returncode == 0]

rows = [["Berkas rahasia ikut dilacak atau akan ikut di-commit", f"{len(tracked)} berkas", len(tracked), sum(bool(SECRET_PATH.search(f)) for f in tracked)],
        ["Berkas rahasia tidak diabaikan .gitignore", f"{sum(f.exists() for f in private_files)} berkas rahasia yang ada", sum(f.exists() for f in private_files),
         sum(f.exists() for f in private_files) - len(ignored)],
        ["Berkas rahasia pernah masuk riwayat commit", f"{n_commits} commit, semua cabang", len(hist), sum(bool(SECRET_PATH.search(f)) for f in hist)]]
for label, toks in tokens.items():
    hits = 0
    for f in tracked:
        p = C.ROOT.parent / f
        try:
            txt = p.read_text(encoding="utf-8", errors="strict").casefold() if p.stat().st_size < 5_000_000 else ""
        except (UnicodeDecodeError, OSError):
            continue
        hits += sum(t.casefold() in txt for t in toks)
    rows.append([f"{label} muncul di berkas repo", f"{len(tracked)} berkas x {len(toks)} nilai", len(tracked), hits])
sc = pd.DataFrame(rows, columns=["check", "scope", "n_checked", "hits"])
sc["result"] = ["lulus" if h == 0 else "gagal" for h in sc.hits]
sc.to_csv(C.RES_ANALYSIS / "secret_scan.csv", index=False)
print(sc.to_string(index=False))
