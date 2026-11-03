"""Outils communs aux pages : calculs mis en cache, formats français, palette, bandeaux."""
from __future__ import annotations

import math

import streamlit as st

from batcrue import EtudeBatardeau, depuis_json, valider, vers_json
from batcrue.ouvrage import METHODES
from ui.etat import P

# Palette catégorielle validée (daltonisme, contraste) – ordre fixe, jamais recyclé.
_CLAIR = {"serie": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"], "encre": "#0b0b0b", "encre2": "#52514e",
          "discret": "#898781", "grille": "#e1e0d9", "fond_lit": "#c3c2b7",
          "rampe": ["#86b6ef", "#2a78d6", "#104281"], "critique": "#d03b3b", "bon": "#0ca30c",
          "eau": "rgba(42,120,214,0.10)"}
_SOMBRE = {"serie": ["#3987e5", "#d95926", "#199e70", "#c98500"], "encre": "#f0efec", "encre2": "#c3c2b7",
           "discret": "#898781", "grille": "#2c2c2a", "fond_lit": "#52514e",
           "rampe": ["#184f95", "#3987e5", "#9ec5f4"], "critique": "#d03b3b", "bon": "#0ca30c",
           "eau": "rgba(57,135,229,0.16)"}

LIBELLES_METHODES = {**METHODES, "enveloppe": "Enveloppe (valeur la plus défavorable)"}


def palette() -> dict:
    try:
        sombre = st.context.theme.type == "dark"
    except Exception:  # pragma: no cover - anciennes versions de Streamlit
        sombre = False
    return _SOMBRE if sombre else _CLAIR


def couleur_methode(m: str) -> str:
    pal = palette()
    return pal["encre"] if m == "enveloppe" else pal["serie"]["ABCD".index(m)]


# ------------------------------------------------------------------ formats
def fr(x, n: int = 2, unite: str = "") -> str:
    """Nombre au format français (virgule décimale, espace des milliers)."""
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    s = f"{x:,.{n}f}".replace(",", " ").replace(".", ",")
    return f"{s} {unite}".strip()


def cm(x_m, n: int = 1) -> str:
    return fr(None if x_m is None else x_m * 100, n, "cm")


def pct(x, n: int = 1) -> str:
    return fr(None if x is None else x * 100, n, "%")


def periode(T) -> str:
    if T is None or (isinstance(T, float) and math.isnan(T)):
        return "—"
    if math.isinf(T) or T > 1e4:
        return "> 10 000 ans"
    if T < 1.05:
        return "< 1 an"
    return f"≈ {fr(T, 0 if T >= 10 else 1)} ans"


def debit(q) -> str:
    return "jamais atteint" if q is None else fr(q, 0, "m³/s")


# ------------------------------------------------------------------ calculs mis en cache
def params_json() -> str:
    return vers_json(P())


@st.cache_resource(max_entries=24, show_spinner=False)
def _etude(pj: str) -> EtudeBatardeau:
    return EtudeBatardeau(depuis_json(pj))


@st.cache_data(max_entries=24, show_spinner=False)
def _calculs(pj: str) -> dict:
    e = _etude(pj)
    return {"courbe": e.courbe(), "tableau": e.tableau_periodes_retour(), "synthese": e.synthese()}


@st.cache_data(max_entries=24, show_spinner=False)
def _sensibilite(pj: str, methode: str):
    return _etude(pj).sensibilite(methode=methode)


@st.cache_data(max_entries=8, show_spinner=False)
def _monte_carlo(pj: str, methode: str) -> dict:
    return _etude(pj).monte_carlo(methode=methode)


@st.cache_data(max_entries=24, show_spinner=False)
def _variantes(pj: str) -> dict:
    e = _etude(pj)
    fr_nom = e.taux_obstruction
    fractions = sorted({0.25, round(fr_nom, 4), 0.5} if 0 < fr_nom < 1 else {0.25, 1 / 3, 0.5})
    return e.variantes_largeur(tuple(fractions))


@st.cache_data(max_entries=24, show_spinner=False)
def _hydrogramme(pj: str) -> dict:
    return _etude(pj).simulation_hydrogramme()


def etude() -> EtudeBatardeau:
    return _etude(params_json())


def calculs() -> dict:
    return _calculs(params_json())


def sensibilite(methode: str):
    return _sensibilite(params_json(), methode)


def monte_carlo(methode: str) -> dict:
    return _monte_carlo(params_json(), methode)


def variantes() -> dict:
    return _variantes(params_json())


def hydrogramme() -> dict:
    return _hydrogramme(params_json())


def erreurs_bloquantes() -> bool:
    """Affiche les erreurs/avertissements de cohérence ; True si le calcul est impossible."""
    err, warn = valider(P())
    for w in warn:
        st.warning(w, icon="⚠️")
    for e in err:
        st.error(e, icon="⛔")
    return bool(err)


def bandeau_verdict(s: dict) -> None:
    niveau = s["niveau"]
    texte = f"**Pré-diagnostic** — {s['verdict']}"
    if niveau == "ok":
        st.success(texte, icon="✅")
    elif niveau == "attention":
        st.warning(texte, icon="⚠️")
    else:
        st.error(texte, icon="⛔")


def note_exemple() -> None:
    if P().get("nom_barrage", "").endswith("(données d'exemple)"):
        st.info("Les valeurs chargées sont **un exemple fictif réaliste** : remplacez-les par les données "
                "du barrage (page 1) avant toute conclusion.", icon="ℹ️")
