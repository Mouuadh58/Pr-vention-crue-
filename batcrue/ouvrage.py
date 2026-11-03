"""Lois hydrauliques au droit du barrage (vannes entièrement ouvertes).

On cherche la cote amont Z1 (section 1, juste en amont de l'ouvrage) qui permet
de faire transiter le débit Q par les passes restées libres, connaissant la
cote aval Z3 (section 3, à l'aval, après ré-épanouissement de l'écoulement).
La section 2 est la section contractée, dans les passes.

Quatre méthodes indépendantes sont programmées ; on compare leurs résultats
et on retient l'enveloppe (valeur la plus défavorable) :

  A. Bilan d'énergie (Bernoulli) avec pertes de charge singulières :
     - perte à l'élargissement brusque de Borda-Carnot (V2 - V3)²/2g,
     - perte à la contraction ξ (V2² - V1²)/2g,
     - contrôle critique (écoulement dénoyé) si le rétrécissement « s'étrangle »
       (principe de Bélanger : charge spécifique minimale).
  B. Formule de Yarnell (1934) : exhaussement dû aux piles de pont, calé
     expérimentalement (utilisée par HEC-RAS).
  C. Formule de d'Aubuisson (1840) : Q = K_A · b2 · y3 · √(2gΔh + V1²).
  D. Lois de seuil dénoyé / noyé (ouvrages en parallèle), formulation usuelle
     en France (SIC, Cassiopée) :
        dénoyé  Q = μ  b √(2g) h1^1.5            si h2 ≤ 2/3 h1
        noyé    Q = μs b h2 √(2g (h1 - h2))      avec μs = 3√3/2 · μ

Conventions : cotes en m NGF, débits en m³/s, largeurs en m.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.optimize import brentq

from .constantes import G

# Coefficients usuels selon la forme des piles / du nez du batardeau.
#   K_yarnell : coefficient de forme de Yarnell (manuel HEC-RAS, tableau 5-1)
#   xi        : coefficient de perte à la contraction (guide HEC-RAS :
#               0,1 progressive ; 0,3 typique d'un pont ; 0,6 brusque)
FORMES = {
    "arrondi": {"libelle": "Nez et queue arrondis (semi-circulaires)", "K_yarnell": 0.90, "xi": 0.1},
    "triangulaire": {"libelle": "Nez et queue triangulaires (90°)", "K_yarnell": 1.05, "xi": 0.3},
    "carre": {"libelle": "Nez et queue carrés (batardeau rectangulaire)", "K_yarnell": 1.25, "xi": 0.6},
}

METHODES = {
    "A": "Énergie + pertes singulières (Borda-Carnot)",
    "B": "Yarnell (1934)",
    "C": "d'Aubuisson (1840)",
    "D": "Lois de seuil dénoyé/noyé",
}

_DEUX_G = 2.0 * G


@dataclass(frozen=True)
class SectionBarrage:
    """Section d'approche et de restitution au droit du barrage (rectangulaire)."""

    largeur: float    # largeur hydraulique de la rivière au droit du barrage B [m]
    cote_fond: float  # cote du fond [m NGF]

    def aire(self, Z: float) -> float:
        return self.largeur * max(Z - self.cote_fond, 0.0)

    def vitesse(self, Q: float, Z: float) -> float:
        a = self.aire(Z)
        return Q / a if a > 0 else math.inf


@dataclass
class ResultatMethode:
    """Résultat d'une méthode pour un débit et une configuration (avec/sans batardeau)."""

    methode: str
    Z_amont: float           # cote amont en écoulement libre (vannes ouvertes) [m NGF]
    V_amont: float           # vitesse d'approche V1 [m/s]
    V_passes: float          # vitesse moyenne dans les passes libres V2 [m/s]
    regime: str              # description du régime
    valide: bool = True      # False si hors du domaine de validité de la méthode
    remarque: str = ""
    Z_passes: float = math.nan  # cote dans les passes (section 2), si calculée
    details: dict | None = None


def regrouper(ouvertures):
    """Regroupe les passes libres de même cote de seuil (largeurs additionnées).

    ``ouvertures`` : itérable de (largeur_libre, cote_seuil). Renvoie une liste
    triée de (largeur, cote_seuil) avec largeur > 0.
    """
    groupes: dict[float, float] = {}
    for b, zs in ouvertures:
        if b > 1e-9:
            cle = round(float(zs), 4)
            groupes[cle] = groupes.get(cle, 0.0) + float(b)
    return sorted(((b, zs) for zs, b in groupes.items()), key=lambda t: t[1])


def surface_libre(ouvertures, Z: float) -> float:
    """Surface d'écoulement offerte par les passes libres sous la cote Z [m²]."""
    return sum(b * max(Z - zs, 0.0) for b, zs in ouvertures)


# --------------------------------------------------------------------------
# Méthode A : bilan d'énergie + Borda-Carnot + contrôle critique
# --------------------------------------------------------------------------
def _z2_expansion(q: float, b: float, zs: float, V3: float, E3: float):
    """Cote Z2 dans la passe pour le débit q, imposée par l'aval.

    Bilan d'énergie entre la passe (2) et l'aval (3) avec perte de Borda-Carnot :
        Z2 + V2²/2g = E3 + max(0, V2 - V3)²/2g
    Renvoie (Z2, noye). Si aucune solution fluviale n'existe dans la passe,
    l'écoulement est contrôlé par la hauteur critique (passe dénoyée).
    """
    yc = (q * q / (G * b * b)) ** (1.0 / 3.0)
    zc = zs + yc

    def f(z2):
        v2 = q / (b * (z2 - zs))
        perte = max(0.0, v2 - V3)
        return z2 + v2 * v2 / _DEUX_G - E3 - perte * perte / _DEUX_G

    if E3 <= zc or f(zc) >= 0.0:
        return zc, False
    z2 = brentq(f, zc, E3 + 1e-9, xtol=1e-9)
    return z2, True


def _z1_depuis_e2(Q: float, sec: SectionBarrage, E2: float, V2: float, xi: float):
    """Cote amont Z1 telle que E1 = E2 + ξ max(0, V2² - V1²)/2g (racine fluviale)."""
    yc1 = (Q * Q / (G * sec.largeur ** 2)) ** (1.0 / 3.0)
    # En dessous de y_m, la fonction n'est plus monotone : borne basse sûre.
    z_bas = sec.cote_fond + yc1 * (1.0 + xi) ** (1.0 / 3.0)

    def h(z1):
        v1 = Q / (sec.largeur * (z1 - sec.cote_fond))
        return z1 + v1 * v1 / _DEUX_G - xi * max(0.0, V2 * V2 - v1 * v1) / _DEUX_G - E2

    if h(z_bas) >= 0.0:
        return z_bas, False
    z_haut = E2 + xi * V2 * V2 / _DEUX_G + 0.01
    return brentq(h, z_bas, z_haut, xtol=1e-9), True


def _energie_requise(q, b, zs, V3, E3, V1, xi):
    """Charge amont nécessaire pour faire passer q dans un groupe de passes."""
    z2, noye = _z2_expansion(q, b, zs, V3, E3)
    v2 = q / (b * (z2 - zs))
    e = z2 + v2 * v2 / _DEUX_G + xi * max(0.0, v2 * v2 - V1 * V1) / _DEUX_G
    return e, z2, v2, noye


def _debit_groupe(E1, V1, b, zs, V3, E3, xi):
    """Débit transitant par un groupe de passes pour une charge amont E1 donnée."""
    if E1 <= max(E3, zs) + 1e-12:
        return 0.0, True
    yc = (E1 - zs + xi * V1 * V1 / _DEUX_G) / (1.5 + xi / 2.0)
    if G * yc < V1 * V1:  # pas d'accélération : pas de perte de contraction
        yc = (E1 - zs) / 1.5
    if yc <= 0.0:
        return 0.0, True
    qc = b * math.sqrt(G * yc ** 3)

    def g(q):
        return _energie_requise(q, b, zs, V3, E3, V1, xi)[0] - E1

    if g(qc) <= 0.0:
        return qc, False
    q = brentq(g, 1e-12, qc, xtol=1e-9, rtol=1e-10)
    return q, True


def methode_energie(Q: float, ouvertures, sec: SectionBarrage, Z3: float, xi: float) -> ResultatMethode:
    """Méthode A : bilan d'énergie avec pertes singulières (Borda-Carnot) et contrôle critique."""
    grp = regrouper(ouvertures)
    if not grp:
        return ResultatMethode("A", math.inf, 0.0, math.inf, "aucune passe libre", False,
                               "Toutes les passes sont obstruées.")
    V3 = sec.vitesse(Q, Z3)
    E3 = Z3 + V3 * V3 / _DEUX_G

    if len(grp) == 1:
        b, zs = grp[0]
        z2, noye = _z2_expansion(Q, b, zs, V3, E3)
        v2 = Q / (b * (z2 - zs))
        e2 = z2 + v2 * v2 / _DEUX_G
        z1, ok = _z1_depuis_e2(Q, sec, e2, v2, xi)
        v1 = sec.vitesse(Q, z1)
        regime = "noyé (fluvial dans les passes)" if noye else "dénoyé (contrôle critique dans les passes)"
        return ResultatMethode("A", z1, v1, v2, regime, ok,
                               "" if ok else "Pas de solution fluviale à l'amont.", z2,
                               {"V3": V3, "E3": E3, "Z2": z2, "E2": e2, "yc2": (Q * Q / (G * b * b)) ** (1 / 3),
                                "b2": b, "zs": zs, "noye": noye, "xi": xi})

    # Plusieurs groupes de passes (cotes de seuil différentes) : répartition du débit.
    def residu(z1):
        v1 = sec.vitesse(Q, z1)
        e1 = z1 + v1 * v1 / _DEUX_G
        return sum(_debit_groupe(e1, v1, b, zs, V3, E3, xi)[0] for b, zs in grp) - Q

    z_bas = Z3
    z_haut = Z3 + 0.5
    while residu(z_haut) < 0.0:
        z_haut += 1.0 + (z_haut - Z3)
        if z_haut - Z3 > 200:
            raise RuntimeError("Méthode A : cote amont introuvable.")
    z1 = brentq(residu, z_bas, z_haut, xtol=1e-9)
    v1 = sec.vitesse(Q, z1)
    e1 = z1 + v1 * v1 / _DEUX_G
    debits, noyes = [], []
    for b, zs in grp:
        q, noye = _debit_groupe(e1, v1, b, zs, V3, E3, xi)
        debits.append(q)
        noyes.append(noye)
    a_libre = 0.0
    for (b, zs), q in zip(grp, debits):
        if q > 0:
            z2 = _z2_expansion(q, b, zs, V3, E3)[0]
            a_libre += b * (z2 - zs)
    v2 = Q / a_libre if a_libre > 0 else math.inf
    if all(noyes):
        regime = "noyé (fluvial dans les passes)"
    elif not any(noyes):
        regime = "dénoyé (contrôle critique dans les passes)"
    else:
        regime = "mixte (passes noyées et dénoyées)"
    return ResultatMethode("A", z1, v1, v2, regime, True, "", math.nan,
                           {"V3": V3, "E3": E3, "debits_groupes": debits, "groupes": grp, "xi": xi})


# --------------------------------------------------------------------------
# Méthode B : Yarnell (1934)
# --------------------------------------------------------------------------
def methode_yarnell(Q: float, ouvertures, sec: SectionBarrage, Z3: float, K: float) -> ResultatMethode:
    """Méthode B : formule empirique de Yarnell.

        Δh = 2 K (K + 10 ω - 0,6) (α + 15 α⁴) V3²/2g
    α : rapport surface obstruée / surface totale à l'aval, ω = V3²/(2 g y3).
    Domaine expérimental : α ≤ 0,5, écoulement fluvial non étranglé (classe A).
    """
    y3 = Z3 - sec.cote_fond
    a3 = sec.aire(Z3)
    v3 = Q / a3
    grp = regrouper(ouvertures)
    a_libre = surface_libre(grp, Z3)
    if a_libre <= 0.0:
        return ResultatMethode("B", math.nan, math.nan, math.inf, "hors domaine", False,
                               "Passes hors d'eau à l'aval : formule non applicable.")
    alpha = max(0.0, 1.0 - a_libre / a3)
    omega = v3 * v3 / (_DEUX_G * y3)
    terme = max(0.0, K + 10.0 * omega - 0.6)
    dh = 2.0 * K * terme * (alpha + 15.0 * alpha ** 4) * v3 * v3 / _DEUX_G
    z1 = Z3 + dh
    valide = alpha <= 0.5 + 1e-9
    remarque = "" if valide else f"α = {alpha:.2f} > 0,5 : hors du domaine expérimental de Yarnell."
    return ResultatMethode("B", z1, sec.vitesse(Q, z1), Q / a_libre, "fluvial (classe A)", valide,
                           remarque, math.nan, {"alpha": alpha, "omega": omega, "K": K, "dh": dh, "V3": v3})


# --------------------------------------------------------------------------
# Méthode C : d'Aubuisson (1840)
# --------------------------------------------------------------------------
def methode_aubuisson(Q: float, ouvertures, sec: SectionBarrage, Z3: float, K_A: float) -> ResultatMethode:
    """Méthode C : formule de d'Aubuisson.

        Q = K_A · Σ b_i (Z3 - z_seuil,i) · √(2 g Δh + V1²)
    résolue par point fixe sur Δh (V1 dépend de la cote amont Z3 + Δh).
    """
    grp = regrouper(ouvertures)
    a_libre = surface_libre(grp, Z3)
    if a_libre <= 0.0:
        return ResultatMethode("C", math.nan, math.nan, math.inf, "hors domaine", False,
                               "Passes hors d'eau à l'aval : formule non applicable.")
    v2p = Q / (K_A * a_libre)
    dh = 0.0
    for _ in range(200):
        v1 = sec.vitesse(Q, Z3 + dh)
        nouveau = max(0.0, (v2p * v2p - v1 * v1) / _DEUX_G)
        if abs(nouveau - dh) < 1e-10:
            dh = nouveau
            break
        dh = nouveau
    z1 = Z3 + dh
    return ResultatMethode("C", z1, sec.vitesse(Q, z1), Q / a_libre, "fluvial", True, "", math.nan,
                           {"dh": dh, "K_A": K_A, "A_libre": a_libre, "V2p": v2p})


# --------------------------------------------------------------------------
# Méthode D : lois de seuil dénoyé / noyé
# --------------------------------------------------------------------------
def debit_seuil(h1: float, h2: float, b: float, mu: float):
    """Débit d'un seuil rectangulaire (dénoyé ou noyé). Renvoie (q, 'dénoyé'|'noyé')."""
    if h1 <= 0.0:
        return 0.0, "à sec"
    mu_s = 1.5 * math.sqrt(3.0) * mu
    if h2 <= 2.0 / 3.0 * h1:
        return mu * b * math.sqrt(_DEUX_G) * h1 ** 1.5, "dénoyé"
    return mu_s * b * h2 * math.sqrt(_DEUX_G * max(h1 - h2, 0.0)), "noyé"


def methode_seuil(Q: float, ouvertures, sec: SectionBarrage, Z3: float, mu: float,
                  vitesse_approche: bool = False) -> ResultatMethode:
    """Méthode D : passes en parallèle, chacune régie par la loi de seuil dénoyé/noyé."""
    grp = regrouper(ouvertures)
    if not grp:
        return ResultatMethode("D", math.inf, 0.0, math.inf, "aucune passe libre", False)

    def charge(z1):
        if not vitesse_approche:
            return z1
        v1 = sec.vitesse(Q, z1)
        return z1 + v1 * v1 / _DEUX_G

    def total(z1):
        h = charge(z1)
        return sum(debit_seuil(h - zs, Z3 - zs, b, mu)[0] for b, zs in grp)

    z_bas = max(Z3, min(zs for _, zs in grp))
    if total(z_bas) >= Q:
        z1 = z_bas
    else:
        z_haut = z_bas + 0.5
        while total(z_haut) < Q:
            z_haut += 1.0 + (z_haut - z_bas)
            if z_haut - z_bas > 200:
                raise RuntimeError("Méthode D : cote amont introuvable.")
        z1 = brentq(lambda z: total(z) - Q, z_bas, z_haut, xtol=1e-9)
    h = charge(z1)
    regimes = {debit_seuil(h - zs, Z3 - zs, b, mu)[1] for b, zs in grp}
    regime = " / ".join(sorted(regimes))
    a_libre = surface_libre(grp, max(Z3, z1))
    return ResultatMethode("D", z1, sec.vitesse(Q, z1), Q / a_libre if a_libre > 0 else math.inf,
                           regime, True, "", math.nan,
                           {"mu": mu, "mu_s": 1.5 * math.sqrt(3) * mu, "h1": [h - zs for _, zs in grp],
                            "h2": [Z3 - zs for _, zs in grp]})
