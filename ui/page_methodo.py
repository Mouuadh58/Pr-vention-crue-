"""Page 4 – Méthodologie, références et autres méthodes possibles."""
from pathlib import Path

import streamlit as st

RACINE = Path(__file__).resolve().parent.parent / "docs"

st.title("📚 Page 4 · Méthodologie & références")
onglets = st.tabs(["Note méthodologique", "Autres méthodes et outils existants", "Démarche réglementaire"])
for onglet, fichier in zip(onglets, ["NOTE_METHODOLOGIQUE.md", "AUTRES_METHODES.md", "REGLEMENTATION.md"]):
    with onglet:
        chemin = RACINE / fichier
        if chemin.exists():
            st.markdown(chemin.read_text(encoding="utf-8"))
        else:
            st.warning(f"Document {fichier} introuvable.")
