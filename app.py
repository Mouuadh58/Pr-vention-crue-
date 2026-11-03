"""BatCrue – application d'étude de l'impact hydraulique d'un batardeau sur les crues.

Lancement :  streamlit run app.py
"""
import streamlit as st

st.set_page_config(page_title="BatCrue · impact hydraulique des batardeaux", page_icon="🌊", layout="wide",
                   initial_sidebar_state="expanded")

from ui import commun, etat  # noqa: E402  (après set_page_config)

etat.init()

pages = [
    st.Page("ui/page_donnees.py", title="1 · Données & calculs", icon="📋", default=True),
    st.Page("ui/page_resultats.py", title="2 · Simulations & résultats", icon="📈"),
    st.Page("ui/page_temps_reel.py", title="3 · Temps réel (Hub'Eau)", icon="🛰️"),
    st.Page("ui/page_methodo.py", title="4 · Méthodologie", icon="📚"),
]
navigation = st.navigation(pages)

navigation.run()

# Résumé affiché après la page : il tient compte des dernières saisies.
with st.sidebar:
    st.markdown("### 🌊 BatCrue")
    st.caption("Impact d'un batardeau sur les crues · barrages de navigation")
    p = etat.P()
    st.markdown(f"**{p['nom_barrage']}**")
    try:
        from batcrue import valider
        if not valider(p)[0]:
            s = commun.calculs()["synthese"]
            libelle = {"ok": "✅ Impact acceptable", "attention": "⚠️ Acceptable sous conditions",
                       "non_conforme": "⛔ Mesures nécessaires"}[s["niveau"]]
            st.markdown(f"{libelle}")
            st.caption(f"ΔZ au barrage Q{int(p['T_reference'])} : {commun.cm(s['dZ_barrage'])} · "
                       f"aux enjeux : {commun.cm(s['dZ_enjeux_max'])}")
    except Exception as exc:  # noqa: BLE001 - la barre latérale ne doit jamais bloquer l'application
        st.caption(f"Calcul indisponible : {exc}")
    st.divider()
    st.caption("Pré-diagnostic : résultats à valider par un ingénieur hydraulicien et par le service police de l'eau.")
