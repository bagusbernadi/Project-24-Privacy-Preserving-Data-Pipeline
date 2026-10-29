"""Pengaturan bersama semua skrip Project 24. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi dengan identitas palsu (tidak di-commit)
PRIVATE_DIR = DATA / "private"                         # kunci HMAC dan mapping key (tidak di-commit)
ANON_DIR = DATA / "anonymized"                         # data anonim yang boleh dibagikan (tidak di-commit; dibuat ulang oleh pipeline)
GROUND_TRUTH = DATA / "ground_truth.json"              # di-commit (kecil, tanpa nama)
DB_PATH = ROOT / "privacy_pipeline.duckdb"
CODE = ROOT / "code"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
HTML_DIR = CODE / "3-presentation" / "html"
CONFIG_DIR = ROOT / "config"
COLUMN_POLICY = CONFIG_DIR / "column_policy.yaml"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RAW_DIR, PRIVATE_DIR, ANON_DIR, RES_PREP, RES_ANALYSIS, RES_PRESENT):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 24260302
DATA_VERSION = "v3"
DATA_DATE = "2026-10-29"       # tanggal data v3 dibuat (juga dipakai sebagai created_at mapping key)
START_DATE = "2026-03-02"      # Senin
N_DAYS = 75                    # hari kerja Senin-Jumat (15 minggu penuh)
MODELS = ["Matic 110", "Bebek 125", "Sport 150"]
SPECIAL_MODEL = "Sport 150"    # model pesanan khusus: kode lot memuat nama customer
SHIFTS = ["Shift 1", "Shift 2"]
STATIONS = ["Frame Welding", "Frame Painting", "Engine Assembly", "Wiring Harness Install",
            "Wheel & Suspension", "Body Panel Assembly", "Electrical Test", "Final Inspection",
            "Performance Test (Dyno)", "Packing"]
SINGLETON_CELL = (8, 1)        # (indeks stasiun, indeks shift): Performance Test (Dyno), Shift 2 = satu operator saja
# kode defect: (kode, nama, indeks stasiun, kategori, bobot di stasiun)
DEFECTS = [
    ("FWD-01", "Porositas las", 0, "Las", 0.55),
    ("FWD-02", "Dimensi frame meleset", 0, "Las", 0.45),
    ("PNT-01", "Cat tipis", 1, "Cat", 0.45),
    ("PNT-02", "Cat berkulit jeruk", 1, "Cat", 0.35),
    ("PNT-03", "Debu pada cat", 1, "Cat", 0.20),
    ("ENG-01", "Torsi baut kurang", 2, "Mesin", 0.50),
    ("ENG-02", "Rembes oli", 2, "Mesin", 0.50),
    ("WRH-01", "Konektor tidak masuk penuh", 3, "Kelistrikan", 0.60),
    ("WRH-02", "Kabel terjepit", 3, "Kelistrikan", 0.40),
    ("WHL-01", "Velg oleng", 4, "Roda", 0.50),
    ("WHL-02", "Suspensi bocor", 4, "Roda", 0.50),
    ("BDY-01", "Gores panel body", 5, "Body", 0.55),
    ("BDY-02", "Celah panel tidak rata", 5, "Body", 0.45),
    ("ELT-01", "Lampu tidak menyala", 6, "Kelistrikan", 0.45),
    ("ELT-02", "Starter gagal", 6, "Kelistrikan", 0.55),
    ("FIN-01", "Cacat kosmetik", 7, "Kosmetik", 0.60),
    ("FIN-02", "Stiker salah", 7, "Kosmetik", 0.40),
    ("DYN-01", "Akselerasi di bawah spec", 8, "Performa", 0.50),
    ("DYN-02", "Rem tidak sesuai tes", 8, "Performa", 0.50),
    ("PKG-01", "Label atau kemasan rusak", 9, "Label", 1.00),
]
BASE_NG = [0.014, 0.040, 0.013, 0.011, 0.012, 0.015, 0.018, 0.010, 0.016, 0.003]   # Frame Painting sengaja paling sering NG
NG_SCALE = 0.82
MODEL_FACTOR = {"Matic 110": 0.85, "Bebek 125": 1.00, "Sport 150": 1.25}
START_QTY = {"Matic 110": 300, "Bebek 125": 240, "Sport 150": 150}

# peluang kebocoran di catatan bebas (dari semua baris yang punya NG), data kotor nama, dan catatan aman
P_NOTE_FULLNAME_PHONE, P_NOTE_FIRSTNAME_PHONE, P_NOTE_CUSTOMER = 0.020, 0.008, 0.012
P_DIRTY_NAME = 0.025
SAFE_NOTES = ["cek ulang", "sesuai prosedur", "mesin dibersihkan", "material baru", "normal", "tanpa catatan"]

# ukuran privasi
K_TARGET = 5                   # k minimum yang diminta rancangan
MIN_OPERATORS_PER_CELL = 2     # sel (stasiun, shift) dengan operator lebih sedikit dari ini: kode operator ditutup
N_CANDIDATE_NAMES = 20000      # daftar nama yang dicoba penyerang pada uji serangan kamus

# asumsi dampak waktu (estimated, tidak diukur dengan stopwatch)
MANUAL_MINUTES_PER_FILE = 45   # asumsi: anonymization manual di Excel per file
FILES_PER_YEAR = 24            # asumsi: 2 file dibagikan per bulan


def load_sql(path):
    """Baca file SQL berisi blok '-- name: nama' menjadi dict nama -> query."""
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.startswith("-- name:"):
            cur = line.split(":", 1)[1].strip()
            out[cur] = []
        elif cur:
            out[cur].append(line)
    return {k: "\n".join(v).strip().rstrip(";") for k, v in out.items()}


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
