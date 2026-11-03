"""Double calcul : compare les résultats du classeur Excel à ceux du moteur Python.

Usage :  python excel/verifier_classeur.py classeur_recalcule.xlsx

Le classeur doit avoir été recalculé (ouvert et enregistré dans Excel ou LibreOffice) afin que
les valeurs des formules soient stockées. Le script lit les données saisies dans la feuille
« Données », refait l'étude avec le moteur Python et affiche les écarts.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import numpy as np
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from batcrue import EtudeBatardeau, defauts  # noqa: E402
from batcrue.remous import ligne_eau_bresse_heun  # noqa: E402


def lire_noms(wb) -> dict:
    vals = {}
    for nom, dn in wb.defined_names.items():
        feuille, cellule = list(dn.destinations)[0]
        vals[nom] = wb[feuille][cellule.replace("$", "")].value
    return vals


def params_depuis_classeur(n: dict) -> dict:
    p = defauts()
    l_passes, l_obst = float(n["L_passes"]), float(n["L_obstruee"])
    p.update({
        "largeur_riviere": n["B_riv"], "cote_fond": n["Z_fond"], "regulation": bool(n["Regulation"]),
        "rn_amont": n["RN_amont"], "cote_arase": n["Crete"], "revanche": n["Revanche"],
        "passes": [{"nom": "Passes obstruées", "largeur": l_obst, "cote_seuil": n["Z_seuil"], "obstruction": 1.0},
                   {"nom": "Passes libres", "largeur": l_passes - l_obst, "cote_seuil": n["Z_seuil"], "obstruction": 0.0}],
        "coefs_personnalises": True, "xi_ref": n["Xi_piles"], "xi_bat": n["Xi_bat"],
        "K_yarnell_ref": n["K_Y_piles"], "K_yarnell_bat": n["K_Y_bat"], "K_A": n["K_A"], "mu": n["Mu"],
        "vitesse_approche_seuil": False,
        "methodes_actives": [m for m in "ABCD" if int(n[f"Actif_{m}"]) == 1],
        "mode_bief": "prismatique", "mode_aval": "normale", "b_min": n["Lit_b"], "m_berge": n["Lit_m"],
        "h_berge": n["Lit_hb"], "B_maj": n["Lit_Bmaj"], "K_min": n["K_min"], "K_maj": n["K_maj"],
        "pente": n["Pente"], "rn_aval": n["RN_aval"], "decalage_aval": n["Decal_aval"],
        "longueur_bief": n["L_bief"], "pas_calcul": float(n["L_bief"]) / 120.0,
        "mode_hydro": "gumbel", "gumbel_u": n["Gu"], "gumbel_beta": n["Gbeta"], "module": n["Module"],
        "T_reference": n["T_ref"], "T_chantier": n["T_ch"], "seuil_dz": n["Seuil_dz"],
        "proba_acceptable": n["P_acc"], "saisonnalite": "personnalisee",
        "poids_mensuels": [float(n[f"Poids_{k}"]) for k in range(1, 13)],
    })
    for cle in ("Date_debut", "Date_fin"):
        v = n[cle]
        v = v.date() if isinstance(v, datetime) else v
        p["debut_travaux" if cle == "Date_debut" else "fin_travaux"] = v.isoformat() if isinstance(v, date) else str(v)
    return p


def verifier(chemin: str) -> int:
    wb = load_workbook(chemin, data_only=True)
    n = lire_noms(wb)
    if n.get("Frac_alea") is None:
        print("Le classeur n'a pas été recalculé : ouvrez-le et enregistrez-le dans Excel ou LibreOffice.")
        return 2
    p = params_depuis_classeur(n)
    e = EtudeBatardeau(p)
    ws = wb["Calculs"]
    entetes = {ws.cell(4, j).value: j for j in range(1, ws.max_column + 1)}
    ecarts = []

    def comparer(nom, v_xl, v_py, tol):
        ok = v_xl is not None and abs(float(v_xl) - float(v_py)) <= tol
        ecarts.append((nom, v_xl, v_py, ok))

    for r in range(5, 14):
        lib = ws.cell(r, 1).value
        q = ws.cell(r, entetes["Q (m³/s)"]).value
        res = e.calcul_debit(float(q))
        comparer(f"{lib} : cote aval", ws.cell(r, entetes["Z aval (m NGF)"]).value, res.Z3, 0.002)
        for m in e.methodes:
            comparer(f"{lib} : ΔZ méthode {m}", ws.cell(r, entetes[f"{m} : ΔZ (m)"]).value, res.dZ[m], 0.002)
        comparer(f"{lib} : ΔZ enveloppe", ws.cell(r, entetes["ΔZ enveloppe (m)"]).value, res.dZ_env, 0.002)
        comparer(f"{lib} : Z amont avec", ws.cell(r, entetes["Z amont avec (m NGF)"]).value, res.Z_bat_env, 0.003)
    comparer("Part de l'aléa annuel", n["Frac_alea"], e.fraction_alea, 1e-6)
    q_s = e.debit_seuil_impact()
    comparer("Débit d'atteinte du seuil", n["Q_seuil"], q_s if q_s else 1e9, 3.0)
    q_c = e.debit_submersion()
    comparer("Débit de submersion", n["Q_sub"], q_c if q_c else 1e9, 3.0)
    # Courbe de remous : même schéma (Bresse + Heun, Coriolis = 1)
    wr = wb["Remous"]
    q_r = float(wr["B3"].value)
    z_s, z_a = float(wr["D3"].value), float(wr["E3"].value)
    sec0 = e.section_ref
    py_s = ligne_eau_bresse_heun(q_r, z_s, sec0, float(p["pente"]), float(p["longueur_bief"]), float(p["pas_calcul"]))
    py_a = ligne_eau_bresse_heun(q_r, z_a, sec0, float(p["pente"]), float(p["longueur_bief"]), float(p["pas_calcul"]))
    xl_s = np.array([wr.cell(6 + i, 24).value for i in range(len(py_s.x))], dtype=float)
    xl_a = np.array([wr.cell(6 + i, 25).value for i in range(len(py_a.x))], dtype=float)
    comparer("Remous : écart max sur Z sans (m)", float(np.max(np.abs(xl_s - py_s.Z))), 0.0, 0.002)
    comparer("Remous : écart max sur Z avec (m)", float(np.max(np.abs(xl_a - py_a.Z))), 0.0, 0.002)
    le = e.ligne_eau(q_r)  # méthode des pas standards de l'application (avec Coriolis)
    dz_xl = xl_a - xl_s
    comparer("Remous : ΔZ Excel vs application (écart max, m)",
             float(np.max(np.abs(dz_xl - le["dZ"].to_numpy()))), 0.0, 0.005)
    largeur = max(len(x[0]) for x in ecarts)
    nb_ko = 0
    for nom, vx, vp, ok in ecarts:
        nb_ko += not ok
        print(f"{'OK ' if ok else 'ÉCART'} {nom:<{largeur}}  Excel = {vx!s:<22} Python = {vp}")
    print(f"\n{len(ecarts) - nb_ko}/{len(ecarts)} contrôles conformes.")
    return 0 if nb_ko == 0 else 1


if __name__ == "__main__":
    sys.exit(verifier(sys.argv[1] if len(sys.argv) > 1 else "excel/BatCrue_etude_batardeau.xlsx"))
