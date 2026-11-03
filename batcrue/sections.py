"""Géométrie et hydraulique d'une section en travers de rivière.

La section est composée :
  * d'un lit mineur trapézoïdal (largeur au fond ``b``, fruit des berges ``m``,
    hauteur de berge ``h_berge``) ;
  * d'un lit majeur optionnel, à fond plat, de largeur cumulée ``B_maj``
    (rive gauche + rive droite), mis en eau au-dessus de la cote de berge.

Le frottement est décrit par la formule de Manning-Strickler (usage français) :

    Q = K · A · R^(2/3) · J^(1/2)

avec K le coefficient de Strickler [m^(1/3)/s], A la surface mouillée [m²],
R = A/P le rayon hydraulique [m] et J la pente de la ligne de charge [m/m].

Le lit composé est traité par la méthode des lits séparés (débitances
additionnées, interfaces verticales non comptées dans le périmètre mouillé),
avec le coefficient de Coriolis α pour l'énergie cinétique.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.optimize import brentq, minimize_scalar

from .constantes import G


@dataclass(frozen=True)
class Section:
    """Section en travers (lit mineur trapézoïdal + lit majeur optionnel)."""

    z_fond: float               # cote du fond du lit mineur [m NGF]
    b: float                    # largeur au fond du lit mineur [m]
    m: float = 0.0              # fruit des berges (horizontal / vertical) [-]
    h_berge: float = math.inf   # profondeur à plein bord [m]
    B_maj: float = 0.0          # largeur cumulée du lit majeur actif [m]
    K_min: float = 30.0         # Strickler du lit mineur [m^1/3/s]
    K_maj: float = 15.0         # Strickler du lit majeur [m^1/3/s]

    # ------------------------------------------------------------------ géométrie
    def _sous_sections(self, y: float):
        """Liste de tuples (A, P, T, K) : lit mineur puis lit majeur s'il est en eau."""
        if y <= 0.0:
            return [(0.0, 0.0, 0.0, self.K_min)]
        s = math.sqrt(1.0 + self.m * self.m)
        if self.B_maj > 0.0 and y > self.h_berge:
            hb = self.h_berge
            t_berge = self.b + 2.0 * self.m * hb
            a_min = (self.b + self.m * hb) * hb + t_berge * (y - hb)
            p_min = self.b + 2.0 * hb * s
            hm = y - hb
            return [(a_min, p_min, t_berge, self.K_min),
                    (self.B_maj * hm, self.B_maj, self.B_maj, self.K_maj)]
        a = (self.b + self.m * y) * y
        p = self.b + 2.0 * y * s
        t = self.b + 2.0 * self.m * y
        return [(a, p, t, self.K_min)]

    def proprietes(self, y: float):
        """Renvoie (A, P, T, débitance Kd, coefficient de Coriolis α) pour la profondeur y."""
        subs = self._sous_sections(y)
        a_tot = p_tot = t_tot = kd_tot = 0.0
        somme_k3_a2 = 0.0
        for a, p, t, k in subs:
            a_tot += a
            p_tot += p
            t_tot += t
            if a > 0.0 and p > 0.0:
                kd = k * a * (a / p) ** (2.0 / 3.0)
                kd_tot += kd
                somme_k3_a2 += kd ** 3 / (a * a)
        if kd_tot > 0.0 and len(subs) > 1:
            alpha = somme_k3_a2 * a_tot * a_tot / kd_tot ** 3
        else:
            alpha = 1.0
        return a_tot, p_tot, t_tot, kd_tot, alpha

    def aire(self, y: float) -> float:
        return self.proprietes(y)[0]

    def largeur_miroir(self, y: float) -> float:
        return self.proprietes(y)[2]

    def debitance(self, y: float) -> float:
        return self.proprietes(y)[3]

    @property
    def cote_berge(self) -> float:
        return self.z_fond + self.h_berge if math.isfinite(self.h_berge) else math.inf

    # ---------------------------------------------------------------- hydraulique
    def hauteur_normale(self, Q: float, pente: float) -> float:
        """Hauteur normale (régime uniforme de Manning-Strickler) [m]."""
        if Q <= 0.0:
            return 0.0
        if pente <= 0.0:
            raise ValueError("La pente doit être strictement positive pour une hauteur normale.")
        rac = math.sqrt(pente)

        def f(y):
            return self.debitance(y) * rac - Q

        y_haut = 1.0
        while f(y_haut) < 0.0:
            y_haut *= 2.0
            if y_haut > 1e4:
                raise ValueError("Hauteur normale introuvable (débit trop fort ?).")
        return brentq(f, 1e-9, y_haut, xtol=1e-7, rtol=1e-10)

    def hauteur_critique(self, Q: float) -> float:
        """Hauteur critique [m] (minimum de la charge spécifique, Bélanger)."""
        if Q <= 0.0:
            return 0.0

        def froude2_trapeze(y):
            a = (self.b + self.m * y) * y
            t = self.b + 2.0 * self.m * y
            return Q * Q * t / (G * a ** 3) - 1.0

        y_haut = 1.0
        while froude2_trapeze(y_haut) > 0.0:
            y_haut *= 2.0
        yc = brentq(froude2_trapeze, 1e-9, y_haut, xtol=1e-8)
        if self.B_maj > 0.0 and yc > self.h_berge:
            # Section composée : on cherche le minimum de la charge spécifique.
            res = minimize_scalar(lambda y: self.charge_specifique(Q, y),
                                  bounds=(1e-6, yc * 1.5), method="bounded")
            yc = float(res.x)
        return yc

    def charge_specifique(self, Q: float, y: float) -> float:
        """Charge spécifique E = y + α Q² / (2 g A²) [m]."""
        a, _, _, _, alpha = self.proprietes(y)
        if a <= 0.0:
            return math.inf
        return y + alpha * Q * Q / (2.0 * G * a * a)

    def froude(self, Q: float, y: float) -> float:
        a, _, t, _, alpha = self.proprietes(y)
        if a <= 0.0:
            return math.inf
        return math.sqrt(alpha * Q * Q * t / (G * a ** 3))

    def vitesse(self, Q: float, y: float) -> float:
        a = self.aire(y)
        return Q / a if a > 0 else math.inf

    def pente_frottement(self, Q: float, y: float) -> float:
        kd = self.debitance(y)
        return (Q / kd) ** 2 if kd > 0 else math.inf

    def decalee(self, z_fond: float) -> "Section":
        """Même section avec une autre cote de fond."""
        return Section(z_fond, self.b, self.m, self.h_berge, self.B_maj, self.K_min, self.K_maj)
