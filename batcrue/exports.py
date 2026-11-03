"""Export des résultats vers un classeur Excel (valeurs calculées, sans formules)."""
from __future__ import annotations

import io

import pandas as pd

from .parametres import vers_json


def excel_resultats(etude, s: dict, courbe: pd.DataFrame, tableau: pd.DataFrame) -> bytes:
    p = etude.p
    synth = pd.DataFrame([
        ("Barrage", p["nom_barrage"]), ("Étude", p["nom_projet"]),
        ("Crue de référence", f"Q{int(p['T_reference'])} = {s['Q_reference']:.0f} m3/s"),
        ("Surélévation au barrage (m)", s["dZ_barrage"]), ("Surélévation max aux enjeux (m)", s["dZ_enjeux_max"]),
        ("Distance d'influence 1 cm (m)", s["distance_influence"]),
        ("Débit d'atteinte du seuil (m3/s)", s["Q_seuil"]), ("Période de retour (ans)", s["T_seuil"]),
        ("Probabilité pendant les travaux", s["P_seuil"]),
        ("Débit de submersion du batardeau (m3/s)", s["Q_submersion"]),
        ("Probabilité de submersion pendant les travaux", s["P_submersion"]),
        ("Débit d'effacement sans batardeau (m3/s)", s["Q_effacement_sans"]),
        ("Débit d'effacement avec batardeau (m3/s)", s["Q_effacement_avec"]),
        ("Vitesse dans les passes avec batardeau (m/s)", s["erosion"]["V_passes_avec"]),
        ("Pré-diagnostic", s["verdict"]),
    ], columns=["Indicateur", "Valeur"])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        synth.to_excel(xw, sheet_name="Synthèse", index=False)
        tableau.to_excel(xw, sheet_name="Périodes de retour", index=False)
        courbe.to_excel(xw, sheet_name="Courbe Q-ΔZ", index=False)
        s["ligne_eau"].to_excel(xw, sheet_name="Ligne d'eau Qref", index=False)
        if s["enjeux"] is not None and not s["enjeux"].empty:
            s["enjeux"].to_excel(xw, sheet_name="Enjeux", index=False)
        pd.DataFrame({"parametres_json": [vers_json(p)]}).to_excel(xw, sheet_name="Paramètres", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                largeur = max(len(str(c.value)) if c.value is not None else 0 for c in col[:60])
                ws.column_dimensions[col[0].column_letter].width = min(max(10, largeur + 2), 60)
    return buf.getvalue()
