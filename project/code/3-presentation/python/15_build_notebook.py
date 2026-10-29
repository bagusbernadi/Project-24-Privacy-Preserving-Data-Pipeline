"""Tahap 3 / langkah 15: buat dan jalankan notebook analisis Q1-Q12 (results/3-presentation/analysis.ipynb) dari CSV hasil."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

M, K = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    M("# Project 24: Privacy-Preserving Data Sharing Pipeline\n\nAnalisis Q1-Q12. Semua tabel dibaca dari `results/` (hasil skrip Python dan SQL). Data adalah simulasi dengan identitas palsu (Faker); "
      "data asli, mapping key, dan kunci HMAC tidak ada di repo."),
    K("""from pathlib import Path
import pandas as pd, matplotlib.pyplot as plt
ROOT = Path.cwd()
while not (ROOT / 'results').exists():
    ROOT = ROOT.parent
R = lambda f: pd.read_csv(next((ROOT / 'results' / d / f) for d in ('1-data-preparation', '2-analysis', '3-presentation') if (ROOT / 'results' / d / f).exists()))
pd.options.display.float_format = '{:.6g}'.format
pd.options.display.max_colwidth = 80
plt.rcParams.update({'figure.figsize': (9, 3.4), 'axes.spines.top': False, 'axes.spines.right': False})
BLUE, GREY, ORANGE = '#1A73E8', '#9AA0A6', '#E8710A'"""),
    M("## Q1. Klasifikasi kolom\nSetiap kolom diklasifikasi (identitas langsung, quasi-identifier, sensitif, aman) dan diberi metode. Kebijakan lengkap: `config/column_policy.yaml`."),
    K("display(R('column_classification.csv')[['table','column','class','method','output','rows_with_identity']]); R('data_profile.csv')"),
    M("## Q2. Baris unik dan k minimum, sebelum vs sesudah"),
    K("R('risk_k_anonymity.csv')"),
    M("## Q3. Serangan kamus: hash biasa vs HMAC"),
    K("R('risk_dictionary_attack.csv')"),
    M("## Q4. Catatan bebas: sisa nama dan telepon menurut cara pembersihan"),
    K("display(R('risk_notes.csv')); R('risk_text_scan.csv')"),
    M("## Risiko sisa: sel stasiun x shift dan penyambungan dengan daftar jaga"),
    K("display(R('risk_operator_cells.csv').query('operators_before == 1')); R('risk_linkage.csv')"),
    M("## Q5. KPI, ranking stasiun, dan Pareto: asli vs anonim"),
    K("display(R('utility_kpi.csv').head(7)); display(R('utility_station_ranking.csv').head(3)); R('utility_pareto.csv').head(5)"),
    K("w = R('utility_weekly_yield.csv'); plt.plot(w.week, w.yield_raw * 100, color=GREY, lw=5, label='asli'); plt.plot(w.week, w.yield_anon * 100, color=BLUE, ls=':', label='anonim'); plt.xticks(rotation=60); plt.ylabel('yield lini (%)'); plt.legend(); plt.show()"),
    M("## Q6. Tren dan korelasi setelah generalisasi tanggal dan skala angka"),
    K("R('utility_trend.csv')"),
    M("## Q7. Kurva risiko vs utilitas menurut tingkat generalisasi"),
    K("g = R('granularity_curve.csv'); display(g)\nfig, ax = plt.subplots(); ax.bar(g.granularity, g.k_min, color=GREY); ax.axhline(5, color=ORANGE, ls='--'); ax.set_ylabel('k minimum')\nax2 = ax.twinx(); ax2.plot(g.granularity, g.trend_corr_weekly, color=BLUE, marker='o'); ax2.set_ylabel('korelasi tren'); plt.show()"),
    M("## Q8. Trade-off tiap metode"),
    K("R('method_tradeoff.csv')[['method','risk_measure','risk_before','risk_after','utility_measure','utility_value','reversible']]"),
    M("## Q9 dan Q12. Deterministik dan pemulihan mapping key"),
    K("display(R('validation_checks.csv')); R('validation_name_normalization.csv')"),
    M("## Q10-Q11. Waktu yang dihemat (waktu manual dan jumlah file per tahun adalah asumsi)"),
    K("display(R('impact_time.csv')); R('impact_scenarios.csv')"),
    M("## Cek silang SQL vs pandas dan pemindaian berkas rahasia"),
    K("x = R('crosscheck_sql.csv'); print(f\"{int(x.match.sum())} dari {len(x)} pemeriksaan cocok\"); R('secret_scan.csv')"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = C.RES_PRESENT / "analysis.ipynb"
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(C.ROOT)}}).execute()
nbf.write(nb, out)
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
print("notebook", out.name, len(nb.cells), "sel;", len(errs), "error")
assert not errs
