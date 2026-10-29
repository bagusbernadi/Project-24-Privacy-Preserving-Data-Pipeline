"""Dashboard Streamlit (3 halaman): sebelum vs sesudah, risiko vs utilitas, trade-off metode. Semua data simulasi (identitas palsu).
Jalankan dari folder project/:  streamlit run code/3-presentation/streamlit/app.py
Membaca CSV ringkas di results/3-presentation/ (tidak membaca data asli, mapping key, atau kunci)."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results" / "3-presentation"
st.set_page_config(page_title="Project 24: Privacy-Preserving Data Sharing Pipeline", layout="wide")
BLUE, ORANGE, GREY, GREEN = "#1A73E8", "#E8710A", "#9AA0A6", "#188038"
pct = lambda v, d=1: f"{v * 100:.{d}f}".replace(".", ",") + "%"


@st.cache_data
def load(name):
    return pd.read_csv(RES / name)


gran, trade, att, notes = load("dash_granularity.csv"), load("dash_tradeoff.csv"), load("dash_attack.csv"), load("dash_notes.csv")
wk, par, rk, val = load("dash_weekly_yield.csv"), load("dash_pareto.csv"), load("dash_ranking.csv"), load("dash_validation.csv")
ev, pol, kpi, sample = load("dash_evaluation.csv"), load("dash_policy.csv"), load("dash_kpi.csv"), load("dash_anon_sample.csv")
st.sidebar.header("Halaman")
page = st.sidebar.radio("Pilih", ["1. Sebelum vs sesudah", "2. Risiko vs utilitas", "3. Trade-off metode"])
st.sidebar.caption("Data simulasi dengan identitas palsu (Faker). Dashboard hanya menampilkan ringkasan; data asli, mapping key, dan kunci tidak ada di sini.")
st.title("Project 24: Privacy-Preserving Data Sharing Pipeline")
st.caption("Lini perakitan sepeda motor, 10 stasiun, 3 model, 2 shift, 75 hari kerja (4.500 baris produksi).")


def e(metric):
    return ev[ev.metric.str.startswith(metric)].iloc[0]


if page.startswith("1"):
    y = kpi.iloc[0]
    c = st.columns(4)
    c[0].metric("Yield lini, data asli", pct(y.raw, 2))
    c[1].metric("Yield lini, data anonim", pct(y.anon, 2), f"selisih {y.abs_diff:.1e}", delta_color="off")
    c[2].metric("Stasiun terburuk sama", f"{int(e('Stasiun dengan ranking').after)} dari 3")
    c[3].metric("Defect teratas sama", f"{int(e('Kode defect dengan').after)} dari 3")
    st.subheader("Kebijakan per kolom")
    st.dataframe(pol[["table", "column", "class", "method", "output", "why"]].rename(columns={"table": "tabel", "column": "kolom", "class": "kelas", "method": "metode", "output": "kolom hasil", "why": "alasan"}),
                 hide_index=True, width="stretch")
    st.subheader("Contoh baris anonim (kode ditampilkan sebagai pola)")
    st.dataframe(sample, hide_index=True, width="stretch")
    st.subheader("Yield mingguan: asli vs anonim")
    f = go.Figure()
    f.add_scatter(x=wk.week, y=wk.yield_raw * 100, name="Asli", line=dict(color=GREY, width=5))
    f.add_scatter(x=wk.week, y=wk.yield_anon * 100, name="Anonim", line=dict(color=BLUE, dash="dot"))
    f.update_layout(yaxis_title="yield lini (%)", height=340, margin=dict(t=10))
    st.plotly_chart(f, width="stretch")
    c1, c2 = st.columns(2)
    c1.markdown("**Ranking NG per stasiun (asli vs anonim)**")
    c1.dataframe(rk[["rank", "station_raw", "station_anon", "same_station"]], hide_index=True)
    c2.markdown("**Pareto defect 8 teratas**")
    c2.dataframe(par[["rank", "defect_raw", "defect_name", "defect_anon", "same_defect"]], hide_index=True)
elif page.startswith("2"):
    st.subheader("Tingkat generalisasi tanggal")
    g = st.select_slider("Generalisasi tanggal", options=list(gran.granularity), value="Mingguan")
    r = gran[gran.granularity == g].iloc[0]
    c = st.columns(4)
    c[0].metric("Baris unik (kombinasi terketat)", pct(r.pct_unique, 0))
    c[1].metric("k minimum", int(r.k_min), "memenuhi k >= 5" if r.k_target_met else "di bawah 5", delta_color="normal" if r.k_target_met else "inverse")
    c[2].metric("Titik waktu untuk tren", int(r.time_points))
    c[3].metric("Korelasi tren mingguan", f"{r.trend_corr_weekly:.2f}".replace(".", ","))
    f = go.Figure()
    f.add_bar(x=gran.granularity, y=gran.k_min, name="k minimum", marker_color=[ORANGE if x == g else GREY for x in gran.granularity], yaxis="y")
    f.add_scatter(x=gran.granularity, y=gran.trend_corr_weekly, name="Korelasi tren (utilitas)", line=dict(color=BLUE), yaxis="y2")
    f.add_hline(y=5, line_dash="dash", line_color=GREEN, annotation_text="k = 5")
    f.update_layout(yaxis=dict(title="k minimum (risiko turun bila naik)"), yaxis2=dict(title="korelasi tren", overlaying="y", side="right", range=[0, 1.05]), height=360, margin=dict(t=10))
    st.plotly_chart(f, width="stretch")
    st.caption("k minimum dihitung pada kombinasi terketat: tanggal/minggu + shift + stasiun + model + kode operator. Operator bergilir tiap minggu, jadi k tidak naik setelah mingguan; yang turun hanya utilitas tren.")
    c1, c2 = st.columns(2)
    a2 = att.assign(recovery_rate=att.recovery_rate.map(lambda v: pct(v, 0)))
    c1.markdown("**Serangan kamus pada kode operator**")
    c1.dataframe(a2[["scheme", "operators_attacked", "recovered", "recovery_rate"]], hide_index=True)
    c2.markdown("**Sisa identitas di catatan bebas**")
    c2.dataframe(notes[["method", "rows_with_identity", "rows_text_unchanged"]], hide_index=True)
else:
    st.subheader("Trade-off tiap metode")
    t = trade.copy()
    t["risk_before"], t["risk_after"] = t.risk_before.round(3), t.risk_after.round(3)
    st.dataframe(t[["method", "applied_to", "risk_measure", "risk_before", "risk_after", "utility_measure", "utility_value", "reversible", "weakness"]], hide_index=True, width="stretch")
    st.subheader("Pemulihan dan deterministik")
    st.dataframe(val[["question", "check", "n_tested", "n_pass", "result"]], hide_index=True, width="stretch")
    st.subheader("Ringkasan sebelum dan sesudah")
    st.dataframe(ev, hide_index=True, width="stretch")
    st.info("Batasan: indeks tidak melindungi bila satu nilai asli diketahui; kode operator masih bisa disambungkan oleh pihak yang punya daftar jaga; data anonim di sini belum tentu anonim bila digabung dengan data lain.")
