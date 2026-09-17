"""
Anàlisi Granulomètrica - Streamlit App
========================================
Permet enganxar dades de tamisatge (mida de gra / % que passa),
editar-les en una taula, i generar la corba granulomètrica.

Per executar:
    pip install streamlit pandas matplotlib numpy
    streamlit run granulometric_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import StringIO

st.set_page_config(page_title="Anàlisi Granulomètrica", layout="wide")
st.title("📊 Anàlisi Granulomètrica")
st.caption("Enganxa les dades de tamisatge (mida de gra i % que passa) i genera la corba.")

# ---------- Estat de sessió: llista de mostres ----------
if "mostres" not in st.session_state:
    # cada mostra: {"nom": str, "df": DataFrame(mida_mm, pct_passa)}
    st.session_state.mostres = {}

# ---------- Dades d'exemple ----------
EXEMPLE = """mida_mm,pct_passa
100,100
50,99
20,96
10,90
5,78
2,60
1,45
0.5,30
0.25,18
0.1,10
0.05,5
0.02,2
0.005,0.5
"""

with st.sidebar:
    st.header("➕ Afegir mostra")
    nom_mostra = st.text_input("Nom de la mostra", value=f"Mostra {len(st.session_state.mostres) + 1}")

    st.markdown("Enganxa les dades en format CSV (`mida_mm,pct_passa`), una línia per tamís:")
    text_dades = st.text_area(
        "Dades",
        value=EXEMPLE if not st.session_state.mostres else "mida_mm,pct_passa\n",
        height=280,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        afegir = st.button("Afegir / Actualitzar", use_container_width=True, type="primary")
    with col_b:
        esborrar_totes = st.button("Esborrar totes", use_container_width=True)

    if esborrar_totes:
        st.session_state.mostres = {}
        st.rerun()

    if afegir:
        try:
            df = pd.read_csv(StringIO(text_dades))
            df.columns = [c.strip().lower() for c in df.columns]
            if not {"mida_mm", "pct_passa"}.issubset(df.columns):
                st.error("Les columnes han de dir-se 'mida_mm' i 'pct_passa'.")
            else:
                df = df[["mida_mm", "pct_passa"]].dropna()
                df = df.sort_values("mida_mm", ascending=False).reset_index(drop=True)
                st.session_state.mostres[nom_mostra] = df
                st.success(f"Mostra '{nom_mostra}' afegida amb {len(df)} punts.")
        except Exception as e:
            st.error(f"Error llegint les dades: {e}")

    if st.session_state.mostres:
        st.divider()
        st.header("🗂️ Mostres actuals")
        per_esborrar = st.selectbox("Esborrar una mostra concreta", ["-"] + list(st.session_state.mostres.keys()))
        if per_esborrar != "-" and st.button("Esborrar seleccionada"):
            del st.session_state.mostres[per_esborrar]
            st.rerun()

# ---------- Funcions de càlcul ----------
def interpolar_d(df, pct_objectiu):
    """Interpola D10, D30, D60 sobre escala log de mida."""
    d = df.sort_values("mida_mm")
    x = np.log10(d["mida_mm"].values)
    y = d["pct_passa"].values
    if pct_objectiu < y.min() or pct_objectiu > y.max():
        return None
    d_log = np.interp(pct_objectiu, y, x)
    return 10 ** d_log

def calcular_parametres(df):
    d10 = interpolar_d(df, 10)
    d30 = interpolar_d(df, 30)
    d60 = interpolar_d(df, 60)
    cu = cc = None
    if d10 and d60:
        cu = d60 / d10
    if d10 and d30 and d60:
        cc = (d30 ** 2) / (d10 * d60)
    return d10, d30, d60, cu, cc

# ---------- Panell principal ----------
if not st.session_state.mostres:
    st.info("👈 Enganxa dades a la barra lateral i prem 'Afegir / Actualitzar' per començar.")
else:
    tab_grafic, tab_taules, tab_parametres = st.tabs(["📈 Gràfic", "📋 Taules", "🔢 Paràmetres (D10/D30/D60)"])

    with tab_grafic:
        ordre_x = st.radio(
            "Ordre de l'eix X",
            ["Gros → Fi (esquerra → dreta)", "Fi → Gros (esquerra → dreta)"],
            horizontal=True,
        )

        fig, ax = plt.subplots(figsize=(9, 5.5))
        for nom, df in st.session_state.mostres.items():
            d = df.sort_values("mida_mm", ascending=(ordre_x.startswith("Fi")))
            ax.plot(d["mida_mm"], d["pct_passa"], marker="o", label=nom)

        ax.set_xscale("log")
        if ordre_x.startswith("Gros"):
            ax.invert_xaxis()
        ax.set_xlabel("Mida de gra (mm, escala log)")
        ax.set_ylabel("% que passa")
        ax.set_ylim(0, 100)
        ax.grid(True, which="both", linestyle="--", alpha=0.5)
        ax.legend()
        ax.set_title("Corba Granulomètrica")
        st.pyplot(fig)

        buf = StringIO()
        fig.savefig("corba_granulometrica.png", dpi=200, bbox_inches="tight")
        with open("corba_granulometrica.png", "rb") as f:
            st.download_button("⬇️ Descarregar gràfic (PNG)", f, file_name="corba_granulometrica.png")

    with tab_taules:
        for nom, df in st.session_state.mostres.items():
            st.subheader(nom)
            edited = st.data_editor(df, num_rows="dynamic", key=f"editor_{nom}", use_container_width=True)
            st.session_state.mostres[nom] = edited

    with tab_parametres:
        files = []
        for nom, df in st.session_state.mostres.items():
            d10, d30, d60, cu, cc = calcular_parametres(df)
            files.append({
                "Mostra": nom,
                "D10 (mm)": round(d10, 4) if d10 else "—",
                "D30 (mm)": round(d30, 4) if d30 else "—",
                "D60 (mm)": round(d60, 4) if d60 else "—",
                "Cu (=D60/D10)": round(cu, 2) if cu else "—",
                "Cc (=D30²/D10·D60)": round(cc, 2) if cc else "—",
            })
        st.dataframe(pd.DataFrame(files), use_container_width=True, hide_index=True)
        st.caption(
            "Cu > 4-6 i 1 < Cc < 3 solen indicar un sòl ben graduat (segons el sistema USCS). "
            "Si alguna mostra no té prou rang de dades, D10/D30/D60 poden no calcular-se (—)."
        )
