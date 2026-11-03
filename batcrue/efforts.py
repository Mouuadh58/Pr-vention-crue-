"""Efforts hydrauliques sur le batardeau et risque de renard (ordres de grandeur).

* Poussée hydrostatique par mètre linéaire, enceinte asséchée :
      F = ½ ρ g h²     appliquée à h/3 au-dessus du fond
* Supplément dynamique (pression d'arrêt sur la face exposée au courant) :
      Fd = ½ ρ V² · h  (par mètre linéaire)
* Renard hydraulique, règle de Lane (1935) : longueur de cheminement pondérée
      Lw = Lv + Lh/3 ≥ C_L · ΔH
  avec C_L le coefficient de Lane du sol de fondation.

Ces vérifications ne remplacent pas la note de calcul du fournisseur du
batardeau ni l'étude géotechnique.
"""
from __future__ import annotations

from .constantes import G, RHO_EAU

COEFFICIENTS_LANE = {
    "Sable très fin ou limon": 8.5,
    "Sable fin": 7.0,
    "Sable moyen": 6.0,
    "Sable grossier": 5.0,
    "Gravier fin": 4.0,
    "Gravier moyen": 3.5,
    "Gravier grossier et galets": 3.0,
    "Blocs, galets et graviers": 2.5,
    "Argile molle": 3.0,
    "Argile moyenne": 2.0,
    "Argile raide": 1.8,
    "Argile très raide": 1.6,
}


def poussee_hydrostatique(h: float) -> float:
    """Poussée hydrostatique [N/m] pour une hauteur d'eau h [m] (enceinte à sec)."""
    h = max(h, 0.0)
    return 0.5 * RHO_EAU * G * h * h


def moment_hydrostatique(h: float) -> float:
    """Moment au pied [N·m/m] de la poussée hydrostatique (bras de levier h/3)."""
    h = max(h, 0.0)
    return poussee_hydrostatique(h) * h / 3.0


def effort_dynamique(V: float, h: float) -> float:
    """Supplément d'effort dû à la pression d'arrêt ½ρV² sur la hauteur h [N/m]."""
    return 0.5 * RHO_EAU * V * V * max(h, 0.0)


def verification_lane(delta_h: float, l_vertical: float, l_horizontal: float, sol: str) -> dict:
    """Vérification du renard par la règle de Lane."""
    c = COEFFICIENTS_LANE[sol]
    lw = l_vertical + l_horizontal / 3.0
    dh_max = lw / c
    ratio = lw / delta_h if delta_h > 0 else float("inf")
    return {"C_L": c, "L_w": lw, "delta_h_max": dh_max, "ratio": ratio, "ok": ratio >= c}
