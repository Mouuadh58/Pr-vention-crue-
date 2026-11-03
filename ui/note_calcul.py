"""Note de calcul détaillée, pas à pas, pour un débit donné (formules et valeurs numériques)."""
from __future__ import annotations

import math

import streamlit as st

from batcrue.constantes import G
from batcrue.ouvrage import METHODES
from ui.commun import cm, fr


def lx(x, n: int = 3) -> str:
    """Nombre formaté pour LaTeX avec virgule décimale."""
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return r"\text{—}"
    return f"{x:.{n}f}".replace(".", "{,}")


def _largeurs(etude, avec: bool) -> float:
    return sum(b for b, _ in etude.ouvertures(avec))


def afficher(etude, Q: float) -> None:
    p = etude.p
    r = etude.calcul_debit(Q)
    T = etude.periode_retour(Q)
    B = float(p["largeur_riviere"])
    zf = float(p["cote_fond"])
    b_sans, b_avec = _largeurs(etude, False), _largeurs(etude, True)

    st.markdown(f"#### 1. Données au débit étudié Q = {fr(Q, 1)} m³/s (période de retour {fr(T, 1)} ans)")
    st.markdown(
        f"- Largeur hydraulique de la rivière au droit du barrage : **B = {fr(B, 2)} m**, fond à **{fr(zf, 2)} m NGF**\n"
        f"- Largeur libre des passes : **b₂ = {fr(b_sans, 2)} m** sans batardeau, **{fr(b_avec, 2)} m** avec "
        f"batardeau (emprise {fr(etude.largeur_obstruee, 2)} m, soit {fr(etude.taux_obstruction * 100, 1)} % des passes)")

    # ----------------------------------------------------------- aval
    st.markdown("#### 2. Cote aval Z₃ (condition limite)")
    if p["mode_aval"] == "normale":
        sec = etude.section_ref
        yn = sec.hauteur_normale(Q, float(p["pente"]))
        A, P_, Tm, Kd, alpha = sec.proprietes(yn)
        st.markdown("Hauteur normale par la formule de **Manning-Strickler** dans le bief aval (lit mineur + lit majeur, "
                    "méthode des lits séparés) :")
        st.latex(r"Q = \sum_i K_i\,A_i\,R_i^{2/3}\,\sqrt{I} \;\Rightarrow\; y_n = %s\ \text{m}"
                 r"\quad (A = %s\ \text{m}^2,\ \text{débitance } K_d = %s\ \text{m}^3/\text{s},\ I = %s)"
                 % (lx(yn), lx(A, 1), lx(Kd, 0), lx(float(p["pente"]), 5)))
        z_n = zf + yn
        st.latex(r"Z_3 = \max(z_f + y_n\ ;\ RN_{aval}) + \delta = \max(%s\ ;\ %s) + %s = %s\ \text{m NGF}"
                 % (lx(z_n), lx(float(p["rn_aval"]), 2), lx(float(p["decalage_aval"]), 2), lx(r.Z3)))
    elif p["mode_aval"] == "tableau":
        st.markdown(f"Interpolation linéaire dans la loi hauteur-débit aval saisie : **Z₃ = {fr(r.Z3, 3)} m NGF**.")
    else:
        st.markdown(f"Cote aval imposée : **Z₃ = {fr(r.Z3, 3)} m NGF**.")
    y3 = r.Z3 - zf
    st.latex(r"V_3 = \frac{Q}{B\,(Z_3 - z_f)} = \frac{%s}{%s \times %s} = %s\ \text{m/s}"
             r"\qquad Fr_3 = \frac{V_3}{\sqrt{g\,y_3}} = %s"
             % (lx(Q, 1), lx(B, 2), lx(y3), lx(r.V3), lx(r.V3 / math.sqrt(G * y3))))

    cols = st.columns(2)
    for col, avec, cle in ((cols[0], False, "ref"), (cols[1], True, "bat")):
        res = getattr(r, cle)
        titre = "Avec batardeau" if avec else "Sans batardeau"
        with col:
            st.markdown(f"##### {titre}")
            if "A" in res:
                _methode_a(res["A"], Q, avec)
            if "B" in res:
                _methode_b(res["B"])
            if "C" in res:
                _methode_c(res["C"], Q)
            if "D" in res:
                _methode_d(res["D"], Q)

    # ----------------------------------------------------------- synthèse
    st.markdown("#### 7. Régulation du barrage et surélévation")
    if p["regulation"]:
        st.markdown(f"Tant qu'il le peut, le barrage maintient la retenue normale **RN = {fr(float(p['rn_amont']), 2)} m NGF** : "
                    "la cote amont réelle est $Z_{amont} = \\max(RN\\,;\\,Z_1)$.")
    lignes = []
    for m in etude.methodes:
        lignes.append({"Méthode": f"{m} · {METHODES[m]}",
                       "Z amont sans (m NGF)": fr(r.Z_ref[m], 3), "Z amont avec (m NGF)": fr(r.Z_bat[m], 3),
                       "ΔZ": cm(r.dZ[m]), "Valide": "oui" if r.valide[m] else "hors domaine"})
    st.dataframe(lignes, hide_index=True)
    st.success(f"**Surélévation retenue (enveloppe des méthodes valides) : ΔZ = {cm(r.dZ_env)}** "
               f"— méthode la plus défavorable : {r.methode_env} ({METHODES.get(r.methode_env, '')}).", icon="📌")


def _methode_a(res, Q, avec):
    st.markdown("**3. Méthode A — Bernoulli + pertes singulières (Borda-Carnot)**")
    d = res.details or {}
    if "b2" in d:
        xi = d["xi"]
        st.latex(r"y_{c2} = \left(\frac{Q^2}{g\,b_2^2}\right)^{1/3} = %s\ \text{m}" % lx(d["yc2"]))
        st.latex(r"Z_2 + \frac{V_2^2}{2g} = E_3 + \frac{(V_2 - V_3)^2}{2g}")
        st.latex(r"\Rightarrow\ Z_2 = %s\ \text{m NGF},\quad V_2 = %s\ \text{m/s}" % (lx(d["Z2"]), lx(res.V_passes)))
        st.caption("Régime : " + res.regime + (" — contrôle par la hauteur critique (Bélanger)." if not d["noye"] else ""))
        st.latex(r"Z_1 + \frac{V_1^2}{2g} = E_2 + \xi\,\frac{V_2^2 - V_1^2}{2g}")
        st.latex(r"\xi = %s\ \Rightarrow\ Z_1 = %s\ \text{m NGF}" % (lx(xi, 2), lx(res.Z_amont)))
    else:
        st.markdown("Passes à seuils différents : répartition du débit entre groupes de passes "
                    f"({', '.join(fr(q, 1) for q in d.get('debits_groupes', []))} m³/s).")
        st.latex(r"Z_1 = %s\ \text{m NGF}" % lx(res.Z_amont))


def _methode_b(res):
    st.markdown("**4. Méthode B — Yarnell (1934)**")
    d = res.details or {}
    if not d:
        st.caption(res.remarque)
        return
    st.latex(r"\Delta h = 2K\,(K + 10\,\omega - 0{,}6)\,(\alpha + 15\,\alpha^4)\,\frac{V_3^2}{2g}")
    st.latex(r"K = %s,\ \alpha = %s,\ \omega = %s" % (lx(d["K"], 2), lx(d["alpha"]), lx(d["omega"], 4)))
    st.latex(r"\Rightarrow\ \Delta h = %s\ \text{m},\quad Z_1 = %s\ \text{m NGF}" % (lx(d["dh"]), lx(res.Z_amont)))
    if res.remarque:
        st.caption("⚠️ " + res.remarque)


def _methode_c(res, Q):
    st.markdown("**5. Méthode C — d'Aubuisson (1840)**")
    d = res.details or {}
    if not d:
        st.caption(res.remarque)
        return
    st.latex(r"Q = K_A \sum_i b_i\,(Z_3 - z_{s,i})\,\sqrt{2g\,\Delta h + V_1^2}")
    st.latex(r"K_A = %s,\ A_{libre} = %s\ \text{m}^2" % (lx(d["K_A"], 2), lx(d["A_libre"], 1)))
    st.latex(r"\Rightarrow\ \Delta h = %s\ \text{m},\quad Z_1 = %s\ \text{m NGF}" % (lx(d["dh"]), lx(res.Z_amont)))


def _methode_d(res, Q):
    st.markdown("**6. Méthode D — lois de seuil dénoyé / noyé**")
    d = res.details or {}
    if not d:
        st.caption(res.remarque)
        return
    st.latex(r"\text{dénoyé } (h_2 \le \tfrac{2}{3} h_1) : Q = \mu\,b\sqrt{2g}\,h_1^{3/2}")
    st.latex(r"\text{noyé} : Q = \mu_s\,b\,h_2\sqrt{2g\,(h_1 - h_2)},\quad \mu_s = \tfrac{3\sqrt{3}}{2}\,\mu")
    st.latex(r"\mu = %s,\ \mu_s = %s\ \Rightarrow\ \text{régime %s},\quad Z_1 = %s\ \text{m NGF}"
             % (lx(d["mu"], 3), lx(d["mu_s"], 3), res.regime, lx(res.Z_amont)))
