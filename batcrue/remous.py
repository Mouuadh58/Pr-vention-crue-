"""Courbe de remous (ligne d'eau en régime permanent graduellement varié).

Méthode des pas standards (« standard step », équation de Bernoulli entre
deux sections successives, intégrée de l'aval vers l'amont en régime fluvial) :

    Z_u + α_u V_u²/2g = Z_d + α_d V_d²/2g + Δx · J̄ + C · |α_u V_u²/2g - α_d V_d²/2g|

    J̄ = (Q / K̄d)²  avec K̄d la débitance moyenne des deux sections (Strickler),
    C  = coefficient de contraction (0,1) ou d'élargissement (0,3) entre sections.

Une variante par intégration directe de l'équation différentielle de Bresse

    dy/dx = (I - J) / (1 - Fr²)

(schéma de Heun, d'ordre 2) est fournie pour la vérification croisée avec le
classeur Excel.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy.optimize import brentq

from .constantes import G
from .sections import Section


@dataclass
class LigneEau:
    """Ligne d'eau calculée (x = distance vers l'amont depuis le barrage)."""

    x: np.ndarray
    Z: np.ndarray
    z_fond: np.ndarray
    z_berge: np.ndarray
    V: np.ndarray
    Fr: np.ndarray
    critique: np.ndarray  # True si la solution fluviale n'existe pas (hauteur critique imposée)


def grille(x_max: float, dx: float) -> np.ndarray:
    n = max(1, int(math.ceil(x_max / dx - 1e-9)))
    return np.linspace(0.0, x_max, n + 1)


def ligne_eau_pas_standard(Q: float, Z_depart: float, section_en: Callable[[float], Section],
                           x_max: float, dx: float, c_contraction: float = 0.1,
                           c_elargissement: float = 0.3) -> LigneEau:
    """Intègre la ligne d'eau de l'aval (x = 0) vers l'amont (x = x_max)."""
    xs = grille(x_max, dx)
    n = len(xs)
    Z = np.empty(n)
    zf = np.empty(n)
    zb = np.empty(n)
    V = np.empty(n)
    Fr = np.empty(n)
    crit = np.zeros(n, dtype=bool)

    sec = section_en(xs[0])
    Z[0] = Z_depart
    zf[0], zb[0] = sec.z_fond, sec.cote_berge
    y = max(Z_depart - sec.z_fond, 1e-6)
    a, _, _, kd_d, al_d = sec.proprietes(y)
    hv_d = al_d * Q * Q / (2 * G * a * a)
    V[0], Fr[0] = Q / a, sec.froude(Q, y)

    for i in range(1, n):
        sec = section_en(xs[i])
        L = xs[i] - xs[i - 1]
        z_d = Z[i - 1]
        yc = sec.hauteur_critique(Q)
        e_d = z_d + hv_d

        def F(z_u, sec=sec, L=L, e_d=e_d, kd_d=kd_d, hv_d=hv_d):
            yu = z_u - sec.z_fond
            au, _, _, kdu, alu = sec.proprietes(yu)
            hvu = alu * Q * Q / (2 * G * au * au)
            j = (2.0 * Q / (kdu + kd_d)) ** 2
            c = c_contraction if hv_d > hvu else c_elargissement
            return z_u + hvu - e_d - L * j - c * abs(hvu - hv_d)

        z_bas = sec.z_fond + yc * 1.0001
        if F(z_bas) > 0.0:
            z_u = z_bas
            crit[i] = True
        else:
            z_haut = max(z_d, z_bas) + 2.0
            while F(z_haut) < 0.0:
                z_haut += 5.0
            z_u = brentq(F, z_bas, z_haut, xtol=1e-7)
        Z[i] = z_u
        zf[i], zb[i] = sec.z_fond, sec.cote_berge
        yu = z_u - sec.z_fond
        a, _, _, kd_d, al_d = sec.proprietes(yu)
        hv_d = al_d * Q * Q / (2 * G * a * a)
        V[i], Fr[i] = Q / a, sec.froude(Q, yu)
    return LigneEau(xs, Z, zf, zb, V, Fr, crit)


def ligne_eau_bresse_heun(Q: float, Z_depart: float, section0: Section, pente: float,
                          x_max: float, dx: float) -> LigneEau:
    """Intégration de dy/ds = -(I - J)/(1 - Fr²) vers l'amont (s = distance amont), schéma de Heun.

    Section prismatique : z_fond(s) = z_fond0 + I·s. Coriolis pris égal à 1
    (formulation identique à celle du classeur Excel).
    """
    xs = grille(x_max, dx)

    def pente_y(y):
        a, _, t, kd, _ = section0.proprietes(y)
        j = (Q / kd) ** 2
        fr2 = Q * Q * t / (G * a ** 3)
        return -(pente - j) / (1.0 - fr2)

    y = np.empty(len(xs))
    y[0] = Z_depart - section0.z_fond
    for i in range(1, len(xs)):
        h = xs[i] - xs[i - 1]
        k1 = pente_y(y[i - 1])
        k2 = pente_y(y[i - 1] + h * k1)
        y[i] = y[i - 1] + 0.5 * h * (k1 + k2)
    zf = section0.z_fond + pente * xs
    Z = zf + y
    V = np.array([section0.vitesse(Q, yy) for yy in y])
    Fr = np.array([section0.froude(Q, yy) for yy in y])
    zb = zf + section0.h_berge
    return LigneEau(xs, Z, zf, zb, V, Fr, np.zeros(len(xs), dtype=bool))


def section_prismatique(section0: Section, pente: float) -> Callable[[float], Section]:
    """Fabrique de sections prismatiques : fond qui remonte de I·x vers l'amont."""
    def f(x):
        return section0.decalee(section0.z_fond + pente * x)
    return f


def section_interpolee(table: list[dict]) -> Callable[[float], Section]:
    """Fabrique de sections interpolées linéairement entre profils en travers tabulés.

    ``table`` : liste de dict avec les clés x, z_fond, b, m, h_berge, B_maj, K_min, K_maj.
    """
    lignes = sorted(table, key=lambda r: float(r["x"]))
    if len(lignes) < 2:
        raise ValueError("Il faut au moins deux profils en travers.")
    cles = ["z_fond", "b", "m", "h_berge", "B_maj", "K_min", "K_maj"]
    xs = np.array([float(r["x"]) for r in lignes])
    vals = {k: np.array([float(r[k]) for r in lignes]) for k in cles}

    def f(x):
        v = {k: float(np.interp(x, xs, vals[k])) for k in cles}
        return Section(v["z_fond"], v["b"], v["m"], v["h_berge"], v["B_maj"], v["K_min"], v["K_maj"])
    return f
