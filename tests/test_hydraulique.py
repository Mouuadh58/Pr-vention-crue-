"""Tests du moteur hydraulique sur des cas analytiques ou de bon sens physique."""
import math

import numpy as np
import pytest

from batcrue.constantes import G
from batcrue.ouvrage import (SectionBarrage, debit_seuil, methode_aubuisson, methode_energie,
                             methode_seuil, methode_yarnell)
from batcrue.remous import ligne_eau_bresse_heun, ligne_eau_pas_standard, section_prismatique
from batcrue.sections import Section


# ----------------------------------------------------------------- sections
def test_hauteur_normale_rectangulaire_verifie_strickler():
    sec = Section(0.0, b=40.0, m=0.0, K_min=30.0)
    Q, I = 250.0, 3e-4
    y = sec.hauteur_normale(Q, I)
    A, P = 40 * y, 40 + 2 * y
    assert 30 * A * (A / P) ** (2 / 3) * math.sqrt(I) == pytest.approx(Q, rel=1e-8)


def test_hauteur_normale_canal_tres_large():
    sec = Section(0.0, b=5000.0, m=0.0, K_min=25.0)
    Q, I = 5000.0, 1e-4
    y = sec.hauteur_normale(Q, I)
    q = Q / 5000.0
    assert y == pytest.approx((q / (25 * math.sqrt(I))) ** 0.6, rel=2e-3)


def test_hauteur_critique_rectangulaire():
    sec = Section(0.0, b=20.0)
    Q = 150.0
    assert sec.hauteur_critique(Q) == pytest.approx((Q * Q / (G * 400)) ** (1 / 3), rel=1e-7)
    # Froude = 1 à la hauteur critique
    assert sec.froude(Q, sec.hauteur_critique(Q)) == pytest.approx(1.0, rel=1e-6)


def test_section_composee_continuite_et_coriolis():
    sec = Section(0.0, b=50, m=2, h_berge=6, B_maj=300, K_min=30, K_maj=15)
    a_moins = sec.aire(6.0 - 1e-9)
    a_plus = sec.aire(6.0 + 1e-9)
    assert a_plus == pytest.approx(a_moins, rel=1e-6)
    _, _, _, _, alpha = sec.proprietes(7.0)
    assert alpha > 1.0  # lit composé : répartition non uniforme des vitesses
    _, _, _, _, alpha_min = sec.proprietes(5.0)
    assert alpha_min == 1.0


# ----------------------------------------------------------------- remous
def test_remous_regime_uniforme_reste_uniforme():
    sec0 = Section(10.0, b=50, m=2, h_berge=8, B_maj=0, K_min=30)
    Q, I = 300.0, 2e-4
    yn = sec0.hauteur_normale(Q, I)
    le = ligne_eau_pas_standard(Q, 10.0 + yn, section_prismatique(sec0, I), 10000, 100, 0, 0)
    profondeurs = le.Z - le.z_fond
    assert np.max(np.abs(profondeurs - yn)) < 2e-3


def test_remous_m1_tend_vers_hauteur_normale():
    sec0 = Section(10.0, b=50, m=2, h_berge=20, B_maj=0, K_min=30)
    Q, I = 300.0, 5e-4
    yn = sec0.hauteur_normale(Q, I)
    le = ligne_eau_pas_standard(Q, 10.0 + yn + 1.0, section_prismatique(sec0, I), 30000, 100, 0, 0)
    y = le.Z - le.z_fond
    assert np.all(np.diff(y) < 1e-9)          # profondeur décroissante vers l'amont (courbe M1)
    assert y[-1] - yn < 0.02                  # retour quasi complet à la hauteur normale
    assert np.all(y > yn - 1e-6)


def test_pas_standard_et_bresse_concordent():
    sec0 = Section(20.0, b=50, m=2, h_berge=6, B_maj=300, K_min=30, K_maj=15)
    Q, I = 600.0, 2e-4
    z0 = 20.0 + sec0.hauteur_normale(Q, I) + 0.20
    a = ligne_eau_pas_standard(Q, z0, section_prismatique(sec0, I), 12000, 100, 0, 0)
    b = ligne_eau_bresse_heun(Q, z0, sec0, I, 12000, 100)
    # La variante de Bresse néglige le coefficient de Coriolis : écart de l'ordre du centimètre
    assert np.max(np.abs(a.Z - b.Z)) < 0.03


# ----------------------------------------------------------------- barrage
SEC = SectionBarrage(largeur=66.0, cote_fond=20.0)


def test_energie_sans_obstacle_pas_de_perte():
    sec = SectionBarrage(60.0, 20.0)
    r = methode_energie(500.0, [(60.0, 20.0)], sec, 26.0, 0.3)
    assert r.Z_amont == pytest.approx(26.0, abs=1e-6)


def test_energie_retrecissement_augmente_cote():
    r_libre = methode_energie(600.0, [(60.0, 20.0)], SEC, 26.5, 0.1)
    r_obst = methode_energie(600.0, [(40.0, 20.0)], SEC, 26.5, 0.6)
    assert r_obst.Z_amont > r_libre.Z_amont > 26.5
    assert "noyé" in r_obst.regime


def test_energie_denoye_retrouve_loi_de_seuil_theorique():
    """Seuil haut, aval bas : passage par la hauteur critique ⇒ μ = (2/3)^1.5/√2 ≈ 0,385."""
    sec = SectionBarrage(30.0, 0.0)
    Q = 50.0
    r = methode_energie(Q, [(30.0, 3.0)], sec, 1.0, 0.0)
    assert "dénoyé" in r.regime
    d = methode_seuil(Q, [(30.0, 3.0)], sec, 1.0, (2 / 3) ** 1.5 / math.sqrt(2), vitesse_approche=True)
    assert r.Z_amont == pytest.approx(d.Z_amont, abs=1e-6)


def test_energie_plusieurs_groupes_coherent_avec_un_groupe():
    z3 = 26.6
    un = methode_energie(650.0, [(40.0, 20.0)], SEC, z3, 0.6)
    deux = methode_energie(650.0, [(20.0, 20.0), (20.0, 20.0005)], SEC, z3, 0.6)
    assert deux.Z_amont == pytest.approx(un.Z_amont, abs=2e-3)


def test_seuils_differents_repartition_debits():
    r = methode_energie(400.0, [(20.0, 20.0), (20.0, 22.0)], SEC, 25.0, 0.3)
    q_bas, q_haut = r.details["debits_groupes"]
    assert q_bas > q_haut > 0
    assert q_bas + q_haut == pytest.approx(400.0, rel=1e-6)


def test_yarnell_valeur_calculee_a_la_main():
    Q, z3 = 700.0, 27.0
    r = methode_yarnell(Q, [(40.0, 20.0)], SEC, z3, 1.25)
    y3 = 7.0
    v3 = Q / (66 * y3)
    alpha = 1 - 40 / 66
    omega = v3 ** 2 / (2 * G * y3)
    attendu = 2 * 1.25 * (1.25 + 10 * omega - 0.6) * (alpha + 15 * alpha ** 4) * v3 ** 2 / (2 * G)
    assert r.Z_amont - z3 == pytest.approx(attendu, rel=1e-10)
    assert r.valide  # α ≈ 0,39 ≤ 0,5


def test_yarnell_hors_domaine_signale():
    r = methode_yarnell(500.0, [(20.0, 20.0)], SEC, 26.0, 1.25)
    assert not r.valide


def test_aubuisson_verifie_sa_formule():
    Q, z3, ka = 700.0, 27.0, 0.95
    r = methode_aubuisson(Q, [(40.0, 20.0)], SEC, z3, ka)
    dh = r.Z_amont - z3
    v1 = Q / (66 * (r.Z_amont - 20.0))
    assert Q == pytest.approx(ka * 40 * 7.0 * math.sqrt(2 * G * dh + v1 ** 2), rel=1e-7)


def test_loi_seuil_continuite_denoye_noye():
    h1, b, mu = 2.0, 10.0, 0.385
    q_den, r1 = debit_seuil(h1, 2 / 3 * h1 - 1e-9, b, mu)
    q_noy, r2 = debit_seuil(h1, 2 / 3 * h1 + 1e-9, b, mu)
    assert r1 == "dénoyé" and r2 == "noyé"
    assert q_den == pytest.approx(q_noy, rel=1e-6)


def test_methodes_coherentes_entre_elles():
    """Les 4 méthodes donnent le même ordre de grandeur de surélévation."""
    Q, z3 = 650.0, 26.9
    ref = [(60.0, 20.0)]
    bat = [(40.0, 20.0)]
    dz = {
        "A": methode_energie(Q, bat, SEC, z3, 0.6).Z_amont - methode_energie(Q, ref, SEC, z3, 0.1).Z_amont,
        "B": methode_yarnell(Q, bat, SEC, z3, 1.25).Z_amont - methode_yarnell(Q, ref, SEC, z3, 0.9).Z_amont,
        "C": methode_aubuisson(Q, bat, SEC, z3, 1.0).Z_amont - methode_aubuisson(Q, ref, SEC, z3, 1.0).Z_amont,
        "D": methode_seuil(Q, bat, SEC, z3, 0.385).Z_amont - methode_seuil(Q, ref, SEC, z3, 0.385).Z_amont,
    }
    valeurs = np.array(list(dz.values()))
    assert np.all(valeurs > 0.05) and np.all(valeurs < 0.40)
    assert valeurs.max() / valeurs.min() < 2.0
