"""Page 3 – Suivi en temps réel (Hub'Eau) et analyse des chroniques de débit."""
import io
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from batcrue import hubeau
from batcrue.hydrologie import Gumbel, analyse_chronique, frequence_empirique
from batcrue.parametres import MOIS
from ui import commun, etat
from ui.commun import cm, debit, fr, palette, pct, periode
from ui.etat import P

st.title("🛰️ Page 3 · Temps réel & données de débit")
st.caption("Débits officiels via l'API publique Hub'Eau (stations de la Banque Hydro), sans clé. "
           "Sans connexion, saisissez un débit ou importez une chronique CSV.")
if commun.erreurs_bloquantes():
    st.stop()
e = commun.etude()
s = commun.calculs()["synthese"]
p = e.p


def etat_chantier(q: float) -> tuple[str, str]:
    """Niveau d'alerte du chantier pour un débit observé."""
    seuils = [(s["Q_submersion"], "critique", "Batardeau submergé : évacuation du chantier"),
              (s["Q_alerte"], "critique", "Cote d'alerte atteinte : mise en sécurité du chantier"),
              (s["Q_seuil"], "vigilance", "Impact supérieur au seuil admissible : déclencher la procédure crue")]
    for qs, niveau, texte in seuils:
        if qs is not None and q >= qs:
            return niveau, texte
    if s["Q_seuil"] is not None and q >= 0.85 * s["Q_seuil"]:
        return "vigilance", "Débit proche du seuil d'impact : surveiller les prévisions Vigicrues"
    return "normal", "Situation normale"


def afficher_situation(q: float, quand: str) -> None:
    r = e.calcul_debit(q)
    niveau, texte = etat_chantier(q)
    (st.error if niveau == "critique" else st.warning if niveau == "vigilance" else st.success)(
        f"**{texte}** — débit {fr(q, 0, 'm³/s')} ({quand}).",
        icon="⛔" if niveau == "critique" else "⚠️" if niveau == "vigilance" else "✅")
    c = st.columns(5)
    c[0].metric("Débit", fr(q, 0, "m³/s"), help=f"Période de retour {periode(e.periode_retour(q))}")
    c[1].metric("Cote aval", fr(r.Z3, 2, "m NGF"))
    c[2].metric("Amont sans batardeau", fr(r.Z_ref_base, 2, "m NGF"))
    c[3].metric("Amont avec batardeau", fr(r.Z_bat_env, 2, "m NGF"))
    c[4].metric("Surélévation", cm(r.dZ_env))
    st.caption(f"Seuils du chantier : impact ≥ {cm(float(p['seuil_dz']), 0)} dès {debit(s['Q_seuil'])} · "
               f"alerte dès {debit(s['Q_alerte'])} · submersion dès {debit(s['Q_submersion'])}.")


onglet_tr, onglet_hist = st.tabs(["📡 Débit actuel", "🗂️ Chroniques & statistiques"])

with onglet_tr:
    a, b = st.columns([1.2, 1])
    with a:
        dep = st.selectbox("Département de la station", ["60", "95", "02", "80", "08"],
                           format_func=lambda d: {"60": "60 – Oise", "95": "95 – Val-d'Oise", "02": "02 – Aisne",
                                                  "80": "80 – Somme", "08": "08 – Ardennes"}[d])
        if st.button("🔎 Lister les stations de l'Oise", key="btn_stations"):
            try:
                st.session_state["_stations"] = hubeau.stations(dep, "Oise")
            except hubeau.HubEauErreur as exc:
                st.error(str(exc))
        stations = st.session_state.get("_stations", [])
        code = "__autre__"
        if stations:
            libelles = {x["code_station"]: f"{x['libelle_station']} ({x['code_station']})" for x in stations}
            libelles["__autre__"] = "Autre code…"
            code = st.selectbox("Station", list(libelles), format_func=libelles.get)
        if code == "__autre__":
            etat.texte("code_station", "Code station Hub'Eau (relevé sur l'HydroPortail)")
        else:
            P()["code_station"] = code
    with b:
        manuel = st.number_input("Débit saisi manuellement (m³/s)", min_value=0.0, value=float(round(e.Q_chantier)),
                                 step=10.0, help="Par exemple le débit annoncé par Vigicrues.")
        if st.button("Évaluer ce débit", key="btn_manuel"):
            st.session_state["_q_obs"] = (manuel, "saisie manuelle")
    if st.button("📡 Lire le débit actuel", type="primary", key="btn_tr", disabled=not P().get("code_station")):
        try:
            serie = hubeau.observations_temps_reel(P()["code_station"], "Q", taille=1000)
            st.session_state["_serie_tr"] = serie
            quand, q = serie[0]
            st.session_state["_q_obs"] = (q, f"observé le {quand.astimezone():%d/%m/%Y à %H:%M}")
        except hubeau.HubEauErreur as exc:
            st.error(f"{exc} Vous pouvez saisir le débit manuellement.")
    if st.session_state.get("_q_obs"):
        afficher_situation(*st.session_state["_q_obs"])
    serie = st.session_state.get("_serie_tr")
    if serie:
        pal = palette()
        t = [x[0] for x in serie]
        q = [x[1] for x in serie]
        fig = go.Figure(go.Scatter(x=t, y=q, mode="lines", line=dict(color=pal["serie"][0], width=2),
                                   name="Débit observé", hovertemplate="%{y:.0f} m³/s<extra></extra>"))
        for qs, nom, coul in ((s["Q_seuil"], "Seuil d'impact", pal["critique"]),
                              (s["Q_alerte"], "Alerte", pal["encre2"])):
            if qs:
                fig.add_hline(y=qs, line=dict(color=coul, width=1.5, dash="dash"), annotation_text=nom)
        fig.update_layout(separators=", ", height=360, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                          yaxis_title="Débit (m³/s)")
        st.plotly_chart(fig, key="tr_fig")
    st.info("Prévisions : consultez **vigicrues.gouv.fr** (tronçon Oise) et saisissez le débit prévu ci-dessus "
            "pour anticiper le déclenchement de la procédure crue du chantier.", icon="🧭")

with onglet_hist:
    st.markdown("Analyse des **débits moyens journaliers** : maxima annuels, loi de Gumbel, saisonnalité des crues "
                "et fréquence des crues pendant la fenêtre de travaux.")
    a, b, c = st.columns(3)
    with a:
        d_debut = st.date_input("Début de la chronique", date(1970, 1, 1), format="DD/MM/YYYY")
    with b:
        d_fin = st.date_input("Fin de la chronique", date.today() - timedelta(days=1), format="DD/MM/YYYY")
    with c:
        st.write("")
        if st.button("⬇️ Télécharger (Hub'Eau)", key="btn_hist", disabled=not P().get("code_station")):
            try:
                with st.spinner("Téléchargement des débits journaliers…"):
                    st.session_state["_chronique"] = hubeau.debits_journaliers(P()["code_station"], d_debut, d_fin)
            except hubeau.HubEauErreur as exc:
                st.error(str(exc))
    fcsv = st.file_uploader("…ou importer un CSV « date;débit » (export HydroPortail, m³/s)", type=["csv", "txt"])
    if fcsv is not None:
        try:
            txt = fcsv.getvalue().decode("utf-8-sig", errors="replace")
            sep = ";" if txt.count(";") >= txt.count(",") else ","
            df = pd.read_csv(io.StringIO(txt), sep=sep)
            dates = pd.to_datetime(df.iloc[:, 0], dayfirst=True, errors="coerce")
            valeurs = pd.to_numeric(df.iloc[:, 1].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            ok = dates.notna() & valeurs.notna()
            st.session_state["_chronique"] = (list(dates[ok].dt.date), list(valeurs[ok]))
        except Exception as exc:  # noqa: BLE001 - message utilisateur
            st.error(f"Fichier illisible : {exc}")
    chron = st.session_state.get("_chronique")
    if chron:
        d0, d1 = e.dates_travaux
        try:
            an = analyse_chronique(chron[0], chron[1], (d0.month, d0.day), (d1.month, d1.day))
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        maxima = an["maxima_annuels"]
        st.success(f"{len(an['serie'])} jours de données, {len(maxima)} années complètes.")
        if len(maxima) >= 5:
            gm = Gumbel.par_moments(list(maxima.values()))
            gv = Gumbel.par_max_vraisemblance(list(maxima.values()))
            x, y, z = st.columns(3)
            x.metric("Gumbel (moments)", f"u = {fr(gm.u, 0)} · β = {fr(gm.beta, 0)}", help=f"Q100 = {debit(gm.quantile(100))}")
            y.metric("Gumbel (max. de vraisemblance)", f"u = {fr(gv.u, 0)} · β = {fr(gv.beta, 0)}",
                     help=f"Q100 = {debit(gv.quantile(100))}")
            q_s = s["Q_seuil"]
            if q_s:
                z.metric("Fréquence empirique d'atteinte du seuil pendant la fenêtre de travaux",
                         pct(frequence_empirique(an["maxima_fenetre"], q_s), 0),
                         help=f"Années où le maximum journalier dans la fenêtre {d0:%d/%m}–{d1:%d/%m} dépasse {debit(q_s)}.")
            st.caption("Débits moyens journaliers : légèrement inférieurs aux pointes instantanées (sur l'Oise, crues "
                       "lentes, l'écart reste modéré). Vérifiez avec les statistiques QIX de l'HydroPortail.")
            if st.button("Appliquer la loi de Gumbel (moments) à l'étude", key="btn_appl_g"):
                P()["mode_hydro"] = "gumbel"
                P()["gumbel_u"], P()["gumbel_beta"] = round(gm.u, 1), round(gm.beta, 1)
                etat.remplacer(P())
                st.rerun()
        pal = palette()
        fig = go.Figure(go.Bar(x=MOIS, y=np.array(an["poids_mensuels"]) * 100, marker=dict(color=pal["serie"][0],
                                                                                          cornerradius=4),
                               hovertemplate="%{x} : %{y:.1f} %<extra></extra>"))
        fig.update_layout(separators=", ", height=300, margin=dict(l=10, r=10, t=30, b=10),
                          yaxis_title="Part des maxima annuels (%)", hovermode="closest")
        st.plotly_chart(fig, key="saisons")
        if st.button("Appliquer cette saisonnalité à l'étude", key="btn_appl_s"):
            P()["saisonnalite"] = "personnalisee"
            P()["poids_mensuels"] = [round(v, 4) for v in an["poids_mensuels"]]
            etat.remplacer(P())
            st.rerun()
        with st.expander("Voir les maxima annuels"):
            st.dataframe(pd.DataFrame({"Année": list(maxima), "Maximum journalier (m³/s)": list(maxima.values()),
                                       "Maximum dans la fenêtre de travaux (m³/s)":
                                           [an["maxima_fenetre"].get(k) for k in maxima]}), hide_index=True)
