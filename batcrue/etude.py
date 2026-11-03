"""Orchestration de l'étude d'impact hydraulique d'un batardeau.

Principe (régime permanent, crue de pointe) :

1. Cote aval Z3(Q) : hauteur normale de Strickler (ou loi tabulée, ou cote
   imposée), bornée inférieurement par la retenue normale du bief aval.
2. Cote amont en écoulement libre (vannes ouvertes) Z1(Q), sans puis avec
   batardeau, par 4 méthodes (énergie/Borda, Yarnell, d'Aubuisson, seuils).
3. Régulation : tant qu'il le peut, le barrage maintient la retenue normale
   RN ; la cote amont réelle est max(RN, Z1). L'impact vaut
       ΔZ(Q) = Zamont,avec(Q) - Zamont,sans(Q)
4. Propagation vers l'amont : courbes de remous avec et sans batardeau
   (méthode des pas standards) ; ΔZ(x) aux enjeux.
5. Hydrologie : périodes de retour (Gumbel) et probabilité d'occurrence
   pendant la période d'installation du batardeau.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from . import efforts as eff
from . import erosion as ero
from .hydrogramme import hydrogramme_synthetique, instants_franchissement
from .hydrologie import (PERIODES_RETOUR, Gumbel, fraction_alea, proba_pendant_travaux)
from .ouvrage import (METHODES, SectionBarrage, methode_aubuisson, methode_energie, methode_seuil,
                      methode_yarnell)
from .parametres import appliquer_formes, completer
from .remous import ligne_eau_pas_standard, section_interpolee, section_prismatique
from .sections import Section


@dataclass
class ResultatDebit:
    """Résultats au droit du barrage pour un débit donné."""

    Q: float
    Z3: float
    V3: float
    ref: dict            # méthode -> ResultatMethode (sans batardeau, écoulement libre)
    bat: dict            # méthode -> ResultatMethode (avec batardeau, écoulement libre)
    Z_ref: dict          # méthode -> cote amont réelle sans batardeau (régulation comprise)
    Z_bat: dict          # méthode -> cote amont réelle avec batardeau
    dZ: dict             # méthode -> surélévation [m]
    valide: dict         # méthode -> bool
    methode_base: str
    dZ_env: float = math.nan
    methode_env: str = ""
    Z_ref_base: float = math.nan
    Z_bat_env: float = math.nan
    regule_ref: bool = False
    regule_bat: bool = False

    def ligne(self) -> dict:
        d = {"Q": self.Q, "Z_aval": self.Z3, "V_aval": self.V3,
             "Z_amont_sans": self.Z_ref_base, "Z_amont_avec": self.Z_bat_env,
             "dZ_enveloppe": self.dZ_env, "methode_enveloppe": self.methode_env,
             "regule_sans": self.regule_ref, "regule_avec": self.regule_bat}
        for m in METHODES:
            d[f"dZ_{m}"] = self.dZ.get(m, math.nan)
            d[f"Z_sans_{m}"] = self.Z_ref.get(m, math.nan)
            d[f"Z_avec_{m}"] = self.Z_bat.get(m, math.nan)
            d[f"valide_{m}"] = self.valide.get(m, False)
        a_ref, a_bat = self.ref.get("A"), self.bat.get("A")
        d["V_passes_sans"] = a_ref.V_passes if a_ref else math.nan
        d["V_passes_avec"] = a_bat.V_passes if a_bat else math.nan
        d["regime_sans"] = a_ref.regime if a_ref else ""
        d["regime_avec"] = a_bat.regime if a_bat else ""
        return d


class EtudeBatardeau:
    """Point d'entrée du moteur de calcul : ``EtudeBatardeau(params)``."""

    def __init__(self, params: dict | None = None):
        p = appliquer_formes(completer(params))
        self.p = p
        self.sec_barrage = SectionBarrage(float(p["largeur_riviere"]), float(p["cote_fond"]))
        self.passes = [dict(nom=str(x.get("nom", f"Passe {i + 1}")), largeur=float(x["largeur"]),
                            cote_seuil=float(x["cote_seuil"]),
                            obstruction=min(max(float(x.get("obstruction", 0) or 0), 0.0), 1.0))
                       for i, x in enumerate(p["passes"])]
        self.section_ref = Section(float(p["cote_fond"]), float(p["b_min"]), float(p["m_berge"]),
                                   float(p["h_berge"]), float(p["B_maj"]), float(p["K_min"]),
                                   float(p["K_maj"]))
        if p["mode_bief"] == "tableau":
            self.section_en = section_interpolee(p["sections_tabulees"])
        else:
            self.section_en = section_prismatique(self.section_ref, float(p["pente"]))
        if p["mode_hydro"] == "quantiles":
            q = [r for r in p["quantiles"] if r.get("T") and r.get("Q")]
            self.gumbel = Gumbel.par_quantiles([float(r["T"]) for r in q], [float(r["Q"]) for r in q])
        else:
            self.gumbel = Gumbel(float(p["gumbel_u"]), float(p["gumbel_beta"]))
        self.methodes = [m for m in METHODES if m in p["methodes_actives"]] or ["A"]
        self.methode_base = "A" if "A" in self.methodes else self.methodes[0]
        self._cache_aval: dict[float, float] = {}
        self._cache_debit: dict[tuple, ResultatDebit] = {}

    # ================================================================ géométrie
    @property
    def largeur_passes(self) -> float:
        return sum(x["largeur"] for x in self.passes)

    @property
    def largeur_obstruee(self) -> float:
        return sum(x["largeur"] * x["obstruction"] for x in self.passes)

    @property
    def taux_obstruction(self) -> float:
        """Part de la largeur d'écoulement des passes occupée par le batardeau."""
        return self.largeur_obstruee / self.largeur_passes if self.largeur_passes > 0 else 0.0

    def ouvertures(self, avec_batardeau: bool, largeur_obstruee: float | None = None):
        """Liste des (largeur libre, cote de seuil) des passes."""
        if not avec_batardeau:
            return [(x["largeur"], x["cote_seuil"]) for x in self.passes]
        if largeur_obstruee is None:
            return [(x["largeur"] * (1.0 - x["obstruction"]), x["cote_seuil"]) for x in self.passes]
        reste = max(0.0, float(largeur_obstruee))
        bloque = [0.0] * len(self.passes)
        ordre = sorted(range(len(self.passes)), key=lambda i: (self.passes[i]["obstruction"] <= 0, i))
        for i in ordre:
            prise = min(reste, self.passes[i]["largeur"])
            bloque[i] = prise
            reste -= prise
        return [(x["largeur"] - bloque[i], x["cote_seuil"]) for i, x in enumerate(self.passes)]

    # ================================================================ aval
    def cote_aval(self, Q: float) -> float:
        cle = round(Q, 6)
        if cle in self._cache_aval:
            return self._cache_aval[cle]
        p = self.p
        mode = p["mode_aval"]
        if mode == "constante":
            z = float(p["cote_aval_constante"])
        elif mode == "tableau":
            pts = sorted(((float(r["Q"]), float(r["Z"])) for r in p["loi_aval"]), key=lambda t: t[0])
            qs = np.array([a for a, _ in pts])
            zs = np.array([b for _, b in pts])
            if Q <= qs[0]:
                z = float(zs[0])
            elif Q >= qs[-1]:  # extrapolation linéaire sur les deux derniers points
                z = float(zs[-1] + (zs[-1] - zs[-2]) * (Q - qs[-1]) / (qs[-1] - qs[-2]))
            else:
                z = float(np.interp(Q, qs, zs))
        else:
            z = self.section_ref.z_fond + self.section_ref.hauteur_normale(Q, float(p["pente"]))
            if p["regulation"] and p["rn_aval"] is not None and math.isfinite(float(p["rn_aval"])):
                z = max(z, float(p["rn_aval"]))
        z += float(p["decalage_aval"])
        z = max(z, self.sec_barrage.cote_fond + 0.05)
        self._cache_aval[cle] = z
        return z

    # ================================================================ barrage
    def niveaux_libres(self, Q: float, avec_batardeau: bool, largeur_obstruee: float | None = None,
                       Z3: float | None = None) -> dict:
        """Cotes amont en écoulement libre (vannes ouvertes) pour chaque méthode active."""
        p = self.p
        z3 = self.cote_aval(Q) if Z3 is None else Z3
        ouv = self.ouvertures(avec_batardeau, largeur_obstruee)
        if avec_batardeau:
            xi = self._coef_effectif(ouv, float(p["xi_ref"]), float(p["xi_bat"]))
            K = self._coef_effectif(ouv, float(p["K_yarnell_ref"]), float(p["K_yarnell_bat"]))
        else:
            xi, K = float(p["xi_ref"]), float(p["K_yarnell_ref"])
        res = {}
        for m in self.methodes:
            if m == "A":
                res[m] = methode_energie(Q, ouv, self.sec_barrage, z3, xi)
            elif m == "B":
                res[m] = methode_yarnell(Q, ouv, self.sec_barrage, z3, K)
            elif m == "C":
                res[m] = methode_aubuisson(Q, ouv, self.sec_barrage, z3, float(p["K_A"]))
            elif m == "D":
                res[m] = methode_seuil(Q, ouv, self.sec_barrage, z3, float(p["mu"]),
                                       bool(p["vitesse_approche_seuil"]))
        return res

    def _coef_effectif(self, ouv, coef_piles: float, coef_batardeau: float) -> float:
        """Coefficient (ξ ou K de Yarnell) pondéré par les largeurs obstruées : piles / batardeau."""
        larg_bat = self.largeur_passes - sum(b for b, _ in ouv)
        larg_piles = max(self.sec_barrage.largeur - self.largeur_passes, 0.0)
        total = larg_bat + larg_piles
        if total <= 0 or larg_bat <= 1e-9:
            return coef_piles
        return (larg_piles * coef_piles + larg_bat * coef_batardeau) / total

    def calcul_debit(self, Q: float, largeur_obstruee: float | None = None) -> ResultatDebit:
        cle = (round(Q, 6), None if largeur_obstruee is None else round(largeur_obstruee, 6))
        if cle in self._cache_debit:
            return self._cache_debit[cle]
        p = self.p
        z3 = self.cote_aval(Q)
        v3 = self.sec_barrage.vitesse(Q, z3)
        ref = self.niveaux_libres(Q, False, None, z3)
        bat = self.niveaux_libres(Q, True, largeur_obstruee, z3)
        rn = float(p["rn_amont"]) if p["regulation"] else -math.inf
        z_ref, z_bat, dz, valide = {}, {}, {}, {}
        a_bat = bat.get("A")
        for m in self.methodes:
            zr, zb = ref[m].Z_amont, bat[m].Z_amont
            z_ref[m] = max(rn, zr) if math.isfinite(zr) else math.nan
            z_bat[m] = max(rn, zb) if math.isfinite(zb) else math.nan
            dz[m] = z_bat[m] - z_ref[m] if (math.isfinite(z_ref[m]) and math.isfinite(z_bat[m])) else math.nan
            ok = ref[m].valide and bat[m].valide and math.isfinite(dz[m])
            if m == "B" and a_bat is not None and "dénoyé" in a_bat.regime:
                ok = False
                bat[m].remarque = "Écoulement étranglé (dénoyé) : Yarnell non applicable."
            valide[m] = ok
        r = ResultatDebit(Q, z3, v3, ref, bat, z_ref, z_bat, dz, valide, self.methode_base)
        candidats = [(dz[m], m) for m in self.methodes if valide[m]]
        if not candidats:
            candidats = [(dz[m], m) for m in self.methodes if math.isfinite(dz[m])]
        if candidats:
            r.dZ_env, r.methode_env = max(candidats)
        r.Z_ref_base = z_ref[self.methode_base]
        r.Z_bat_env = r.Z_ref_base + r.dZ_env
        r.regule_ref = p["regulation"] and ref[self.methode_base].Z_amont <= rn
        r.regule_bat = p["regulation"] and bat[self.methode_base].Z_amont <= rn
        self._cache_debit[cle] = r
        return r

    def dz_methode(self, r: ResultatDebit, methode: str) -> float:
        return r.dZ_env if methode == "enveloppe" else r.dZ.get(methode, math.nan)

    # ================================================================ débits
    def debit_T(self, T: float) -> float:
        return self.gumbel.quantile(T)

    @property
    def Q_reference(self) -> float:
        return self.debit_T(float(self.p["T_reference"]))

    @property
    def Q_chantier(self) -> float:
        return self.debit_T(float(self.p["T_chantier"]))

    def grille_debits(self, n: int = 60) -> np.ndarray:
        q_max = 1.15 * max(self.debit_T(100), self.Q_reference,
                           max([float(c["Q"]) for c in self.p["crues_historiques"] if c.get("Q")] or [0]))
        q_min = max(1.0, 0.3 * float(self.p["module"]))
        base = np.linspace(q_min, q_max, n)
        extras = [self.debit_T(T) for T in PERIODES_RETOUR] + [self.Q_reference, self.Q_chantier]
        return np.unique(np.concatenate([base, np.array(extras)]))

    def courbe(self, debits=None, largeur_obstruee: float | None = None) -> pd.DataFrame:
        debits = self.grille_debits() if debits is None else debits
        return pd.DataFrame([self.calcul_debit(float(q), largeur_obstruee).ligne() for q in debits])

    def debit_effacement(self, avec_batardeau: bool) -> float:
        """Débit au-delà duquel le barrage ne peut plus tenir la retenue normale (vannes ouvertes)."""
        if not self.p["regulation"]:
            return math.nan
        rn = float(self.p["rn_amont"])
        m = self.methode_base

        def f(q):
            return self.niveaux_libres(q, avec_batardeau)[m].Z_amont - rn

        q_lo, q_hi = 1.0, 3.0 * self.debit_T(100)
        if f(q_lo) >= 0:
            return q_lo
        if f(q_hi) < 0:
            return math.nan
        return brentq(f, q_lo, q_hi, xtol=0.01)

    def _premier_franchissement(self, valeurs_fn, seuil: float, debits=None):
        debits = self.grille_debits(120) if debits is None else debits
        prec_q, prec_v = None, None
        for q in debits:
            v = valeurs_fn(self.calcul_debit(float(q)))
            if math.isfinite(v) and v >= seuil:
                if prec_q is None:
                    return float(q)
                return float(prec_q + (seuil - prec_v) / (v - prec_v) * (q - prec_q))
            prec_q, prec_v = q, v
        return None

    def debit_seuil_impact(self, methode: str = "enveloppe"):
        """Plus petit débit pour lequel ΔZ au barrage atteint le seuil admissible."""
        return self._premier_franchissement(lambda r: self.dz_methode(r, methode), float(self.p["seuil_dz"]))

    def debit_submersion(self, avec_revanche: bool = False):
        """Débit pour lequel la cote amont atteint la crête (ou crête - revanche)."""
        cote = float(self.p["cote_arase"]) - (float(self.p["revanche"]) if avec_revanche else 0.0)
        return self._premier_franchissement(lambda r: r.Z_bat_env, cote)

    # ================================================================ remous
    def ligne_eau(self, Q: float, methode: str | None = None, largeur_obstruee: float | None = None) -> pd.DataFrame:
        methode = methode or self.p["methode_ligne_eau"]
        r = self.calcul_debit(Q, largeur_obstruee)
        z0_ref = r.Z_ref_base
        dz0 = self.dz_methode(r, methode)
        z0_bat = z0_ref + (dz0 if math.isfinite(dz0) else 0.0)
        L, dx = float(self.p["longueur_bief"]), float(self.p["pas_calcul"])
        prism = self.p["mode_bief"] != "tableau"
        cc, ce = (0.0, 0.0) if prism else (0.1, 0.3)
        le_ref = ligne_eau_pas_standard(Q, z0_ref, self.section_en, L, dx, cc, ce)
        le_bat = ligne_eau_pas_standard(Q, z0_bat, self.section_en, L, dx, cc, ce)
        df = pd.DataFrame({"x": le_ref.x, "z_fond": le_ref.z_fond, "z_berge": le_ref.z_berge,
                           "Z_sans": le_ref.Z, "Z_avec": le_bat.Z, "V_sans": le_ref.V, "V_avec": le_bat.V,
                           "Fr_sans": le_ref.Fr, "Fr_avec": le_bat.Fr,
                           "critique": le_ref.critique | le_bat.critique})
        df["dZ"] = df["Z_avec"] - df["Z_sans"]
        if prism:
            try:
                yn = self.section_ref.hauteur_normale(Q, float(self.p["pente"]))
                df["Z_normale"] = df["z_fond"] + yn
            except ValueError:
                df["Z_normale"] = math.nan
        return df

    @staticmethod
    def distance_influence(df: pd.DataFrame, seuil: float = 0.01) -> float:
        """Distance vers l'amont au-delà de laquelle ΔZ < seuil [m]."""
        au_dessus = df.index[df["dZ"] >= seuil]
        if len(au_dessus) == 0:
            return 0.0
        i = au_dessus.max()
        if i >= len(df) - 1:
            return float(df["x"].iloc[-1])
        x0, x1 = df["x"].iloc[i], df["x"].iloc[i + 1]
        d0, d1 = df["dZ"].iloc[i], df["dZ"].iloc[i + 1]
        return float(x0 + (d0 - seuil) / (d0 - d1) * (x1 - x0)) if d0 != d1 else float(x0)

    def impacts_enjeux(self, df: pd.DataFrame) -> pd.DataFrame:
        lignes = []
        for e in self.p["enjeux"]:
            try:
                x = float(e.get("x"))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(x):
                continue
            x = min(max(x, 0.0), float(df["x"].iloc[-1]))
            zs = float(np.interp(x, df["x"], df["Z_sans"]))
            za = float(np.interp(x, df["x"], df["Z_avec"]))
            cd = e.get("cote_dommages")
            try:
                cd = float(cd)
            except (TypeError, ValueError):
                cd = math.nan
            lignes.append({"enjeu": e.get("nom", ""), "x": x, "Z_sans": zs, "Z_avec": za, "dZ": za - zs,
                           "cote_dommages": cd,
                           "inonde_sans": bool(math.isfinite(cd) and zs > cd),
                           "inonde_avec": bool(math.isfinite(cd) and za > cd)})
        return pd.DataFrame(lignes)

    # ================================================================ risque
    @property
    def dates_travaux(self) -> tuple[date, date]:
        return date.fromisoformat(str(self.p["debut_travaux"])), date.fromisoformat(str(self.p["fin_travaux"]))

    @property
    def fraction_alea(self) -> float:
        d0, d1 = self.dates_travaux
        poids = None if self.p["saisonnalite"] == "uniforme" else self.p["poids_mensuels"]
        return fraction_alea(d0, d1, poids)

    def proba_travaux(self, Q) -> float:
        if Q is None or not math.isfinite(Q):
            return 0.0
        return proba_pendant_travaux(self.gumbel, Q, self.fraction_alea)

    def periode_retour(self, Q) -> float:
        if Q is None or not math.isfinite(Q):
            return math.inf
        return self.gumbel.periode_retour(Q)

    def tableau_periodes_retour(self) -> pd.DataFrame:
        lignes = []
        Ts = sorted(set(PERIODES_RETOUR + [int(self.p["T_chantier"]), int(self.p["T_reference"])]))
        for T in Ts:
            q = self.debit_T(T)
            d = self.calcul_debit(q).ligne()
            d.update({"evenement": f"Q{T}", "T": float(T), "P_travaux": self.proba_travaux(q)})
            lignes.append(d)
        for c in self.p["crues_historiques"]:
            try:
                q = float(c["Q"])
            except (TypeError, ValueError, KeyError):
                continue
            d = self.calcul_debit(q).ligne()
            d.update({"evenement": str(c.get("nom", "Crue historique")), "T": self.periode_retour(q),
                      "P_travaux": self.proba_travaux(q)})
            lignes.append(d)
        df = pd.DataFrame(lignes)
        cols = ["evenement", "T", "Q", "P_travaux"] + [c for c in df.columns if c not in ("evenement", "T", "Q", "P_travaux")]
        return df[cols]

    # ================================================================ érosion / efforts
    def erosion(self, Q: float) -> dict:
        p = self.p
        r = self.calcul_debit(Q)
        a = r.bat.get("A") or next(iter(r.bat.values()))
        v2 = a.V_passes if math.isfinite(a.V_passes) else r.Q / max(1e-6, sum(
            b * max(r.Z3 - zs, 0) for b, zs in self.ouvertures(True)))
        v_loc = float(p["k_vitesse_locale"]) * v2
        d = ero.diametre_isbash(v_loc, float(p["rho_enrochement"]), float(p["C_isbash"]))
        y1 = r.Z3 - self.sec_barrage.cote_fond
        w2 = sum(b for b, _ in self.ouvertures(True))
        w1 = sum(b for b, _ in self.ouvertures(False))
        aff = ero.affouillement_contraction(y1, w1, w2, float(p["k1_laursen"])) if p["fond_affouillable"] else math.nan
        v2_ref = (r.ref.get("A") or next(iter(r.ref.values()))).V_passes
        return {"V_passes_sans": v2_ref, "V_passes_avec": v2, "V_locale": v_loc, "D_isbash": d,
                "M_bloc": ero.masse_bloc(d, float(p["rho_enrochement"])), "affouillement": aff,
                "depasse": v_loc > float(p["vitesse_admissible"])}

    def efforts(self, Q: float) -> dict:
        p = self.p
        r = self.calcul_debit(Q)
        z_int = float(p["cote_fond_enceinte"])
        z_ext = min(r.Z_bat_env, float(p["cote_arase"]))
        h = z_ext - z_int
        v1 = (r.bat.get("A") or next(iter(r.bat.values()))).V_amont
        lane = None
        if p.get("lane_applicable"):
            lane = eff.verification_lane(h, float(p["l_cheminement_v"]), float(p["l_cheminement_h"]),
                                         p["sol_fondation"])
        return {"Z_ext": z_ext, "submerge": r.Z_bat_env > float(p["cote_arase"]), "h": h,
                "F_hydro": eff.poussee_hydrostatique(h), "M_hydro": eff.moment_hydrostatique(h),
                "F_dyn": eff.effort_dynamique(v1, h), "V_amont": v1, "lane": lane}

    # ================================================================ hydrogramme
    def simulation_hydrogramme(self, t=None, q=None) -> dict:
        p = self.p
        if t is None or q is None:
            if p["hydro_mode"] == "csv" and p.get("hydro_csv"):
                arr = np.asarray(p["hydro_csv"], dtype=float)
                t, q = arr[:, 0], arr[:, 1]
            else:
                qp = self.debit_T(float(p["hydro_T"]))
                t, q = hydrogramme_synthetique(qp, float(p["hydro_Qb"]), float(p["hydro_t_pic"]),
                                               float(p["hydro_duree"]))
        t = np.asarray(t, dtype=float)
        q = np.asarray(q, dtype=float)
        grille = np.linspace(max(1.0, float(np.nanmin(q))), max(float(np.nanmax(q)) * 1.001, 2.0), 80)
        c = self.courbe(grille)
        z_sans = np.interp(q, c["Q"], c["Z_amont_sans"])
        z_avec = np.interp(q, c["Q"], c["Z_amont_avec"])
        dz = z_avec - z_sans
        crete = float(p["cote_arase"])
        alerte = crete - float(p["revanche"])
        t_alerte = instants_franchissement(t, z_avec, alerte)
        t_sub = instants_franchissement(t, z_avec, crete)
        t_seuil = instants_franchissement(t, dz, float(p["seuil_dz"]))
        return {"t": t, "Q": q, "Z_sans": z_sans, "Z_avec": z_avec, "dZ": dz,
                "t_alerte": t_alerte, "t_submersion": t_sub, "t_seuil": t_seuil,
                "delai_alerte_submersion": (t_sub - t_alerte) if (t_sub is not None and t_alerte is not None) else None,
                "dZ_max": float(np.nanmax(dz)), "Z_max": float(np.nanmax(z_avec))}

    # ================================================================ variantes
    def variantes_largeur(self, fractions=(0.25, 1 / 3, 0.5), debits=None) -> dict:
        debits = self.grille_debits(40) if debits is None else debits
        out = {}
        for f in fractions:
            larg = f * self.largeur_passes
            out[f] = self.courbe(debits, larg)
        return out

    # ================================================================ sensibilité
    def _variante(self, **modifs) -> "EtudeBatardeau":
        p = dict(self.p)
        p.update(modifs)
        return EtudeBatardeau(p)

    def sensibilite(self, Q: float | None = None, methode: str = "enveloppe") -> pd.DataFrame:
        """Analyse « un paramètre à la fois » de ΔZ au barrage."""
        Q = self.Q_reference if Q is None else Q
        p = self.p
        base = self.dz_methode(self.calcul_debit(Q), methode)
        ks, kq, za = float(p["incert_strickler"]), float(p["incert_debit"]), float(p["incert_aval"])
        passes_m = [dict(x, obstruction=min(1.0, x["obstruction"] * 0.9)) for x in self.passes]
        cas = [
            ("Strickler lit mineur ±%d %%" % round(ks * 100),
             {"K_min": p["K_min"] * (1 - ks)}, {"K_min": p["K_min"] * (1 + ks)}, None),
            ("Strickler lit majeur ±%d %%" % round(ks * 100),
             {"K_maj": p["K_maj"] * (1 - ks)}, {"K_maj": p["K_maj"] * (1 + ks)}, None),
            ("Débit ±%d %%" % round(kq * 100), {}, {}, (Q * (1 - kq), Q * (1 + kq))),
            (("Cote aval ±%.2f m" % za).replace(".", ","), {"decalage_aval": p["decalage_aval"] - za},
             {"decalage_aval": p["decalage_aval"] + za}, None),
            ("Pente ±30 %", {"pente": p["pente"] * 0.7}, {"pente": p["pente"] * 1.3}, None),
            ("Contraction ξ batardeau 0,3 – 0,8", {"coefs_personnalises": True, "xi_bat": 0.3},
             {"coefs_personnalises": True, "xi_bat": 0.8}, None),
            ("K_A d'Aubuisson 1,07 – 0,87", {"K_A": 1.07}, {"K_A": 0.87}, None),
            ("μ seuil 0,40 – 0,35", {"mu": 0.40}, {"mu": 0.35}, None),
            ("K Yarnell batardeau 1,05 – 1,40", {"coefs_personnalises": True, "K_yarnell_bat": 1.05},
             {"coefs_personnalises": True, "K_yarnell_bat": 1.40}, None),
            ("Largeur obstruée -10 %", {"passes": passes_m}, {}, None),
        ]
        lignes = []
        for libelle, bas, haut, debits in cas:
            vals = []
            for modif, q in ((bas, None if debits is None else debits[0]),
                             (haut, None if debits is None else debits[1])):
                if not modif and q is None:
                    vals.append(base)
                    continue
                if modif.get("coefs_personnalises"):
                    modif = {"xi_ref": p["xi_ref"], "xi_bat": p["xi_bat"], "K_yarnell_ref": p["K_yarnell_ref"],
                             "K_yarnell_bat": p["K_yarnell_bat"], **modif}
                et = self._variante(**modif) if modif else self
                vals.append(et.dz_methode(et.calcul_debit(q if q is not None else Q), methode))
            lignes.append({"parametre": libelle, "dZ_bas": vals[0], "dZ_haut": vals[1],
                           "ecart_max": max(abs(vals[0] - base), abs(vals[1] - base))})
        df = pd.DataFrame(lignes).sort_values("ecart_max", ascending=True)
        df.attrs["base"] = base
        return df

    def monte_carlo(self, Q: float | None = None, n: int | None = None, graine: int | None = None,
                    methode: str = "enveloppe") -> dict:
        """Propagation d'incertitudes (tirages uniformes) sur ΔZ au barrage."""
        p = self.p
        Q = self.Q_reference if Q is None else Q
        n = int(p["mc_n"]) if n is None else n
        rng = np.random.default_rng(int(p["mc_graine"]) if graine is None else graine)
        ks, kq, za = float(p["incert_strickler"]), float(p["incert_debit"]), float(p["incert_aval"])
        res = np.empty(n)
        for i in range(n):
            modif = {
                "K_min": p["K_min"] * rng.uniform(1 - ks, 1 + ks),
                "K_maj": p["K_maj"] * rng.uniform(1 - ks, 1 + ks),
                "decalage_aval": p["decalage_aval"] + rng.uniform(-za, za),
                "coefs_personnalises": True,
                "xi_ref": p["xi_ref"], "K_yarnell_ref": p["K_yarnell_ref"],
                "xi_bat": rng.uniform(0.3, 0.8), "K_yarnell_bat": rng.uniform(1.05, 1.40),
                "K_A": rng.uniform(0.87, 1.07), "mu": rng.uniform(0.35, 0.40),
            }
            et = self._variante(**modif)
            res[i] = et.dz_methode(et.calcul_debit(Q * rng.uniform(1 - kq, 1 + kq)), methode)
        seuil = float(p["seuil_dz"])
        return {"tirages": res, "moyenne": float(np.mean(res)), "p50": float(np.percentile(res, 50)),
                "p90": float(np.percentile(res, 90)), "p95": float(np.percentile(res, 95)),
                "max": float(np.max(res)), "proba_depassement": float(np.mean(res > seuil)), "Q": Q}

    # ================================================================ synthèse
    def synthese(self, methode: str = "enveloppe") -> dict:
        p = self.p
        q_ref = self.Q_reference
        r = self.calcul_debit(q_ref)
        le = self.ligne_eau(q_ref, methode)
        enj = self.impacts_enjeux(le)
        dz_bar = self.dz_methode(r, methode)
        dz_enj = float(enj["dZ"].max()) if not enj.empty else math.nan
        q_seuil = self.debit_seuil_impact(methode)
        q_sub = self.debit_submersion(False)
        q_alerte = self.debit_submersion(True)
        ero_ = self.erosion(q_ref)
        seuil = float(p["seuil_dz"])
        crit = dz_enj if math.isfinite(dz_enj) else dz_bar
        p_seuil = self.proba_travaux(q_seuil) if q_seuil else 0.0
        p_acc = float(p["proba_acceptable"])
        if crit <= seuil + 1e-12:
            niveau = "ok"
            verdict = (f"Impact inférieur au seuil de {seuil * 100:.0f} cm pour la crue de référence "
                       f"Q{int(p['T_reference'])}.")
        elif p_seuil < p_acc:
            niveau = "attention"
            verdict = (f"Le seuil de {seuil * 100:.0f} cm est dépassé à partir de {q_seuil:.0f} m³/s, "
                       f"mais la probabilité d'atteindre ce débit pendant les travaux reste faible "
                       f"({p_seuil * 100:.1f} %). Acceptable sous réserve d'une procédure d'alerte et de "
                       f"retrait/effacement du batardeau, à valider avec le service police de l'eau.")
        else:
            niveau = "non_conforme"
            verdict = (f"Le seuil de {seuil * 100:.0f} cm est dépassé dès {q_seuil:.0f} m³/s, débit qui a "
                       f"{p_seuil * 100:.0f} % de chances d'être atteint pendant les travaux. Mesures à "
                       f"étudier : batardeau amovible avec retrait déclenché avant {q_seuil:.0f} m³/s "
                       f"(prévisions Vigicrues), réduction de l'emprise, phasage ou période plus favorable.")
        return {
            "Q_reference": q_ref, "T_reference": float(p["T_reference"]),
            "Q_chantier": self.Q_chantier, "T_chantier": float(p["T_chantier"]),
            "dZ_barrage": dz_bar, "methode_env": r.methode_env, "dZ_methodes": dict(r.dZ),
            "valide_methodes": dict(r.valide),
            "dZ_enjeux_max": dz_enj, "enjeux": enj,
            "distance_influence": self.distance_influence(le, 0.01),
            "Q_seuil": q_seuil, "T_seuil": self.periode_retour(q_seuil), "P_seuil": p_seuil,
            "Q_submersion": q_sub, "T_submersion": self.periode_retour(q_sub),
            "P_submersion": self.proba_travaux(q_sub) if q_sub else 0.0,
            "Q_alerte": q_alerte, "T_alerte": self.periode_retour(q_alerte),
            "P_alerte": self.proba_travaux(q_alerte) if q_alerte else 0.0,
            "Q_effacement_sans": self.debit_effacement(False), "Q_effacement_avec": self.debit_effacement(True),
            "P_chantier": self.proba_travaux(self.Q_chantier),
            "fraction_alea": self.fraction_alea, "taux_obstruction": self.taux_obstruction,
            "largeur_obstruee": self.largeur_obstruee,
            "erosion": ero_, "niveau": niveau, "verdict": verdict, "resultat_ref": r, "ligne_eau": le,
            "Z_amont_sans": r.Z_ref_base, "Z_amont_avec": r.Z_bat_env, "Z_aval": r.Z3,
        }
