"""Hydrologie : loi de Gumbel et risque de crue pendant la période de travaux.

Loi de Gumbel des maxima annuels (usage courant en France, HydroPortail) :

    F(Q) = exp(-exp(-(Q - u)/β))         Q_T = u - β · ln(-ln(1 - 1/T))

Interprétation poissonnienne équivalente : le nombre moyen de dépassements du
débit Q par an vaut λ(Q) = exp(-(Q - u)/β), d'où F(Q) = exp(-λ(Q)).

Risque pendant les travaux : si une fraction f de l'aléa annuel est couverte par
la période d'installation du batardeau (f = 1 pour une année complète, f
pondéré par la saisonnalité des crues sinon) :

    P(au moins un dépassement de Q pendant les travaux) = 1 - exp(-λ(Q) · f)
"""
from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np

from .constantes import GAMMA_EULER

PERIODES_RETOUR = [2, 5, 10, 20, 50, 100]


@dataclass(frozen=True)
class Gumbel:
    u: float      # paramètre de position (mode) [m³/s]
    beta: float   # paramètre d'échelle (gradex des débits) [m³/s]

    @staticmethod
    def variable_reduite(T: float) -> float:
        return -math.log(-math.log(1.0 - 1.0 / T))

    def quantile(self, T: float) -> float:
        return self.u + self.beta * self.variable_reduite(T)

    def taux_annuel(self, Q: float) -> float:
        """Nombre moyen annuel de dépassements de Q (processus de Poisson)."""
        return math.exp(-(Q - self.u) / self.beta)

    def non_depassement(self, Q: float) -> float:
        return math.exp(-self.taux_annuel(Q))

    def periode_retour(self, Q: float) -> float:
        p = 1.0 - self.non_depassement(Q)
        return math.inf if p <= 0 else 1.0 / p

    # ------------------------------------------------------------ ajustements
    @classmethod
    def par_moments(cls, maxima) -> "Gumbel":
        x = np.asarray([v for v in maxima if v is not None and np.isfinite(v)], dtype=float)
        if len(x) < 5:
            raise ValueError("Au moins 5 maxima annuels sont nécessaires.")
        beta = math.sqrt(6.0) * float(np.std(x, ddof=1)) / math.pi
        u = float(np.mean(x)) - GAMMA_EULER * beta
        return cls(u, beta)

    @classmethod
    def par_quantiles(cls, periodes, debits) -> "Gumbel":
        """Ajustement par moindres carrés sur des couples (T, Q_T) (ex. tableau HydroPortail)."""
        y = np.array([cls.variable_reduite(float(t)) for t in periodes])
        q = np.array(debits, dtype=float)
        if len(q) < 2:
            raise ValueError("Au moins deux couples (T, Q) sont nécessaires.")
        beta, u = np.polyfit(y, q, 1)
        if beta <= 0:
            raise ValueError("Ajustement de Gumbel impossible (pente négative).")
        return cls(float(u), float(beta))

    @classmethod
    def par_max_vraisemblance(cls, maxima) -> "Gumbel":
        from scipy.stats import gumbel_r
        x = np.asarray([v for v in maxima if v is not None and np.isfinite(v)], dtype=float)
        if len(x) < 5:
            raise ValueError("Au moins 5 maxima annuels sont nécessaires.")
        loc, scale = gumbel_r.fit(x)
        return cls(float(loc), float(scale))


def fraction_alea(debut: date, fin: date, poids_mensuels=None) -> float:
    """Fraction de l'aléa annuel couverte par la période [début, fin] (bornes incluses).

    ``poids_mensuels`` : 12 poids (janvier à décembre) décrivant la saisonnalité
    des crues ; ils sont normalisés à 1. Par défaut, répartition uniforme
    (hypothèse prudente pour des travaux en période d'étiage).
    """
    if fin < debut:
        raise ValueError("La date de fin des travaux précède la date de début.")
    w = np.ones(12) if poids_mensuels is None else np.asarray(poids_mensuels, dtype=float)
    if len(w) != 12 or np.any(w < 0) or w.sum() <= 0:
        raise ValueError("12 poids mensuels positifs sont attendus.")
    w = w / w.sum()
    total = 0.0
    jour = debut
    un_jour = timedelta(days=1)
    while jour <= fin:
        total += w[jour.month - 1] / calendar.monthrange(jour.year, jour.month)[1]
        jour += un_jour
    return total


def proba_pendant_travaux(gumbel: Gumbel, Q: float, fraction: float) -> float:
    """Probabilité qu'au moins une crue dépasse Q pendant les travaux."""
    if not np.isfinite(Q):
        return 0.0
    return 1.0 - math.exp(-gumbel.taux_annuel(Q) * fraction)


def debit_de_projet_travaux(gumbel: Gumbel, fraction: float, proba: float) -> float:
    """Débit dont la probabilité de dépassement pendant les travaux vaut ``proba``."""
    lam = -math.log(1.0 - proba) / fraction
    return gumbel.u - gumbel.beta * math.log(lam)


# ------------------------------------------------------------------ chroniques
def analyse_chronique(dates, debits, debut_mj: tuple[int, int], fin_mj: tuple[int, int]):
    """Analyse d'une chronique de débits journaliers (Hub'Eau, HydroPortail, CSV).

    Renvoie un dict :
      * ``maxima_annuels`` {année: débit max}
      * ``maxima_fenetre`` {année: débit max sur la fenêtre de travaux (mois, jour)}
      * ``poids_mensuels`` : fréquence des mois d'occurrence des maxima annuels
        (lissée par +0,5 par mois pour éviter les poids nuls)
    Les années incomplètes (< 300 jours) sont écartées des maxima annuels.
    """
    import pandas as pd

    s = pd.Series(np.asarray(debits, dtype=float), index=pd.to_datetime(dates)).dropna().sort_index()
    if s.empty:
        raise ValueError("Chronique vide.")
    maxima_annuels, mois_max, maxima_fenetre = {}, [], {}
    for annee, grp in s.groupby(s.index.year):
        if len(grp) >= 300:
            maxima_annuels[int(annee)] = float(grp.max())
            mois_max.append(int(grp.idxmax().month))
        d0 = pd.Timestamp(year=int(annee), month=debut_mj[0], day=debut_mj[1])
        if fin_mj >= debut_mj:
            d1 = pd.Timestamp(year=int(annee), month=fin_mj[0], day=fin_mj[1])
            fen = grp[(grp.index >= d0) & (grp.index <= d1)]
            duree = (d1 - d0).days + 1
        else:  # fenêtre à cheval sur deux années : on la rattache à l'année de début
            d1 = pd.Timestamp(year=int(annee) + 1, month=fin_mj[0], day=fin_mj[1])
            fen = s[(s.index >= d0) & (s.index <= d1)]
            duree = (d1 - d0).days + 1
        if len(fen) >= 0.8 * duree:
            maxima_fenetre[int(annee)] = float(fen.max())
    poids = np.full(12, 0.5)
    for m in mois_max:
        poids[m - 1] += 1.0
    return {"maxima_annuels": maxima_annuels, "maxima_fenetre": maxima_fenetre,
            "poids_mensuels": list(poids / poids.sum()), "serie": s}


def frequence_empirique(maxima: dict, Q: float) -> float:
    """Fréquence empirique (formule de Weibull) des années où le maximum dépasse Q."""
    v = np.array(list(maxima.values()), dtype=float)
    if len(v) == 0:
        return math.nan
    return float((v >= Q).sum()) / (len(v) + 1)
