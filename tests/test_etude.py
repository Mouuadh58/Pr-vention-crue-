"""Tests de l'orchestrateur d'étude, de l'hydrologie, des paramètres et du client Hub'Eau."""
import math
from datetime import date

import numpy as np
import pytest

from batcrue import EtudeBatardeau, defauts, depuis_json, valider, vers_json
from batcrue.efforts import poussee_hydrostatique, verification_lane
from batcrue.erosion import diametre_isbash
from batcrue.hydrogramme import hydrogramme_synthetique, instants_franchissement, lire_hydrogramme_csv
from batcrue.hydrologie import (Gumbel, analyse_chronique, fraction_alea, proba_pendant_travaux)


@pytest.fixture(scope="module")
def etude():
    return EtudeBatardeau(defauts())


def test_parametres_par_defaut_valides():
    err, _ = valider(defauts())
    assert err == []


def test_sans_obstruction_impact_nul():
    p = defauts()
    for x in p["passes"]:
        x["obstruction"] = 0.0
    e = EtudeBatardeau(p)
    for T in (2, 10, 100):
        r = e.calcul_debit(e.debit_T(T))
        for m, dz in r.dZ.items():
            assert abs(dz) < 1e-9, (m, T, dz)


def test_regulation_impact_nul_en_basses_eaux(etude):
    r = etude.calcul_debit(150.0)
    assert r.regule_ref and r.regule_bat
    assert r.dZ_env == pytest.approx(0.0, abs=1e-12)
    assert r.Z_ref_base == pytest.approx(defauts()["rn_amont"])


def test_impact_croit_avec_le_debit_et_l_obstruction(etude):
    dz = [etude.calcul_debit(etude.debit_T(T)).dZ["A"] for T in (5, 10, 50, 100)]
    assert all(b > a for a, b in zip(dz, dz[1:]))
    q = etude.Q_reference
    d25 = etude.calcul_debit(q, 0.25 * etude.largeur_passes).dZ_env
    d50 = etude.calcul_debit(q, 0.50 * etude.largeur_passes).dZ_env
    assert d50 > d25 > 0


def test_effacement_plus_tot_avec_batardeau(etude):
    assert etude.debit_effacement(True) < etude.debit_effacement(False)


def test_remous_impact_decroit_vers_l_amont(etude):
    le = etude.ligne_eau(etude.Q_reference)
    assert le["dZ"].iloc[0] > 0.05
    assert np.all(np.diff(le["dZ"].to_numpy()) <= 1e-6)
    assert le["dZ"].iloc[-1] < le["dZ"].iloc[0]


def test_synthese_complete(etude):
    s = etude.synthese()
    assert s["niveau"] in {"ok", "attention", "non_conforme"}
    assert 0 < s["dZ_barrage"] < 0.5
    assert s["Q_seuil"] is not None and s["Q_seuil"] < s["Q_reference"]
    assert 0 <= s["P_seuil"] <= 1
    assert s["fraction_alea"] == pytest.approx(184 / 365, rel=0.02)


def test_mode_tableau_proche_du_mode_prismatique():
    p = defauts()
    p["mode_aval"] = "tableau"
    p["mode_bief"] = "tableau"
    p["sections_tabulees"] = [
        {"x": 0, "z_fond": 20.0, "b": 50, "m": 2, "h_berge": 6, "B_maj": 300, "K_min": 30, "K_maj": 15},
        {"x": 12000, "z_fond": 22.4, "b": 50, "m": 2, "h_berge": 6, "B_maj": 300, "K_min": 30, "K_maj": 15},
    ]
    e_tab, e_pri = EtudeBatardeau(p), EtudeBatardeau(defauts())
    q = e_pri.Q_reference
    assert e_tab.calcul_debit(q).dZ_env == pytest.approx(e_pri.calcul_debit(q).dZ_env, abs=0.01)
    l_tab, l_pri = e_tab.ligne_eau(q), e_pri.ligne_eau(q)
    assert np.max(np.abs(l_tab["dZ"].to_numpy() - l_pri["dZ"].to_numpy())) < 0.01


def test_tableau_periodes_retour(etude):
    df = etude.tableau_periodes_retour()
    assert {"Q2", "Q10", "Q100"} <= set(df["evenement"])
    assert (df["P_travaux"].between(0, 1)).all()


def test_sensibilite_et_monte_carlo(etude):
    s = etude.sensibilite()
    assert len(s) >= 8 and s["ecart_max"].ge(0).all()
    mc = etude.monte_carlo(n=40, graine=3)
    assert len(mc["tirages"]) == 40
    assert mc["p50"] <= mc["p95"] <= mc["max"]


def test_hydrogramme_et_alertes(etude):
    sim = etude.simulation_hydrogramme()
    assert sim["Q"].max() == pytest.approx(etude.debit_T(defauts()["hydro_T"]), rel=1e-3)
    assert sim["dZ_max"] > 0


def test_variantes_largeur(etude):
    v = etude.variantes_largeur((0.25, 0.5))
    assert v[0.5]["dZ_enveloppe"].max() > v[0.25]["dZ_enveloppe"].max()


# ----------------------------------------------------------------- hydrologie
def test_gumbel_quantile_et_periode_retour():
    g = Gumbel(283.0, 88.0)
    for T in (2, 10, 100, 1000):
        assert g.periode_retour(g.quantile(T)) == pytest.approx(T, rel=1e-9)


def test_gumbel_ajustement_quantiles():
    g = Gumbel(300.0, 90.0)
    Ts = [2, 5, 10, 20, 50, 100]
    g2 = Gumbel.par_quantiles(Ts, [g.quantile(T) for T in Ts])
    assert g2.u == pytest.approx(300.0, rel=1e-9) and g2.beta == pytest.approx(90.0, rel=1e-9)


def test_gumbel_moments_sur_echantillon():
    rng = np.random.default_rng(0)
    x = rng.gumbel(300.0, 90.0, 20000)
    g = Gumbel.par_moments(x)
    assert g.u == pytest.approx(300.0, rel=0.02) and g.beta == pytest.approx(90.0, rel=0.03)


def test_fraction_alea_et_proba():
    assert fraction_alea(date(2027, 1, 1), date(2027, 12, 31)) == pytest.approx(1.0)
    g = Gumbel(283.0, 88.0)
    q100 = g.quantile(100)
    assert proba_pendant_travaux(g, q100, 1.0) == pytest.approx(0.01, rel=1e-9)
    poids_hiver = [3, 3, 2, 1, 0, 0, 0, 0, 0, 1, 2, 3]
    assert fraction_alea(date(2027, 6, 1), date(2027, 8, 31), poids_hiver) == pytest.approx(0.0)


def test_analyse_chronique():
    import pandas as pd
    jours = pd.date_range("2000-01-01", "2009-12-31", freq="D")
    q = 100 + 400 * np.exp(-((jours.dayofyear - 30) / 20.0) ** 2)
    a = analyse_chronique(jours, q, (5, 1), (10, 31))
    assert len(a["maxima_annuels"]) == 10
    assert max(a["maxima_fenetre"].values()) < 110
    assert np.argmax(a["poids_mensuels"]) in (0, 1)


# ----------------------------------------------------------------- divers
def test_json_aller_retour():
    p = defauts()
    p2 = depuis_json(vers_json(p))
    assert p2["passes"] == p["passes"]
    assert math.isnan(p2["enjeux"][2]["cote_dommages"])


def test_isbash_et_efforts():
    assert diametre_isbash(3.0, 2650, 0.86) == pytest.approx(9 / (2 * 9.81 * 1.65 * 0.86 ** 2))
    assert poussee_hydrostatique(5.0) == pytest.approx(0.5 * 1000 * 9.81 * 25)
    v = verification_lane(3.0, 12.0, 3.0, "Sable moyen")
    assert v["L_w"] == pytest.approx(13.0) and not v["ok"]


def test_hydrogramme_synthetique_pic():
    t, q = hydrogramme_synthetique(500, 100, 48, 240, 1)
    assert q[48] == pytest.approx(500.0)
    assert q.argmax() == 48
    assert instants_franchissement(t, q, 300) < 48


def test_lecture_csv_hydrogramme():
    t, q = lire_hydrogramme_csv("date;debit\n01/02/2021 00:00;120,5\n01/02/2021 06:00;180\n01/02/2021 12:00;240\n")
    assert list(t) == [0.0, 6.0, 12.0] and q[0] == pytest.approx(120.5)


# ----------------------------------------------------------------- Hub'Eau (simulé)
class _Rep:
    def __init__(self, js, code=200):
        self._js, self.status_code, self.text = js, code, str(js)

    def json(self):
        return self._js


class _Session:
    def __init__(self, reponses):
        self.reponses, self.appels = reponses, []

    def get(self, url, params=None, timeout=None):
        self.appels.append((url, params))
        return self.reponses.pop(0)


def test_hubeau_debit_actuel_conversion_l_s():
    from batcrue import hubeau
    s = _Session([_Rep({"data": [{"date_obs": "2026-11-03T06:00:00Z", "resultat_obs": 254300.0},
                                 {"date_obs": "2026-11-03T05:00:00Z", "resultat_obs": 250000.0}],
                        "next": None})])
    quand, q = hubeau.debit_actuel("H0000000", session=s)
    assert q == pytest.approx(254.3) and quand.hour == 6
    assert s.appels[0][1]["grandeur_hydro"] == "Q"


def test_hubeau_journaliers_pagination():
    from batcrue import hubeau
    s = _Session([
        _Rep({"data": [{"date_obs_elab": "2020-01-02", "resultat_obs_elab": 2000.0}], "next": "page2"}),
        _Rep({"data": [{"date_obs_elab": "2020-01-01", "resultat_obs_elab": 1000.0}], "next": None}),
    ])
    d, q = hubeau.debits_journaliers("H0000000", date(2020, 1, 1), date(2020, 1, 2), session=s)
    assert d == [date(2020, 1, 1), date(2020, 1, 2)] and q == [1.0, 2.0]


def test_hubeau_erreur_http():
    from batcrue import hubeau
    s = _Session([_Rep({"message": "bad"}, code=400)])
    with pytest.raises(hubeau.HubEauErreur):
        hubeau.debit_actuel("XXX", session=s)
