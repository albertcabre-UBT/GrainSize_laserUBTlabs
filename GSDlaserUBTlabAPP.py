"""
Analisi Granulometrica - Streamlit App
========================================
Permet enganxar dades de tamisatge (mida de gra / % que passa) directament
en una taula buida, editar-les, i generar la corba granulometrica.

Per executar:
    pip install streamlit pandas matplotlib numpy
    streamlit run granulometric_app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Analisi Granulometrica", layout="wide")
st.title("📊 Anàlisi Granulomètrica")
st.caption("Enganxa les dades de tamisatge (mida de gra i % que passa) i genera la corba.")

# ---------- Estat de sessio: llista de mostres ----------
if "mostres" not in st.session_state:
    # cada mostra: nom -> DataFrame(mida_mm, pct_passa)
    st.session_state.mostres = {}

# ---------- Taula buida per defecte (per enganxar dades tipus Excel) ----------
TAULA_BUIDA = pd.DataFrame({"mida_mm": [None] * 12, "pct_passa": [None] * 12})

if "taula_nova" not in st.session_state:
    st.session_state.taula_nova = TAULA_BUIDA.copy()

with st.sidebar:
    st.header("➕ Afegir mostra")
    nom_mostra = st.text_input("Nom de la mostra", value=f"Mostra {len(st.session_state.mostres) + 1}")

    st.markdown(
        "Enganxa les dades directament a la taula (clica la primera cel·la "
        "i fes **Ctrl+V**), o escriu-les a mà. Prem '+' per afegir més files."
    )
    taula_editada = st.data_editor(
        st.session_state.taula_nova,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_nova_mostra",
        column_config={
            "mida_mm": st.column_config.NumberColumn("Mida (mm)", format="%.4f"),
            "pct_passa": st.column_config.NumberColumn("% passa", format="%.2f"),
        },
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
        df = taula_editada.dropna(subset=["mida_mm", "pct_passa"]).copy()
        if df.empty:
            st.error("La taula no té cap fila vàlida (mida_mm i pct_passa).")
        else:
            df = df.sort_values("mida_mm", ascending=False).reset_index(drop=True)
            st.session_state.mostres[nom_mostra] = df
            st.session_state.taula_nova = TAULA_BUIDA.copy()  # neteja per a la seguent mostra
            st.success(f"Mostra '{nom_mostra}' afegida amb {len(df)} punts.")
            st.rerun()

    if st.session_state.mostres:
        st.divider()
        st.header("🗂️ Mostres actuals")
        per_esborrar = st.selectbox("Esborrar una mostra concreta", ["-"] + list(st.session_state.mostres.keys()))
        if per_esborrar != "-" and st.button("Esborrar seleccionada"):
            del st.session_state.mostres[per_esborrar]
            st.rerun()

# ---------- Funcions de calcul ----------
def interpolar_d(df, pct_objectiu):
    """Interpola D10, D80, D84 sobre escala log de mida."""
    d = df.sort_values("mida_mm")
    x = np.log10(d["mida_mm"].values)
    y = d["pct_passa"].values
    if pct_objectiu < y.min() or pct_objectiu > y.max():
        return None
    d_log = np.interp(pct_objectiu, y, x)
    return 10 ** d_log

def calcular_parametres(df):
    d10 = interpolar_d(df, 10)
    d80 = interpolar_d(df, 80)
    d84 = interpolar_d(df, 84)
    return d10, d80, d84

# ---------- Panell principal ----------
if not st.session_state.mostres:
    st.info("👈 Enganxa dades a la taula de la barra lateral i prem 'Afegir / Actualitzar' per començar.")
else:
    tab_grafic, tab_taules, tab_parametres = st.tabs(["📈 Gràfic", "📋 Taules", "🔢 Paràmetres (D10/D80/D84)"])

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
            d10, d80, d84 = calcular_parametres(df)
            files.append({
                "Mostra": nom,
                "D10 (mm)": round(d10, 4) if d10 else "—",
                "D80 (mm)": round(d80, 4) if d80 else "—",
                "D84 (mm)": round(d84, 4) if d84 else "—",
            })
        st.dataframe(pd.DataFrame(files), use_container_width=True, hide_index=True)
        st.caption(
            "D10, D80 i D84 s'obtenen per interpolació lineal sobre escala logarítmica de la mida de gra. "
            "Si una mostra no cobreix aquest % de pas, el valor pot no calcular-se (—)."
        )
