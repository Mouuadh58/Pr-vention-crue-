"""Page 1 – Données d'entrée et calculs détaillés."""
import pandas as pd
import streamlit as st

from batcrue import FORMES, METHODES, defauts, depuis_json
from batcrue.efforts import COEFFICIENTS_LANE
from batcrue.hydrologie import PERIODES_RETOUR
from batcrue.parametres import MOIS
from ui import commun, etat, graphiques, note_calcul
from ui.etat import P

st.title("📋 Page 1 · Données & calculs")
st.caption("Saisissez les données du barrage, du batardeau et de la rivière. Tout est recalculé "
           "instantanément ; les résultats et simulations sont sur la page 2.")
commun.note_exemple()

# ------------------------------------------------------------------ fichiers
c1, c2, c3 = st.columns([1, 1, 2])
with c1:
    if st.button("↺ Recharger l'exemple", help="Remet toutes les données d'exemple."):
        etat.remplacer(defauts())
        st.rerun()
with c2:
    st.download_button("💾 Enregistrer les données", commun.params_json().encode("utf-8"),
                       file_name="donnees_batardeau.json", mime="application/json",
                       help="Fichier JSON réutilisable (à rouvrir avec « Ouvrir »).")
with c3:
    f = st.file_uploader("Ouvrir un fichier de données (.json)", type=["json"], label_visibility="collapsed")
    if f is not None and st.session_state.get("_dernier_fichier") != (f.name, f.size):
        try:
            etat.remplacer(depuis_json(f.getvalue()))
            st.session_state["_dernier_fichier"] = (f.name, f.size)
            st.rerun()
        except (ValueError, KeyError) as exc:
            st.error(f"Fichier illisible : {exc}")

zone_alertes = st.container()
LIB_FORMES = {k: v["libelle"] for k, v in FORMES.items()}
onglets = st.tabs(["🏗️ Barrage & batardeau", "🌊 Rivière (amont / aval)", "📊 Hydrologie & travaux",
                   "🎯 Critères & méthodes", "⚙️ Compléments"])

# ================================================================== barrage
with onglets[0]:
    a, b = st.columns(2)
    with a:
        st.subheader("Barrage")
        etat.texte("nom_projet", "Intitulé de l'étude")
        etat.texte("nom_barrage", "Barrage")
        etat.nombre("largeur_riviere", "Largeur hydraulique au droit du barrage B (m)", 0.5, "%.2f", 1.0,
                    aide="Largeur entre culées, hors écluse : sections d'approche et de restitution.")
        etat.nombre("cote_fond", "Cote du fond au droit du barrage (m NGF)", 0.05, "%.2f")
        if etat.case("regulation", "Barrage régulé (maintien de la retenue normale)",
                     aide="Tant que les vannes ne sont pas toutes ouvertes, le barrage maintient la RN : "
                          "l'impact du batardeau est alors nul."):
            etat.nombre("rn_amont", "Retenue normale amont RN (m NGF)", 0.05, "%.2f")
        etat.choix("forme_piles", "Forme des piles existantes", list(FORMES), LIB_FORMES)
    with b:
        st.subheader("Batardeau")
        etat.texte("type_batardeau", "Type de batardeau")
        etat.choix("forme_batardeau", "Forme du nez du batardeau", list(FORMES), LIB_FORMES)
        etat.nombre("cote_arase", "Cote de crête (arase) du batardeau (m NGF)", 0.05, "%.2f")
        etat.nombre("revanche", "Revanche de sécurité (m)", 0.05, "%.2f", 0.0)
        etat.nombre("longueur_batardeau", "Emprise dans le sens du courant (m)", 1.0, "%.1f", 0.0)
        etat.nombre("cote_fond_enceinte", "Cote du fond de l'enceinte asséchée (m NGF)", 0.05, "%.2f")
        d1, d2 = st.columns(2)
        with d1:
            etat.jour("debut_travaux", "Pose du batardeau")
        with d2:
            etat.jour("fin_travaux", "Dépose du batardeau")
    st.markdown("**Passes du barrage** — indiquez la part de chaque passe occupée par le batardeau "
                "(1 = passe entièrement obstruée).")
    etat.tableau("passes", ["nom", "largeur", "cote_seuil", "obstruction"], {
        "nom": st.column_config.TextColumn("Passe", required=True),
        "largeur": st.column_config.NumberColumn("Largeur (m)", min_value=0.0, format="%.2f", required=True),
        "cote_seuil": st.column_config.NumberColumn("Cote du seuil (m NGF)", format="%.2f", required=True),
        "obstruction": st.column_config.NumberColumn("Part obstruée (0 à 1)", min_value=0.0, max_value=1.0,
                                                     step=0.05, format="%.2f", required=True),
    }, requis=["largeur", "cote_seuil"])
    zone_schema = st.container()

# ================================================================== rivière
with onglets[1]:
    st.subheader("Bief amont (propagation de la surélévation)")
    mode = etat.choix("mode_bief", "Description du bief", ["prismatique", "tableau"],
                      {"prismatique": "Section type constante + pente moyenne",
                       "tableau": "Profils en travers tabulés (levés)"}, horizontal=True)
    if mode == "prismatique":
        a, b, c = st.columns(3)
        with a:
            etat.nombre("b_min", "Largeur au fond du lit mineur (m)", 1.0, "%.1f", 0.1)
            etat.nombre("m_berge", "Fruit des berges (H/V)", 0.1, "%.2f", 0.0)
        with b:
            etat.nombre("h_berge", "Hauteur de berge / plein bord (m)", 0.1, "%.2f", 0.1)
            etat.nombre("B_maj", "Largeur du lit majeur actif (m)", 10.0, "%.0f", 0.0,
                        aide="Somme rive gauche + rive droite ; 0 si la vallée est endiguée.")
        with c:
            etat.nombre("K_min", "Strickler lit mineur K (m^1/3/s)", 1.0, "%.1f", 1.0)
            etat.nombre("K_maj", "Strickler lit majeur K (m^1/3/s)", 1.0, "%.1f", 1.0)
    else:
        st.markdown("Profils en travers (x = distance vers l'amont depuis le barrage), interpolés linéairement :")
        etat.tableau("sections_tabulees", ["x", "z_fond", "b", "m", "h_berge", "B_maj", "K_min", "K_maj"], {
            "x": st.column_config.NumberColumn("x (m)", format="%.0f"),
            "z_fond": st.column_config.NumberColumn("Fond (m NGF)", format="%.2f"),
            "b": st.column_config.NumberColumn("b fond (m)", format="%.1f"),
            "m": st.column_config.NumberColumn("Fruit", format="%.2f"),
            "h_berge": st.column_config.NumberColumn("h berge (m)", format="%.2f"),
            "B_maj": st.column_config.NumberColumn("Lit majeur (m)", format="%.0f"),
            "K_min": st.column_config.NumberColumn("K mineur", format="%.1f"),
            "K_maj": st.column_config.NumberColumn("K majeur", format="%.1f"),
        }, requis=["x", "z_fond", "b", "m", "h_berge", "B_maj", "K_min", "K_maj"])
        st.caption("Le lit d'aval reste décrit par la section type ci-dessous (hauteur normale).")
        a, b, c = st.columns(3)
        with a:
            etat.nombre("b_min", "Aval : largeur au fond (m)", 1.0, "%.1f", 0.1)
            etat.nombre("m_berge", "Aval : fruit des berges", 0.1, "%.2f", 0.0)
        with b:
            etat.nombre("h_berge", "Aval : hauteur de berge (m)", 0.1, "%.2f", 0.1)
            etat.nombre("B_maj", "Aval : lit majeur (m)", 10.0, "%.0f", 0.0)
        with c:
            etat.nombre("K_min", "Aval : Strickler lit mineur", 1.0, "%.1f", 1.0)
            etat.nombre("K_maj", "Aval : Strickler lit majeur", 1.0, "%.1f", 1.0)
    a, b, c = st.columns(3)
    with a:
        etat.nombre("pente", "Pente moyenne I (m/m)", 0.00001, "%.5f", 0.000001,
                    aide="Ex. 0,0002 = 20 cm/km.")
    with b:
        etat.nombre("longueur_bief", "Longueur étudiée vers l'amont (m)", 500.0, "%.0f", 100.0,
                    aide="Typiquement jusqu'au barrage amont.")
    with c:
        etat.nombre("pas_calcul", "Pas de calcul de la courbe de remous (m)", 10.0, "%.0f", 5.0)
    with st.expander("Valeurs usuelles du coefficient de Strickler"):
        st.markdown("| Type de lit | K (m^1/3/s) |\n|---|---|\n| Canal béton lisse | 70 – 90 |\n"
                    "| Rivière canalisée, fond sablo-graveleux, berges régulières | 30 – 40 |\n"
                    "| Rivière naturelle avec végétation | 20 – 30 |\n| Lit majeur en prairie | 15 – 25 |\n"
                    "| Lit majeur boisé ou bâti | 5 – 15 |")
    st.markdown("**Enjeux à vérifier** (x = distance vers l'amont, cote de premiers dommages facultative)")
    etat.tableau("enjeux", ["nom", "x", "cote_dommages"], {
        "nom": st.column_config.TextColumn("Enjeu", required=True),
        "x": st.column_config.NumberColumn("x (m)", format="%.0f", required=True),
        "cote_dommages": st.column_config.NumberColumn("Cote de premiers dommages (m NGF)", format="%.2f"),
    }, requis=["nom", "x"])

    st.subheader("Condition aval")
    mode_aval = etat.choix("mode_aval", "Cote aval Z₃", ["normale", "tableau", "constante"],
                           {"normale": "Hauteur normale (Strickler)", "tableau": "Loi hauteur-débit mesurée",
                            "constante": "Cote imposée"}, horizontal=True)
    a, b = st.columns(2)
    with a:
        if mode_aval == "normale":
            etat.nombre("rn_aval", "Retenue normale du bief aval (m NGF)", 0.05, "%.2f",
                        aide="Cote minimale tenue par le barrage aval.")
        elif mode_aval == "constante":
            etat.nombre("cote_aval_constante", "Cote aval imposée (m NGF)", 0.05, "%.2f")
        etat.nombre("decalage_aval", "Décalage appliqué à la cote aval (m)", 0.05, "%.2f",
                    aide="Pour tester la sensibilité (ex. +0,20 m).")
    with b:
        if mode_aval == "tableau":
            etat.tableau("loi_aval", ["Q", "Z"], {
                "Q": st.column_config.NumberColumn("Débit (m³/s)", format="%.1f", required=True),
                "Z": st.column_config.NumberColumn("Cote aval (m NGF)", format="%.2f", required=True),
            }, requis=["Q", "Z"])
            st.caption("Échelle aval du barrage, études PPRI… Extrapolation linéaire au-delà du dernier point.")

# ================================================================== hydrologie
with onglets[2]:
    st.subheader("Débits de crue")
    mode_h = etat.choix("mode_hydro", "Loi des débits de pointe", ["gumbel", "quantiles"],
                        {"gumbel": "Paramètres de Gumbel", "quantiles": "Tableau Q(T) (ex. HydroPortail) – ajusté"},
                        horizontal=True)
    if mode_h == "gumbel":
        a, b = st.columns(2)
        with a:
            etat.nombre("gumbel_u", "Paramètre de position u (m³/s)", 1.0, "%.1f")
        with b:
            etat.nombre("gumbel_beta", "Paramètre d'échelle β (m³/s)", 1.0, "%.1f", 0.1)
    else:
        etat.tableau("quantiles", ["T", "Q"], {
            "T": st.column_config.NumberColumn("Période de retour T (ans)", min_value=1.01, format="%.0f", required=True),
            "Q": st.column_config.NumberColumn("Débit Q_T (m³/s)", format="%.1f", required=True),
        }, requis=["T", "Q"])
    try:
        g = commun.etude().gumbel
        st.markdown(f"Loi utilisée : **u = {commun.fr(g.u, 1)} m³/s, β = {commun.fr(g.beta, 1)} m³/s**")
        st.dataframe(pd.DataFrame({"T (ans)": PERIODES_RETOUR + [1000],
                                   "Q_T (m³/s)": [round(g.quantile(T), 1) for T in PERIODES_RETOUR + [1000]]}).T,
                     column_config={i: st.column_config.Column(width="small") for i in range(7)})
    except Exception as exc:  # noqa: BLE001 - message utilisateur
        st.error(f"Loi hydrologique invalide : {exc}")
    with st.expander("ℹ️ Ordres de grandeur sur l'Oise et incertitude de la crue centennale"):
        st.markdown("À Venette, l'Entente Oise-Aisne estime **Q100 ≈ 623 m³/s** (loi GPD, 1910-2021) ; une autre "
                    "analyse avec crues historiques donne **≈ 686 m³/s**, et l'étude Hydratec (2014) retenait "
                    "**770 m³/s**. Cet écart de ±10 % justifie l'analyse de sensibilité de la page 2. "
                    "Récupérez les débits officiels de votre station sur l'HydroPortail ou via la page 3 (Hub'Eau).")
    a, b, c = st.columns(3)
    with a:
        etat.nombre("module", "Module (débit moyen) (m³/s)", 1.0, "%.1f", 0.1)
    with b:
        etat.nombre("T_reference", "Crue de référence de l'étude d'impact T (ans)", 1, None, 2, 10000, entier=True,
                    aide="Souvent la crue centennale ou la plus forte crue connue (PPRI).")
    with c:
        etat.nombre("T_chantier", "Crue de chantier T (ans)", 1, None, 2, 1000, entier=True)
    st.markdown("**Crues historiques** (facultatif) — elles seront ajoutées au tableau des résultats.")
    etat.tableau("crues_historiques", ["nom", "Q"], {
        "nom": st.column_config.TextColumn("Crue", required=True),
        "Q": st.column_config.NumberColumn("Débit de pointe (m³/s)", format="%.0f", required=True),
    }, requis=["nom", "Q"])

    st.subheader("Saisonnalité des crues pendant les travaux")
    sais = etat.choix("saisonnalite", "Répartition des crues dans l'année", ["uniforme", "personnalisee"],
                      {"uniforme": "Uniforme (prudent pour des travaux d'été)",
                       "personnalisee": "Poids mensuels (calculés page 3 ou saisis)"}, horizontal=True)
    if sais == "personnalisee":
        poids = list(P()["poids_mensuels"])
        df_p = pd.DataFrame([poids], columns=MOIS)
        k = f"w{st.session_state.get(etat.VERSION, 0)}_poids"
        ed = st.data_editor(df_p, key=k, hide_index=True)
        P()["poids_mensuels"] = [max(0.0, float(v)) if pd.notna(v) else 0.0 for v in ed.iloc[0].tolist()]
        st.caption("Poids relatifs (normalisés automatiquement) : part des crues survenant chaque mois.")
    zone_alea = st.container()

# ================================================================== critères
with onglets[3]:
    a, b = st.columns(2)
    with a:
        st.subheader("Critères d'acceptabilité")
        etat.nombre("seuil_dz", "Surélévation admissible (cm)", 0.5, "%.1f", 0.0, facteur=100.0,
                    aide="À fixer avec le service police de l'eau (DDT) ; souvent 1 à 5 cm sur les enjeux.")
        etat.nombre("proba_acceptable", "Probabilité acceptable pendant les travaux (%)", 0.5, "%.1f", 0.0, 100.0,
                    facteur=100.0)
        etat.nombre("vitesse_admissible", "Vitesse admissible (m/s)", 0.1, "%.2f", 0.0)
        etat.nombre("k_vitesse_locale", "Facteur de survitesse locale au nez du batardeau", 0.1, "%.2f", 1.0)
        etat.nombre("rho_enrochement", "Masse volumique des enrochements (kg/m³)", 50.0, "%.0f", 1100.0)
        etat.choix("C_isbash", "Coefficient d'Isbash", [0.86, 1.20],
                   {0.86: "0,86 – blocs exposés, forte turbulence", 1.20: "1,20 – blocs encastrés"})
        if etat.case("fond_affouillable", "Fond affouillable au droit des passes (pas de radier béton)"):
            etat.choix("k1_laursen", "Mode de transport (Laursen)", [0.59, 0.64, 0.69],
                       {0.59: "Charriage dominant", 0.64: "Mixte", 0.69: "Suspension dominante"})
    with b:
        st.subheader("Méthodes de calcul")
        etat.multichoix("methodes_actives", "Méthodes comparées", list(METHODES), METHODES)
        etat.choix("methode_ligne_eau", "Méthode retenue pour les résultats",
                   ["enveloppe"] + list(METHODES), commun.LIBELLES_METHODES)
        perso = etat.case("coefs_personnalises", "Coefficients personnalisés",
                          aide="Sinon, déduits des formes de piles et de nez de batardeau.")
        if not perso:
            for cle, forme in (("xi_ref", "forme_piles"), ("xi_bat", "forme_batardeau")):
                P()[cle] = FORMES[P()[forme]]["xi"]
            P()["K_yarnell_ref"] = FORMES[P()["forme_piles"]]["K_yarnell"]
            P()["K_yarnell_bat"] = FORMES[P()["forme_batardeau"]]["K_yarnell"]
            st.caption(f"ξ piles = {P()['xi_ref']}, ξ batardeau = {P()['xi_bat']}, "
                       f"K Yarnell piles = {P()['K_yarnell_ref']}, K Yarnell batardeau = {P()['K_yarnell_bat']}")
        else:
            c1, c2 = st.columns(2)
            with c1:
                etat.nombre("xi_ref", "ξ contraction – piles", 0.05, "%.2f", 0.0)
                etat.nombre("K_yarnell_ref", "K Yarnell – piles", 0.05, "%.2f", 0.5)
            with c2:
                etat.nombre("xi_bat", "ξ contraction – batardeau", 0.05, "%.2f", 0.0)
                etat.nombre("K_yarnell_bat", "K Yarnell – batardeau", 0.05, "%.2f", 0.5)
        c1, c2 = st.columns(2)
        with c1:
            etat.nombre("K_A", "Coefficient de d'Aubuisson K_A", 0.01, "%.2f", 0.5, 1.5,
                        aide="1,0 = perte totale de l'énergie cinétique ; littérature ≈ 0,87 à 1,07.")
        with c2:
            etat.nombre("mu", "Coefficient de seuil μ", 0.005, "%.3f", 0.2, 0.6,
                        aide="0,385 = seuil épais théorique ; μ noyé = 3√3/2 · μ.")
        etat.case("vitesse_approche_seuil", "Méthode D : tenir compte de la vitesse d'approche", bascule=False)

# ================================================================== compléments
with onglets[4]:
    a, b, c = st.columns(3)
    with a:
        st.subheader("Événement de crue")
        mode_hy = etat.choix("hydro_mode", "Hydrogramme", ["synthetique", "csv"],
                             {"synthetique": "Synthétique (forme de type SOCOSE)", "csv": "Importé (CSV)"})
        if mode_hy == "synthetique":
            etat.nombre("hydro_T", "Période de retour du pic (ans)", 1, None, 2, 1000, entier=True)
            etat.nombre("hydro_t_pic", "Durée de montée (h)", 6.0, "%.0f", 1.0)
            etat.nombre("hydro_duree", "Durée simulée (h)", 12.0, "%.0f", 12.0)
            etat.nombre("hydro_Qb", "Débit de base (m³/s)", 5.0, "%.0f", 0.0)
        else:
            fcsv = st.file_uploader("Hydrogramme CSV (date;débit ou heures;débit)", type=["csv", "txt"])
            if fcsv is not None:
                from batcrue.hydrogramme import lire_hydrogramme_csv
                try:
                    t, q = lire_hydrogramme_csv(fcsv.getvalue())
                    P()["hydro_csv"] = [[float(a_), float(b_)] for a_, b_ in zip(t, q)]
                    st.success(f"{len(t)} valeurs importées, pic {commun.fr(max(q), 0)} m³/s.")
                except ValueError as exc:
                    st.error(str(exc))
            elif not P().get("hydro_csv"):
                st.info("Aucun fichier importé : l'hydrogramme synthétique sera utilisé.")
    with b:
        st.subheader("Renard hydraulique")
        if etat.case("lane_applicable", "Batardeau fondé sur sol meuble",
                     aide="Palplanches ou remblai sur alluvions. Sans objet pour un batardeau posé sur radier béton."):
            etat.choix("sol_fondation", "Sol de fondation", list(COEFFICIENTS_LANE))
            etat.nombre("l_cheminement_v", "Cheminement vertical (m)", 0.5, "%.1f", 0.0,
                        aide="Ex. 2 × fiche des palplanches.")
            etat.nombre("l_cheminement_h", "Cheminement horizontal (m)", 0.5, "%.1f", 0.0)
    with c:
        st.subheader("Incertitudes")
        etat.nombre("incert_strickler", "Incertitude sur le Strickler (± %)", 1.0, "%.0f", 0.0, 80.0, facteur=100.0)
        etat.nombre("incert_debit", "Incertitude sur le débit (± %)", 1.0, "%.0f", 0.0, 80.0, facteur=100.0)
        etat.nombre("incert_aval", "Incertitude sur la cote aval (± m)", 0.05, "%.2f", 0.0)
        etat.nombre("mc_n", "Nombre de tirages Monte-Carlo", 50, None, 50, 5000, entier=True)

# ================================================================== contrôles et zones différées
with zone_alertes:
    bloque = commun.erreurs_bloquantes()
if bloque:
    st.stop()
e = commun.etude()
with zone_schema:
    st.markdown(f"Emprise du batardeau : **{commun.fr(e.largeur_obstruee, 1)} m**, soit "
                f"**{commun.fr(e.taux_obstruction * 100, 0)} %** de la largeur des passes "
                f"et {commun.fr(e.largeur_obstruee / float(P()['largeur_riviere']) * 100, 0)} % de la rivière.")
    st.plotly_chart(graphiques.schema_barrage(e, e.calcul_debit(e.Q_reference)), key="schema")
    st.caption(f"Vue de face depuis l'amont ; niveaux pour la crue de référence Q{int(P()['T_reference'])} "
               f"({commun.debit(e.Q_reference)}).")
with zone_alea:
    st.metric("Part de l'aléa annuel couverte par la période de travaux", commun.pct(e.fraction_alea, 0),
              help="1 an complet = 100 %. Sert au calcul des probabilités pendant les travaux.")

# ================================================================== calculs détaillés
st.divider()
st.header("🧮 Calculs détaillés (note de calcul)")
options = {f"Q{T} = {commun.debit(e.debit_T(T))}": e.debit_T(T) for T in PERIODES_RETOUR}
options[f"Crue de chantier Q{int(P()['T_chantier'])} = {commun.debit(e.Q_chantier)}"] = e.Q_chantier
options["Autre débit…"] = None
choix_q = st.selectbox("Débit pour la note de calcul", list(options), index=len(PERIODES_RETOUR) - 1)
q_note = options[choix_q]
if q_note is None:
    q_note = st.number_input("Débit (m³/s)", min_value=1.0, value=float(round(e.Q_reference)), step=10.0)
note_calcul.afficher(e, float(q_note))
