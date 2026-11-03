"""Vitesses, protection par enrochements et affouillement (ordres de grandeur).

* Formule d'Isbash (reprise dans le Guide Enrochement CIRIA/CUR/CETMEF, 2009) :
      U_cr = C · √(2 g Δ D)    ⇒    D = U² / (2 g Δ C²)
  Δ = (ρs - ρw)/ρw densité déjaugée relative ; C = 0,86 (blocs exposés,
  forte turbulence, cas du nez de batardeau) ou 1,20 (blocs encastrés).

* Affouillement général de contraction en lit mobile (Laursen, 1960, repris par
  HEC-18) : y2/y1 = (Q2/Q1)^(6/7) · (W1/W2)^k1 avec Q2 = Q1 (tout le débit
  passe dans la section rétrécie) ; k1 = 0,59 (charriage), 0,64 (mixte),
  0,69 (suspension). Valable seulement si le fond est affouillable (pas de
  radier béton) : à confirmer par une étude spécifique.
"""
from __future__ import annotations

import math

from .constantes import G, RHO_EAU


def diametre_isbash(V: float, rho_s: float = 2650.0, C: float = 0.86) -> float:
    """Diamètre des blocs (sphère équivalente) stables sous la vitesse V [m]."""
    delta = (rho_s - RHO_EAU) / RHO_EAU
    return V * V / (2.0 * G * delta * C * C)


def masse_bloc(D: float, rho_s: float = 2650.0) -> float:
    """Masse d'un bloc sphérique équivalent de diamètre D [kg]."""
    return rho_s * math.pi * D ** 3 / 6.0


def affouillement_contraction(y1: float, W1: float, W2: float, k1: float = 0.64) -> float:
    """Approfondissement général dans la section rétrécie (Laursen, lit mobile) [m]."""
    if W2 <= 0:
        return math.inf
    return y1 * ((W1 / W2) ** k1 - 1.0)
