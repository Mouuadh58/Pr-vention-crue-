"""Page 2 – Simulations en temps réel et résultats."""
import math

import numpy as np
import pandas as pd
import streamlit as st

from batcrue import exports, rapport
from batcrue.hydrologie import debit_de_projet_travaux
from ui import commun, graphiques
from ui.commun import cm, debit, fr, pct, periode

st.title("📈 Page 2 · Simulations & résultats")
commun.note_exemple()
if commun.erreurs_bloquantes():
    st.stop()

e = commun.etude()
c = commun.calculs()
s, courbe, tab = c["synthese"], c["courbe"], c["tableau"]
p = e.p
methode = p["methode_ligne_eau"]
seuil = float(p["seuil_dz"])
T_ref = int(p["T_reference"])

commun.bandeau_verdict(s)
k = st.columns(3) + st.columns(3)
k[0].metric(f"Surélévation au barrage · Q{T_ref}", cm(s["dZ_barrage"]),
            help=f"{commun.LIBELLES_METHODES[methode]}. Débit {debit(s['Q_reference'])}.")
k[1].metric("Surélévation max aux enjeux", cm(s["dZ_enjeux_max"]),
            help="Maximum de ΔZ sur les enjeux déclarés (page 1, onglet Rivière).")
k[2].metric(f"Débit où ΔZ atteint {cm(seuil, 0)}", debit(s["Q_seuil"]), help=f"Période de retour {periode(s['T_seuil'])}.")
k[3].metric("Probabilité pendant les travaux", pct(s["P_seuil"]),
            help="Probabilité qu'au moins une crue dépasse ce débit pendant l'installation du batardeau.")
k[4].metric("Submersion du batardeau", debit(s["Q_submersion"]),
            help=f"Période de retour {periode(s['T_submersion'])} ; probabilité pendant les travaux "
                 f"{pct(s['P_submersion'])}.")
er = s["erosion"]
k[5].metric("Vitesse dans les passes", fr(er["V_passes_avec"], 2, "m/s"),
            delta=f"+{fr(er['V_passes_avec'] - er['V_passes_sans'], 2)} m/s", delta_color="inverse",
            help=f"Q{T_ref}, avec batardeau ; écart par rapport à la situation sans batardeau.")

# ================================================================== simulation temps réel
st.divider()
st.subheader("🎛️ Simulation en temps réel")
q_min, q_max = int(math.floor(courbe["Q"].min())), int(math.ceil(courbe["Q"].max()))
if not (q_min <= st.session_state.get("sim_Q", -1) <= q_max):
    st.session_state["sim_Q"] = int(round(e.Q_reference))
taux_nom = int(round(e.taux_obstruction * 100))
if "sim_taux" not in st.session_state or st.session_state.get("_taux_nom") != taux_nom:
    st.session_state["sim_taux"] = taux_nom
    st.session_state["_taux_nom"] = taux_nom
raccourcis = {f"Q{T}": e.debit_T(T) for T in (2, 5, 10, 20, 50, 100)}


def _aller(code):
    st.session_state["sim_Q"] = int(round(raccourcis[st.session_state[code]]))


st.pills("Aller à", list(raccourcis), key="sim_raccourci", on_change=_aller, args=("sim_raccourci",))
c1, c2, c3 = st.columns([2.2, 1.4, 1.4])
with c1:
    Q = st.slider("Débit simulé Q (m³/s)", q_min, q_max, key="sim_Q", step=1)
with c2:
    taux = st.slider("Emprise du batardeau (% de la largeur des passes)", 0, 95, key="sim_taux", step=1,
                     help="Variante instantanée : ne modifie pas les données de la page 1.")
with c3:
    meth = st.selectbox("Méthode", ["enveloppe"] + e.methodes, key="sim_methode",
                        index=(["enveloppe"] + e.methodes).index(methode) if methode in (["enveloppe"] + e.methodes) else 0,
                        format_func=lambda m: commun.LIBELLES_METHODES.get(m, m))
larg = None if taux == taux_nom else taux / 100.0 * e.largeur_passes
r = e.calcul_debit(float(Q), larg)
le = e.ligne_eau(float(Q), meth, larg)
enj = e.impacts_enjeux(le)
dz = e.dz_methode(r, meth)
regime = r.bat[e.methode_base].regime if e.methode_base in r.bat else ""
m = st.columns(3) + st.columns(3)
m[0].metric("Période de retour", periode(e.periode_retour(float(Q))))
m[1].metric("Cote aval (m NGF)", fr(r.Z3, 2))
m[2].metric("Vitesse dans les passes", fr(r.bat[e.methode_base].V_passes, 2, "m/s"), help=regime)
m[3].metric("Amont sans batardeau (m NGF)", fr(r.Z_ref_base, 2),
            help="Retenue normale maintenue" if r.regule_ref else "Vannes entièrement ouvertes")
m[4].metric("Amont avec batardeau (m NGF)", fr(r.Z_ref_base + dz, 2),
            help="Retenue normale maintenue" if r.regule_bat else "Vannes entièrement ouvertes")
m[5].metric("Surélévation ΔZ", cm(dz), delta="au-dessus du seuil" if dz > seuil else "sous le seuil",
            delta_color="inverse" if dz > seuil else "normal", delta_arrow="off")
if r.regule_ref and r.regule_bat:
    st.caption("💡 À ce débit, le barrage tient sa retenue normale avec ou sans batardeau : aucun impact.")
elif r.regule_ref and not r.regule_bat:
    st.caption("💡 À ce débit, le batardeau fait perdre la régulation : sans lui, la retenue normale serait tenue.")
st.plotly_chart(graphiques.ligne_eau(le, enj, seuil), key="ligne_sim")
st.caption(f"Distance d'influence (ΔZ ≥ 1 cm) : **{fr(e.distance_influence(le) / 1000, 1)} km** "
           f"{'(toute la longueur étudiée)' if e.distance_influence(le) >= float(p['longueur_bief']) - 1 else ''}")
with st.expander("Voir les données : enjeux et ligne d'eau"):
    if not enj.empty:
        st.dataframe(enj.assign(dZ_cm=enj["dZ"] * 100).drop(columns=["dZ"]), hide_index=True, column_config={
            "enjeu": "Enjeu", "x": st.column_config.NumberColumn("x (m)", format="%.0f"),
            "Z_sans": st.column_config.NumberColumn("Z sans (m NGF)", format="%.3f"),
            "Z_avec": st.column_config.NumberColumn("Z avec (m NGF)", format="%.3f"),
            "dZ_cm": st.column_config.NumberColumn("ΔZ (cm)", format="%.1f"),
            "cote_dommages": st.column_config.NumberColumn("Cote dommages", format="%.2f"),
            "inonde_sans": "Atteint sans", "inonde_avec": "Atteint avec"})
    pas = max(1, int(round(500 / float(p["pas_calcul"]))))
    st.dataframe(le.iloc[::pas][["x", "z_fond", "Z_sans", "Z_avec", "dZ", "V_sans", "V_avec"]], hide_index=True)

# ================================================================== onglets de résultats
st.divider()
onglets = st.tabs(["📉 ΔZ selon le débit", "📏 Cotes au barrage", "📋 Par période de retour", "🎲 Risque pendant travaux",
                   "🌊 Crue simulée", "🔀 Variantes d'emprise", "🎯 Sensibilité & incertitudes",
                   "🪨 Vitesses, érosion, efforts"])

with onglets[0]:
    st.plotly_chart(graphiques.dz_debit(courbe, e, e.methodes, seuil), key="dz_q")
    st.markdown(f"L'impact est **nul tant que le barrage tient sa retenue** (jusqu'à {debit(s['Q_effacement_avec'])} "
                f"avec batardeau, {debit(s['Q_effacement_sans'])} sans). Au-delà, le batardeau rétrécit "
                "l'écoulement et la surélévation croît avec le débit. Traits pointillés : méthode hors de son domaine.")
    with st.expander("Voir les données"):
        cols = ["Q", "Z_aval", "Z_amont_sans", "Z_amont_avec", "dZ_enveloppe"] + [f"dZ_{m_}" for m_ in e.methodes]
        st.dataframe(courbe[cols].assign(**{c_: courbe[c_] * 100 for c_ in cols if c_.startswith("dZ")}),
                     hide_index=True)

with onglets[1]:
    st.plotly_chart(graphiques.cotes_debit(courbe, e), key="cotes_q")
    st.markdown(f"Crête du batardeau atteinte pour **{debit(s['Q_submersion'])}** ({periode(s['T_submersion'])}) ; "
                f"cote d'alerte (crête − revanche) pour **{debit(s['Q_alerte'])}** ({periode(s['T_alerte'])}).")

with onglets[2]:
    t = tab.copy()
    vue = pd.DataFrame({
        "Événement": t["evenement"], "T (ans)": t["T"], "Q (m³/s)": t["Q"],
        "Proba. pendant travaux (%)": t["P_travaux"] * 100, "Cote aval": t["Z_aval"],
        "Amont sans": t["Z_amont_sans"], "Amont avec": t["Z_amont_avec"],
        "ΔZ enveloppe (cm)": t["dZ_enveloppe"] * 100,
        **{f"ΔZ {m_} (cm)": t[f"dZ_{m_}"] * 100 for m_ in e.methodes},
        "V passes sans (m/s)": t["V_passes_sans"], "V passes avec (m/s)": t["V_passes_avec"],
        "Régime avec": t["regime_avec"]})
    fmt = {c_: st.column_config.NumberColumn(c_, format="%.1f") for c_ in vue.columns if "(cm)" in c_ or "(%)" in c_}
    fmt.update({c_: st.column_config.NumberColumn(c_, format="%.2f") for c_ in ("Cote aval", "Amont sans", "Amont avec",
                                                                              "V passes sans (m/s)", "V passes avec (m/s)")})
    fmt["Q (m³/s)"] = st.column_config.NumberColumn("Q (m³/s)", format="%.0f")
    fmt["T (ans)"] = st.column_config.NumberColumn("T (ans)", format="%.0f")
    st.dataframe(vue, hide_index=True, column_config=fmt)
    st.caption("Cotes en m NGF. Ajoutez des crues historiques en page 1 (onglet Hydrologie).")

with onglets[3]:
    d0, d1 = e.dates_travaux
    st.markdown(f"Batardeau en place du **{d0:%d/%m/%Y}** au **{d1:%d/%m/%Y}** ({(d1 - d0).days + 1} jours), "
                f"soit **{pct(s['fraction_alea'], 0)}** de l'aléa annuel "
                f"({'répartition uniforme' if p['saisonnalite'] == 'uniforme' else 'saisonnalité personnalisée'}).")
    st.plotly_chart(graphiques.risque(e, s), key="risque")
    lignes = [("Atteinte du seuil d'impact", s["Q_seuil"]), ("Alerte (crête − revanche)", s["Q_alerte"]),
              ("Submersion du batardeau", s["Q_submersion"]), (f"Crue de chantier Q{int(p['T_chantier'])}", s["Q_chantier"])]
    st.dataframe(pd.DataFrame([{"Événement": n, "Débit (m³/s)": q, "Période de retour": periode(e.periode_retour(q)),
                                "Probabilité pendant les travaux (%)": e.proba_travaux(q) * 100}
                               for n, q in lignes if q is not None]), hide_index=True,
                 column_config={"Débit (m³/s)": st.column_config.NumberColumn(format="%.0f"),
                                "Probabilité pendant les travaux (%)": st.column_config.NumberColumn(format="%.1f")})
    pa = float(p["proba_acceptable"])
    if 0 < pa < 1 and s["fraction_alea"] > 0:
        qp = debit_de_projet_travaux(e.gumbel, s["fraction_alea"], pa)
        st.info(f"Pour limiter le risque à **{pct(pa, 0)}** pendant les travaux, le dispositif doit tenir jusqu'à "
                f"**{debit(qp)}** ({periode(e.periode_retour(qp))} en statistique annuelle).", icon="🧭")

with onglets[4]:
    sim = commun.hydrogramme()
    st.plotly_chart(graphiques.hydrogramme(sim, p), key="hydro")
    a, b, c_ = st.columns(3)
    a.metric("Surélévation maximale", cm(sim["dZ_max"]))
    b.metric("Cote maximale avec batardeau", fr(sim["Z_max"], 2, "m NGF"))
    if sim["delai_alerte_submersion"] is not None:
        c_.metric("Délai entre alerte et submersion", fr(sim["delai_alerte_submersion"], 0, "h"),
                  help="Temps disponible pour mettre le chantier en sécurité après franchissement de la cote d'alerte.")
    elif sim["t_alerte"] is not None:
        c_.metric("Cote d'alerte atteinte après", fr(sim["t_alerte"], 0, "h"), help="La crête n'est pas atteinte.")
    else:
        c_.metric("Cote d'alerte", "non atteinte")
    st.caption("Calcul quasi-permanent : succession d'états permanents, adapté aux crues lentes de l'Oise.")

with onglets[5]:
    var = commun.variantes()
    st.plotly_chart(graphiques.variantes(var, seuil, e.taux_obstruction), key="variantes")
    lignes = []
    for f_, df_ in sorted(var.items()):
        dz_ref = float(np.interp(e.Q_reference, df_["Q"], df_["dZ_enveloppe"]))
        franchi = df_[df_["dZ_enveloppe"] >= seuil]
        lignes.append({"Emprise (% des passes)": f_ * 100, f"ΔZ à Q{T_ref} (cm)": dz_ref * 100,
                       "Débit d'atteinte du seuil (m³/s)": float(franchi["Q"].iloc[0]) if not franchi.empty else None})
    st.dataframe(pd.DataFrame(lignes), hide_index=True, column_config={
        "Emprise (% des passes)": st.column_config.NumberColumn(format="%.0f"),
        f"ΔZ à Q{T_ref} (cm)": st.column_config.NumberColumn(format="%.1f"),
        "Débit d'atteinte du seuil (m³/s)": st.column_config.NumberColumn(format="%.0f")})
    st.caption("Utile pour comparer un phasage des travaux (batardeau plus étroit) avec la solution de base.")

with onglets[6]:
    sens = commun.sensibilite(methode)
    st.plotly_chart(graphiques.tornade(sens), key="tornade")
    st.caption(f"ΔZ au barrage pour Q{T_ref} en faisant varier un paramètre à la fois.")
    st.markdown("**Propagation des incertitudes (Monte-Carlo)** — tirages simultanés de tous les paramètres incertains.")
    cle_mc = f"mc_{commun.params_json().__hash__()}_{methode}"
    if st.button(f"▶️ Lancer {int(p['mc_n'])} tirages", key="btn_mc") or st.session_state.get("_mc") == cle_mc:
        st.session_state["_mc"] = cle_mc
        with st.spinner("Calcul en cours…"):
            mc = commun.monte_carlo(methode)
        a, b, c_, d_ = st.columns(4)
        a.metric("Médiane", cm(mc["p50"]))
        b.metric("90ᵉ centile", cm(mc["p90"]))
        c_.metric("95ᵉ centile", cm(mc["p95"]))
        d_.metric(f"P(ΔZ > {cm(seuil, 0)})", pct(mc["proba_depassement"], 0))
        st.plotly_chart(graphiques.histogramme_mc(mc, seuil), key="mc")

with onglets[7]:
    ef = e.efforts(e.Q_reference)
    a, b, c_ = st.columns(3)
    with a:
        st.markdown(f"**Vitesses (Q{T_ref})**")
        st.metric("Passes sans → avec batardeau", f"{fr(er['V_passes_sans'], 2)} → {fr(er['V_passes_avec'], 2)} m/s")
        st.metric("Vitesse locale au nez", fr(er["V_locale"], 2, "m/s"),
                  delta="dépasse la vitesse admissible" if er["depasse"] else "admissible",
                  delta_color="inverse" if er["depasse"] else "normal", delta_arrow="off")
    with b:
        st.markdown("**Protection (Isbash)**")
        st.metric("Diamètre des blocs", fr(er["D_isbash"], 2, "m"))
        st.metric("Masse unitaire", fr(er["M_bloc"], 0, "kg"))
        if p["fond_affouillable"]:
            st.metric("Affouillement de contraction (Laursen)", fr(er["affouillement"], 2, "m"))
    with c_:
        st.markdown("**Efforts sur le batardeau**")
        st.metric("Poussée hydrostatique", fr(ef["F_hydro"] / 1000, 0, "kN/m"),
                  help=f"Hauteur d'eau {fr(ef['h'], 2)} m (enceinte à sec).")
        st.metric("Supplément dynamique", fr(ef["F_dyn"] / 1000, 1, "kN/m"))
        if ef["submerge"]:
            st.error("Batardeau submergé à ce débit : efforts calculés à la cote de crête.", icon="🌊")
        if ef["lane"]:
            ln = ef["lane"]
            (st.success if ln["ok"] else st.error)(
                f"Règle de Lane : Lw/ΔH = {fr(ln['ratio'], 2)} pour {fr(ln['C_L'], 1)} requis "
                f"(ΔH max ≈ {fr(ln['delta_h_max'], 2)} m).")
    st.plotly_chart(graphiques.vitesses(courbe, e), key="vitesses")
    st.caption("Ordres de grandeur : ne remplacent ni la note de calcul du fournisseur, ni l'étude géotechnique.")

# ================================================================== exports
st.divider()
st.subheader("📤 Exports")
a, b, c_ = st.columns(3)
with a:
    if st.button("📄 Préparer le rapport (HTML imprimable)", key="btn_rapport"):
        st.session_state["_rapport"] = rapport.generer_html(e, s, courbe, tab)
    if st.session_state.get("_rapport"):
        st.download_button("⬇️ Télécharger le rapport", st.session_state["_rapport"].encode("utf-8"),
                           file_name="rapport_impact_batardeau.html", mime="text/html")
with b:
    st.download_button("📊 Résultats (Excel)", exports.excel_resultats(e, s, courbe, tab),
                       file_name="resultats_batardeau.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
with c_:
    st.download_button("💾 Données (JSON)", commun.params_json().encode("utf-8"), file_name="donnees_batardeau.json",
                       mime="application/json")
