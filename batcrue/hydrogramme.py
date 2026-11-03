"""Hydrogrammes de crue pour la simulation quasi-permanente d'un événement.

Hydrogramme synthétique en cloche (forme de type SOCOSE) :

    Q(t) = Qb + (Qp - Qb) · 2 s⁴ / (1 + s⁸)      avec s = t / t_pic

Le pic est atteint à t = t_pic. Sur l'Oise, les crues sont lentes (montée de
plusieurs jours) : l'hypothèse quasi-permanente (succession d'états
permanents) est alors acceptable pour estimer les cotes et les délais
d'alerte.
"""
from __future__ import annotations

import io

import numpy as np


def hydrogramme_synthetique(Qp: float, Qb: float, t_pic_h: float, duree_h: float, pas_h: float = 1.0):
    """Renvoie (t [h], Q [m³/s])."""
    t = np.arange(0.0, duree_h + pas_h / 2.0, pas_h)
    s = t / t_pic_h
    forme = 2.0 * s ** 4 / (1.0 + s ** 8)
    return t, Qb + (Qp - Qb) * forme


def lire_hydrogramme_csv(contenu: bytes | str):
    """Lit un CSV « date;débit » ou « heures;débit » (séparateur ; ou ,).

    Renvoie (t [h depuis le début], Q [m³/s]).
    """
    import pandas as pd

    if isinstance(contenu, bytes):
        contenu = contenu.decode("utf-8-sig", errors="replace")
    sep = ";" if contenu.count(";") >= contenu.count(",") else ","
    df = pd.read_csv(io.StringIO(contenu), sep=sep)
    if df.shape[1] < 2:
        raise ValueError("Le fichier doit contenir deux colonnes : temps et débit.")
    c_t, c_q = df.columns[:2]
    q = pd.to_numeric(df[c_q].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    t_num = pd.to_numeric(df[c_t].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    if t_num.notna().all():
        t = t_num.to_numpy(dtype=float)
    else:
        dt = pd.to_datetime(df[c_t], dayfirst=True, errors="coerce")
        if dt.isna().any():
            raise ValueError("Colonne de temps illisible (dates ou heures attendues).")
        t = (dt - dt.iloc[0]).dt.total_seconds().to_numpy() / 3600.0
    masque = np.isfinite(q.to_numpy(dtype=float))
    return t[masque], q.to_numpy(dtype=float)[masque]


def instants_franchissement(t, valeurs, seuil: float):
    """Premier instant (interpolé) où ``valeurs`` atteint ``seuil``, ou None."""
    v = np.asarray(valeurs, dtype=float)
    for i in range(len(v)):
        if v[i] >= seuil:
            if i == 0:
                return float(t[0])
            v0, v1 = v[i - 1], v[i]
            return float(t[i - 1] + (seuil - v0) / (v1 - v0) * (t[i] - t[i - 1]))
    return None
