"""Tests des sorties : rapport HTML, export Excel des résultats, génération du classeur à formules."""
import io
import re

import pytest
from openpyxl import load_workbook

from batcrue import EtudeBatardeau, defauts
from batcrue.exports import excel_resultats
from batcrue.rapport import generer_html


@pytest.fixture(scope="module")
def resultats():
    e = EtudeBatardeau(defauts())
    return e, e.synthese(), e.courbe(), e.tableau_periodes_retour()


def test_rapport_html_complet_et_theme(resultats):
    e, s, c, t = resultats
    h = generer_html(e, s, c, t)
    assert h.startswith("<!doctype html>") and '<meta charset="utf-8">' in h
    for titre in ("Synthèse", "Données d'entrée", "Méthodes", "Résultats", "Risque pendant les travaux"):
        assert titre in h
    assert h.count("<svg") == 3
    # Les couleurs des graphiques passent par des variables CSS (thème clair/sombre).
    svgs = re.findall(r"<svg.*?</svg>", h, flags=re.S)
    assert all(not re.search(r"#[0-9a-fA-F]{6}", x) for x in svgs)
    fragment = generer_html(e, s, c, t, document_complet=False)
    assert fragment.startswith("<title>") and "<html" not in fragment


def test_export_excel_resultats(resultats):
    e, s, c, t = resultats
    wb = load_workbook(io.BytesIO(excel_resultats(e, s, c, t)))
    assert {"Synthèse", "Périodes de retour", "Courbe Q-ΔZ", "Paramètres"} <= set(wb.sheetnames)


def test_generation_classeur_formules(tmp_path):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "excel"))
    from generer_classeur import generer
    chemin = generer(tmp_path / "classeur.xlsx")
    wb = load_workbook(chemin)
    assert {"Données", "Calculs", "Remous", "Risque", "Résultats", "Tarage"} <= set(wb.sheetnames)
    for nom in ("B_riv", "L_obstruee", "Gu", "Frac_alea", "Q_seuil", "Dist_influence"):
        assert nom in wb.defined_names
    calc = wb["Calculs"]
    formules = [cell.value for row in calc.iter_rows(min_row=5, max_row=10) for cell in row
                if isinstance(cell.value, str) and cell.value.startswith("=")]
    assert len(formules) > 300
