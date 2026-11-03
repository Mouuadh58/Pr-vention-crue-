"""État de l'application : un seul jeu de paramètres partagé par toutes les pages.

Chaque widget est relié à une clé du dictionnaire de paramètres. Sa valeur
initiale est lue dans ce dictionnaire, puis toute modification y est recopiée :
on peut donc changer de page sans rien perdre. Charger un fichier ou revenir à
l'exemple incrémente un numéro de version, ce qui réinitialise tous les widgets.
"""
from __future__ import annotations

import math
from datetime import date

import pandas as pd
import streamlit as st

from batcrue import defauts

CLE = "batcrue_params"
VERSION = "batcrue_version"


def init() -> None:
    if CLE not in st.session_state:
        st.session_state[CLE] = defauts()
    if VERSION not in st.session_state:
        st.session_state[VERSION] = 0


def P() -> dict:
    init()
    return st.session_state[CLE]


def remplacer(params: dict) -> None:
    """Remplace tout le jeu de paramètres (import, retour à l'exemple)."""
    st.session_state[CLE] = params
    st.session_state[VERSION] = st.session_state.get(VERSION, 0) + 1


def _k(nom: str) -> str:
    return f"w{st.session_state.get(VERSION, 0)}_{nom}"


def nombre(nom: str, label: str, step: float | None = None, fmt: str | None = None,
           mini: float | None = None, maxi: float | None = None, aide: str | None = None,
           entier: bool = False, facteur: float = 1.0) -> float:
    """Saisie numérique liée au paramètre ``nom`` (``facteur`` : affichage, ex. m → cm)."""
    conv = int if entier else float
    k = _k(nom)
    if k not in st.session_state:
        v = P()[nom]
        v = conv(v * facteur) if v is not None and not (isinstance(v, float) and math.isnan(v)) else conv(0)
        if mini is not None:
            v = max(v, conv(mini))
        if maxi is not None:
            v = min(v, conv(maxi))
        st.session_state[k] = v
    kw = {"key": k, "help": aide}
    if step is not None:
        kw["step"] = conv(step)
    if fmt:
        kw["format"] = fmt
    if mini is not None:
        kw["min_value"] = conv(mini)
    if maxi is not None:
        kw["max_value"] = conv(maxi)
    v = st.number_input(label, **kw)
    P()[nom] = conv(v / facteur) if facteur != 1.0 else v
    return P()[nom]


def texte(nom: str, label: str, aide: str | None = None, zone: bool = False) -> str:
    k = _k(nom)
    if k not in st.session_state:
        st.session_state[k] = str(P()[nom] or "")
    v = (st.text_area if zone else st.text_input)(label, key=k, help=aide)
    P()[nom] = v
    return v


def case(nom: str, label: str, aide: str | None = None, bascule: bool = True) -> bool:
    k = _k(nom)
    if k not in st.session_state:
        st.session_state[k] = bool(P()[nom])
    v = (st.toggle if bascule else st.checkbox)(label, key=k, help=aide)
    P()[nom] = bool(v)
    return bool(v)


def choix(nom: str, label: str, options: list, libelles: dict | None = None, aide: str | None = None,
          horizontal: bool = False) -> object:
    k = _k(nom)
    if k not in st.session_state:
        v = P()[nom]
        st.session_state[k] = v if v in options else options[0]
    fmt = (lambda o: libelles.get(o, str(o))) if libelles else str
    if horizontal:
        v = st.radio(label, options, key=k, format_func=fmt, help=aide, horizontal=True)
    else:
        v = st.selectbox(label, options, key=k, format_func=fmt, help=aide)
    P()[nom] = v
    return v


def multichoix(nom: str, label: str, options: list, libelles: dict | None = None,
               aide: str | None = None) -> list:
    k = _k(nom)
    if k not in st.session_state:
        st.session_state[k] = [o for o in P()[nom] if o in options]
    fmt = (lambda o: libelles.get(o, str(o))) if libelles else str
    v = st.multiselect(label, options, key=k, format_func=fmt, help=aide)
    P()[nom] = list(v)
    return list(v)


def jour(nom: str, label: str, aide: str | None = None) -> date:
    k = _k(nom)
    if k not in st.session_state:
        try:
            st.session_state[k] = date.fromisoformat(str(P()[nom]))
        except ValueError:
            st.session_state[k] = date.today()
    v = st.date_input(label, key=k, help=aide, format="DD/MM/YYYY")
    P()[nom] = v.isoformat()
    return v


def tableau(nom: str, colonnes: list[str], config: dict | None = None, requis: list[str] | None = None,
            dynamique: bool = True, hauteur: int | None = None) -> pd.DataFrame:
    """Tableau éditable lié à une liste de dictionnaires du jeu de paramètres."""
    k = _k(nom)
    kb = k + "__base"
    if k not in st.session_state or kb not in st.session_state:
        st.session_state[kb] = pd.DataFrame(P()[nom], columns=colonnes)
    kw = {"key": k, "num_rows": "dynamic" if dynamique else "fixed", "hide_index": True,
          "column_config": config or {}}
    if hauteur:
        kw["height"] = hauteur
    df = st.data_editor(st.session_state[kb], **kw)
    requis = requis or []
    lignes = []
    for rec in df.to_dict("records"):
        propre = {}
        for c, v in rec.items():
            propre[c] = None if (v is None or (isinstance(v, float) and math.isnan(v)) or v is pd.NA) else v
        if all(propre.get(c) is not None for c in requis):
            for c, v in propre.items():
                if v is None:
                    propre[c] = math.nan
            lignes.append(propre)
    P()[nom] = lignes
    return df
