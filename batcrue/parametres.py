"""Jeu de paramètres de l'étude : valeurs par défaut, contrôle de cohérence, import/export JSON.

Les valeurs par défaut décrivent un **barrage type fictif** inspiré de l'Oise
moyenne (3 passes de 20 m, crue centennale ≈ 690 m³/s). Elles servent de
démonstration et doivent être remplacées par les données réelles du barrage
étudié (plans VNF, levés bathymétriques, loi hauteur-débit aval, études PPRI).
"""
from __future__ import annotations

import copy
import json
import math
from datetime import date

from .efforts import COEFFICIENTS_LANE
from .ouvrage import FORMES

MOIS = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]

DEFAUTS: dict = {
    # ------------------------------------------------------------- projet
    "nom_projet": "Impact hydraulique d'un batardeau de passe – étude type",
    "nom_barrage": "Barrage type de l'Oise (données d'exemple)",
    "auteur": "",
    "commentaire": ("Données fictives mais réalistes, à remplacer par les données du barrage "
                    "(plans VNF, levés bathymétriques, loi hauteur-débit aval, études PPRI)."),
    # ------------------------------------------------------------- barrage
    "largeur_riviere": 66.0,      # largeur hydraulique au droit du barrage (hors écluse) [m]
    "cote_fond": 20.00,           # cote du fond au droit du barrage [m NGF]
    "regulation": True,           # le barrage maintient la retenue normale tant qu'il le peut
    "rn_amont": 25.00,            # retenue normale amont [m NGF]
    "forme_piles": "arrondi",
    "passes": [
        {"nom": "Passe navigable", "largeur": 20.0, "cote_seuil": 20.0, "obstruction": 1.0},
        {"nom": "Pertuis 1", "largeur": 20.0, "cote_seuil": 20.0, "obstruction": 0.0},
        {"nom": "Pertuis 2", "largeur": 20.0, "cote_seuil": 20.0, "obstruction": 0.0},
    ],
    # ------------------------------------------------------------- batardeau
    "type_batardeau": "Batardeau flottant de passe",
    "forme_batardeau": "carre",
    "cote_arase": 26.80,          # cote de crête du batardeau [m NGF]
    "revanche": 0.30,             # revanche de sécurité sous la crête [m]
    "longueur_batardeau": 25.0,   # emprise dans le sens du courant [m]
    "cote_fond_enceinte": 20.00,  # cote du fond de l'enceinte asséchée [m NGF]
    "debut_travaux": "2027-05-01",
    "fin_travaux": "2027-10-31",
    # ------------------------------------------------------------- bief amont
    "mode_bief": "prismatique",   # "prismatique" ou "tableau"
    "b_min": 50.0,                # largeur au fond du lit mineur [m]
    "m_berge": 2.0,               # fruit des berges (H/V)
    "h_berge": 6.0,               # hauteur de berge (plein bord) [m]
    "B_maj": 300.0,               # largeur cumulée du lit majeur actif [m]
    "K_min": 30.0,                # Strickler lit mineur
    "K_maj": 15.0,                # Strickler lit majeur
    "pente": 0.0002,              # pente moyenne du fond [m/m]
    "longueur_bief": 12000.0,     # longueur étudiée vers l'amont [m]
    "pas_calcul": 100.0,          # pas d'espace de la courbe de remous [m]
    "sections_tabulees": [
        {"x": 0.0, "z_fond": 20.0, "b": 50.0, "m": 2.0, "h_berge": 6.0, "B_maj": 300.0, "K_min": 30.0, "K_maj": 15.0},
        {"x": 6000.0, "z_fond": 21.2, "b": 48.0, "m": 2.0, "h_berge": 6.0, "B_maj": 350.0, "K_min": 30.0, "K_maj": 15.0},
        {"x": 12000.0, "z_fond": 22.4, "b": 52.0, "m": 2.0, "h_berge": 6.0, "B_maj": 300.0, "K_min": 30.0, "K_maj": 15.0},
    ],
    "enjeux": [
        {"nom": "Pont routier (exemple)", "x": 1500.0, "cote_dommages": 28.20},
        {"nom": "Quartier riverain (exemple)", "x": 4000.0, "cote_dommages": 27.90},
        {"nom": "Pied du barrage amont", "x": 12000.0, "cote_dommages": math.nan},
    ],
    # ------------------------------------------------------------- aval
    "mode_aval": "normale",       # "normale", "tableau" ou "constante"
    "rn_aval": 23.00,             # retenue normale du bief aval [m NGF]
    "decalage_aval": 0.0,         # décalage appliqué à la cote aval (sensibilité) [m]
    "cote_aval_constante": 25.0,
    "loi_aval": [
        {"Q": 50.0, "Z": 23.00}, {"Q": 150.0, "Z": 23.17}, {"Q": 250.0, "Z": 24.27},
        {"Q": 350.0, "Z": 25.19}, {"Q": 450.0, "Z": 25.99}, {"Q": 550.0, "Z": 26.50},
        {"Q": 650.0, "Z": 26.91}, {"Q": 800.0, "Z": 27.43},
    ],
    # ------------------------------------------------------------- hydrologie
    "mode_hydro": "gumbel",       # "gumbel" ou "quantiles"
    "gumbel_u": 283.0,            # paramètre de position [m³/s]
    "gumbel_beta": 88.0,          # paramètre d'échelle [m³/s]
    "quantiles": [
        {"T": 2, "Q": 315.0}, {"T": 5, "Q": 415.0}, {"T": 10, "Q": 481.0},
        {"T": 20, "Q": 544.0}, {"T": 50, "Q": 626.0}, {"T": 100, "Q": 688.0},
    ],
    "module": 100.0,              # débit moyen interannuel [m³/s]
    "crues_historiques": [],      # [{"nom": ..., "Q": ...}]
    "T_reference": 100,           # crue de référence de l'étude d'impact [ans]
    "T_chantier": 10,             # crue de chantier [ans]
    "saisonnalite": "uniforme",   # "uniforme" ou "personnalisee"
    "poids_mensuels": [1.0] * 12,
    # ------------------------------------------------------------- critères
    "seuil_dz": 0.05,             # surélévation admissible (à fixer avec la police de l'eau) [m]
    "proba_acceptable": 0.05,     # probabilité acceptable pendant les travaux [-]
    "vitesse_admissible": 2.0,    # vitesse admissible dans les passes / au pied [m/s]
    "k_vitesse_locale": 1.5,      # facteur de survitesse locale au nez du batardeau
    "rho_enrochement": 2650.0,
    "C_isbash": 0.86,
    "fond_affouillable": False,
    "k1_laursen": 0.64,
    # ------------------------------------------------------------- coefficients
    "coefs_personnalises": False,
    "xi_ref": FORMES["arrondi"]["xi"],
    "xi_bat": FORMES["carre"]["xi"],
    "K_yarnell_ref": FORMES["arrondi"]["K_yarnell"],
    "K_yarnell_bat": FORMES["carre"]["K_yarnell"],
    "K_A": 1.0,                   # coefficient de d'Aubuisson
    "mu": 0.385,                  # coefficient de débit du seuil dénoyé
    "vitesse_approche_seuil": False,
    "methodes_actives": ["A", "B", "C", "D"],
    "methode_ligne_eau": "enveloppe",
    # ------------------------------------------------------------- hydrogramme
    "hydro_mode": "synthetique",  # "synthetique" ou "csv"
    "hydro_T": 10,
    "hydro_t_pic": 96.0,          # temps de montée [h]
    "hydro_duree": 360.0,         # durée simulée [h]
    "hydro_Qb": 100.0,            # débit de base [m³/s]
    "hydro_csv": None,            # [[t_h, Q], ...] si importé
    # ------------------------------------------------------------- efforts / renard
    "lane_applicable": False,     # batardeau fondé sur sol meuble (palplanches, remblai)
    "sol_fondation": "Sable moyen",
    "l_cheminement_v": 12.0,      # cheminement vertical (ex. 2 × fiche des palplanches) [m]
    "l_cheminement_h": 2.0,       # cheminement horizontal [m]
    # ------------------------------------------------------------- incertitudes
    "mc_n": 300,
    "mc_graine": 1,
    "incert_strickler": 0.20,     # ± relatif
    "incert_debit": 0.10,         # ± relatif
    "incert_aval": 0.20,          # ± absolu [m]
    # ------------------------------------------------------------- Hub'Eau
    "code_station": "",
}

CLES_TABLES = {"passes", "sections_tabulees", "enjeux", "loi_aval", "quantiles", "crues_historiques"}


def defauts() -> dict:
    return copy.deepcopy(DEFAUTS)


def completer(params: dict | None) -> dict:
    """Complète un jeu de paramètres partiel avec les valeurs par défaut."""
    p = defauts()
    if params:
        for k, v in params.items():
            if k in p:
                p[k] = copy.deepcopy(v)
    return p


def appliquer_formes(p: dict) -> dict:
    """Si les coefficients ne sont pas personnalisés, les déduit des formes choisies."""
    if not p.get("coefs_personnalises"):
        fp = FORMES.get(p["forme_piles"], FORMES["arrondi"])
        fb = FORMES.get(p["forme_batardeau"], FORMES["carre"])
        p["xi_ref"], p["K_yarnell_ref"] = fp["xi"], fp["K_yarnell"]
        p["xi_bat"], p["K_yarnell_bat"] = fb["xi"], fb["K_yarnell"]
    return p


def _num(v, defaut=math.nan) -> float:
    try:
        x = float(v)
        return x
    except (TypeError, ValueError):
        return defaut


def valider(params: dict) -> tuple[list[str], list[str]]:
    """Contrôle de cohérence. Renvoie (erreurs bloquantes, avertissements)."""
    p = completer(params)
    err, warn = [], []
    passes = p["passes"]
    if not passes:
        err.append("Aucune passe n'est définie pour le barrage.")
    larg = sum(_num(x.get("largeur"), 0) for x in passes)
    if larg <= 0:
        err.append("La largeur totale des passes doit être positive.")
    if larg > p["largeur_riviere"] + 1e-6:
        err.append(f"La somme des largeurs de passes ({larg:.1f} m) dépasse la largeur de la rivière "
                   f"au droit du barrage ({p['largeur_riviere']:.1f} m).")
    obst = sum(_num(x.get("largeur"), 0) * min(max(_num(x.get("obstruction"), 0), 0), 1) for x in passes)
    if obst <= 0:
        warn.append("Aucune passe n'est obstruée : le batardeau n'a pas d'emprise (impact nul).")
    if larg > 0 and obst >= larg - 1e-9:
        err.append("Toutes les passes sont obstruées : aucun écoulement possible.")
    for x in passes:
        o = _num(x.get("obstruction"), 0)
        if o < 0 or o > 1:
            warn.append(f"Passe « {x.get('nom')} » : le taux d'obstruction doit être compris entre 0 et 1.")
        if _num(x.get("cote_seuil"), p["cote_fond"]) < p["cote_fond"] - 1e-6:
            warn.append(f"Passe « {x.get('nom')} » : seuil sous le fond de la rivière.")
    if p["regulation"] and p["rn_amont"] <= p["cote_fond"]:
        err.append("La retenue normale amont doit être au-dessus du fond.")
    if p["regulation"] and p["mode_aval"] != "tableau" and p["rn_aval"] >= p["rn_amont"]:
        warn.append("La retenue aval est supérieure ou égale à la retenue amont.")
    if p["pente"] <= 0 and (p["mode_aval"] == "normale" or p["mode_bief"] == "prismatique"):
        err.append("La pente doit être strictement positive (hauteur normale, bief prismatique).")
    for k in ("K_min", "K_maj"):
        if p[k] <= 0:
            err.append(f"Le coefficient de Strickler {k} doit être positif.")
    if p["K_min"] < 15 or p["K_min"] > 60:
        warn.append("Strickler du lit mineur inhabituel (valeurs courantes 20 à 45 en rivière).")
    if p["gumbel_beta"] <= 0 and p["mode_hydro"] == "gumbel":
        err.append("Le paramètre d'échelle de Gumbel doit être positif.")
    if p["mode_aval"] == "tableau" and len(p["loi_aval"]) < 2:
        err.append("La loi hauteur-débit aval doit comporter au moins deux points.")
    if p["mode_bief"] == "tableau" and len(p["sections_tabulees"]) < 2:
        err.append("Il faut au moins deux profils en travers tabulés.")
    try:
        d0, d1 = date.fromisoformat(str(p["debut_travaux"])), date.fromisoformat(str(p["fin_travaux"]))
        if d1 < d0:
            err.append("La fin des travaux précède leur début.")
    except ValueError:
        err.append("Dates de travaux invalides (format AAAA-MM-JJ attendu).")
    if p["sol_fondation"] not in COEFFICIENTS_LANE:
        warn.append("Type de sol inconnu pour la règle de Lane.")
    if p["pas_calcul"] <= 0 or p["longueur_bief"] <= 0:
        err.append("Longueur de bief et pas de calcul doivent être positifs.")
    if not p["methodes_actives"]:
        err.append("Au moins une méthode de calcul doit être active.")
    return err, warn


# ------------------------------------------------------------------ JSON
def _nettoyer(v):
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, dict):
        return {k: _nettoyer(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_nettoyer(x) for x in v]
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "item"):  # types numpy
        return _nettoyer(v.item())
    return v


def vers_json(params: dict) -> str:
    return json.dumps(_nettoyer(params), ensure_ascii=False, indent=2)


def depuis_json(texte: str | bytes) -> dict:
    if isinstance(texte, bytes):
        texte = texte.decode("utf-8-sig")
    brut = json.loads(texte)
    if not isinstance(brut, dict):
        raise ValueError("Fichier de paramètres invalide.")
    p = completer(brut)
    for e in p["enjeux"]:
        if e.get("cote_dommages") is None:
            e["cote_dommages"] = math.nan
    return p
