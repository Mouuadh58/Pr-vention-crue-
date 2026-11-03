"""Génération du rapport HTML (note de calcul imprimable) de l'étude d'impact.

Les graphiques sont produits par matplotlib en SVG avec des couleurs
« sentinelles » remplacées ensuite par des variables CSS : ils suivent ainsi
le thème clair ou sombre de la page et restent nets à l'impression.
"""
from __future__ import annotations

import html
import io
import math
from datetime import date

import numpy as np

from .ouvrage import FORMES, METHODES

# Couleurs sentinelles -> variables CSS
_SENTINELLES = {
    "#010101": "var(--encre)", "#020202": "var(--encre-2)", "#030303": "var(--filet)",
    "#101010": "var(--serie-1)", "#202020": "var(--serie-2)", "#303030": "var(--serie-3)",
    "#404040": "var(--serie-4)", "#505050": "var(--critique)", "#707070": "var(--lit)",
}
_COUL_METH = {"A": "#101010", "B": "#202020", "C": "#303030", "D": "#404040"}


def _f(x, n=2, unite=""):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    s = f"{x:,.{n}f}".replace(",", " ").replace(".", ",")
    return f"{s} {unite}" if unite else s


def _cm(x, n=1):
    return _f(None if x is None else x * 100, n, "cm")


def _pct(x, n=1):
    return _f(None if x is None else x * 100, n, "%")


def _T(T):
    if T is None or (isinstance(T, float) and math.isnan(T)):
        return "—"
    if math.isinf(T) or T > 1e4:
        return "> 10 000 ans"
    return f"≈ {_f(T, 0 if T >= 10 else 1)} ans"


def _e(t) -> str:
    return html.escape(str(t))


# ------------------------------------------------------------------ graphiques
def _figure(largeur=7.2, hauteur=3.4, lignes=1, ratios=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "svg.fonttype": "none", "font.family": "sans-serif", "font.size": 9,
        "text.color": "#010101", "axes.labelcolor": "#010101", "xtick.color": "#020202",
        "ytick.color": "#020202", "axes.edgecolor": "#020202", "grid.color": "#030303",
        "axes.grid": True, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": "none", "axes.facecolor": "none", "savefig.facecolor": "none",
        "legend.frameon": False, "axes.axisbelow": True,
    })
    if lignes == 1:
        fig, ax = plt.subplots(figsize=(largeur, hauteur))
        return fig, ax
    fig, axes = plt.subplots(lignes, 1, figsize=(largeur, hauteur), sharex=True,
                             gridspec_kw={"height_ratios": ratios or [1] * lignes, "hspace": 0.12})
    return fig, axes


def _svg(fig) -> str:
    import matplotlib.pyplot as plt
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    s = buf.getvalue()
    s = s[s.index("<svg"):]
    for k, v in _SENTINELLES.items():
        s = s.replace(k, v).replace(k.upper(), v)
    s = s.replace('width="', 'data-w="', 1).replace('height="', 'data-h="', 1)
    return s


def _virgule(ax):
    from matplotlib.ticker import FuncFormatter
    fmt = FuncFormatter(lambda v, _: f"{v:g}".replace(".", ","))
    ax.xaxis.set_major_formatter(fmt)
    ax.yaxis.set_major_formatter(fmt)


def _graphe_dz(etude, courbe, seuil):
    fig, ax = _figure()
    for m in etude.methodes:
        y = np.where(courbe[f"valide_{m}"].to_numpy().astype(bool), courbe[f"dZ_{m}"] * 100, np.nan)
        ax.plot(courbe["Q"], y, color=_COUL_METH[m], lw=1.6, label=f"{m} · {METHODES[m]}")
    ax.plot(courbe["Q"], courbe["dZ_enveloppe"] * 100, color="#010101", lw=2.6, label="Enveloppe retenue")
    ax.axhline(seuil * 100, color="#505050", lw=1.2, ls="--")
    ax.text(courbe["Q"].iloc[0], seuil * 100, f" seuil {seuil * 100:.0f} cm", color="#505050", va="bottom", fontsize=8)
    for T in (2, 10, 100):
        q = etude.debit_T(T)
        ax.axvline(q, color="#020202", lw=0.7, ls=":")
        ax.text(q, ax.get_ylim()[1], f"Q{T}", ha="center", va="bottom", fontsize=8, color="#020202")
    ax.set_xlabel("Débit Q (m³/s)")
    ax.set_ylabel("Surélévation au barrage (cm)")
    ax.legend(loc="upper left", fontsize=8)
    _virgule(ax)
    return _svg(fig)


def _graphe_ligne(le, enjeux, seuil):
    fig, (a1, a2) = _figure(7.2, 4.6, 2, [2.2, 1])
    xk = le["x"] / 1000
    a1.fill_between(xk, le["z_fond"].min() - 1, le["z_fond"], color="#707070", lw=0)
    if np.isfinite(le["z_berge"]).all():
        a1.plot(xk, le["z_berge"], color="#020202", lw=1, ls=":", label="Haut de berge")
    a1.plot(xk, le["Z_sans"], color="#101010", lw=1.8, label="Sans batardeau")
    a1.plot(xk, le["Z_avec"], color="#202020", lw=1.8, label="Avec batardeau")
    if enjeux is not None and not enjeux.empty:
        a1.scatter(enjeux["x"] / 1000, enjeux["Z_avec"], marker="D", s=22, color="#010101", zorder=5)
        for _, r in enjeux.iterrows():
            a1.annotate(str(r["enjeu"]), (r["x"] / 1000, r["Z_avec"]), textcoords="offset points",
                        xytext=(0, 7), ha="center", fontsize=7.5)
    a1.set_ylabel("Cote (m NGF)")
    a1.legend(loc="upper left", fontsize=8, ncol=3)
    bas_eau = float(le["Z_sans"].min())
    if np.isfinite(le["z_berge"]).all():
        bas_eau = min(bas_eau, float(le["z_berge"].min()))
    a1.set_ylim(max(float(le["z_fond"].min()) - 0.3, bas_eau - 1.2), float(le["Z_avec"].max()) + 0.9)
    a2.plot(xk, le["dZ"] * 100, color="#202020", lw=1.8)
    a2.axhline(seuil * 100, color="#505050", lw=1.1, ls="--")
    a2.set_ylim(bottom=0)
    a2.set_ylabel("ΔZ (cm)")
    a2.set_xlabel("Distance vers l'amont depuis le barrage (km)")
    _virgule(a1)
    _virgule(a2)
    return _svg(fig)


def _graphe_risque(etude, s):
    fig, ax = _figure(7.2, 3.0)
    q = np.linspace(max(1.0, 0.5 * etude.debit_T(2)), 1.3 * etude.debit_T(100), 200)
    ax.plot(q, [etude.proba_travaux(v) * 100 for v in q], color="#101010", lw=1.8)
    for nom, qv in (("seuil d'impact", s["Q_seuil"]), ("alerte", s["Q_alerte"]), ("submersion", s["Q_submersion"])):
        if qv:
            pv = etude.proba_travaux(qv) * 100
            ax.scatter([qv], [pv], color="#010101", s=18, zorder=5)
            ax.annotate(f"{nom}\n{pv:.1f} %".replace(".", ","), (qv, pv), textcoords="offset points",
                        xytext=(8, 6), fontsize=7.5)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Débit Q (m³/s)")
    ax.set_ylabel("Probabilité pendant les travaux (%)")
    _virgule(ax)
    return _svg(fig)


# ------------------------------------------------------------------ tableaux
def _table(entetes, lignes, classes=None) -> str:
    th = "".join(f"<th>{_e(h)}</th>" for h in entetes)
    corps = []
    for ligne in lignes:
        tds = "".join(f'<td class="{(classes or [""] * len(ligne))[i]}">{v}</td>' for i, v in enumerate(ligne))
        corps.append(f"<tr>{tds}</tr>")
    return f'<div class="tableau"><table><thead><tr>{th}</tr></thead><tbody>{"".join(corps)}</tbody></table></div>'


def _paires(paires) -> str:
    return '<dl class="paires">' + "".join(f"<div><dt>{_e(k)}</dt><dd>{v}</dd></div>" for k, v in paires) + "</dl>"


# ------------------------------------------------------------------ styles
_STYLE = """
/* Note de calcul : une colonne de lecture (~68 caractères), tableaux et figures pleine largeur. */
:root {
  --papier: #ffffff; --voile: #f2f6f8; --encre: #12202a; --encre-2: #4a5965; --filet: #d5dee4; --lit: #e2e7ea;
  --riviere: #0d5f80; --batardeau: #bf4f1b; --bon: #0a7a32; --vigilance: #9a5b00; --critique: #b3261e;
  --serie-1: #2a78d6; --serie-2: #eb6834; --serie-3: #1baf7a; --serie-4: #eda100;
  --f-titre: "IBM Plex Sans Condensed", "Roboto Condensed", "Arial Narrow", sans-serif;
  --f-texte: "IBM Plex Sans", "Segoe UI", system-ui, -apple-system, sans-serif;
  --f-donnee: "IBM Plex Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --papier: #0e161c; --voile: #15212a; --encre: #e4ecf1; --encre-2: #a8b6c0; --filet: #2a3944; --lit: #24323c;
  --riviere: #5bb4d8; --batardeau: #ef8d58; --bon: #44c271; --vigilance: #e2a53c; --critique: #f07a72;
  --serie-1: #3987e5; --serie-2: #d95926; --serie-3: #199e70; --serie-4: #c98500; color-scheme: dark; } }
:root[data-theme="dark"] {
  --papier: #0e161c; --voile: #15212a; --encre: #e4ecf1; --encre-2: #a8b6c0; --filet: #2a3944; --lit: #24323c;
  --riviere: #5bb4d8; --batardeau: #ef8d58; --bon: #44c271; --vigilance: #e2a53c; --critique: #f07a72;
  --serie-1: #3987e5; --serie-2: #d95926; --serie-3: #199e70; --serie-4: #c98500; color-scheme: dark; }
* { box-sizing: border-box; }
body { background: var(--papier); color: var(--encre); font: 15px/1.6 var(--f-texte); margin: 0; }
.page { max-width: 62rem; margin: 0 auto; padding-block: 2.5rem 4rem;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 2.25rem; }
header.entete { display: grid; gap: .6rem; border-bottom: 2px solid var(--encre); padding-bottom: 1.25rem; }
.surtitre { font: 600 .74rem/1.2 var(--f-donnee); letter-spacing: .12em; text-transform: uppercase; color: var(--riviere); }
h1 { font: 700 clamp(1.7rem, 4vw, 2.5rem)/1.08 var(--f-titre); margin: 0; text-wrap: balance; letter-spacing: -.01em; }
h2 { font: 700 1.35rem/1.2 var(--f-titre); margin: 0; text-wrap: balance; display: flex; gap: .6rem; align-items: baseline; }
h2 .num { font: 600 .9rem var(--f-donnee); color: var(--riviere); }
h3 { font: 600 1rem/1.3 var(--f-texte); margin: 0; }
section { display: grid; gap: 1rem; min-width: 0; }
p { margin: 0; max-width: 68ch; }
.meta { display: flex; flex-wrap: wrap; gap: .4rem 1.4rem; color: var(--encre-2); font-size: .88rem; }
.statut { display: inline-flex; align-items: center; gap: .45rem; font: 600 .82rem var(--f-texte); padding: .3rem .7rem;
  border-radius: 999px; border: 1.5px solid currentColor; width: fit-content; }
.statut.ok { color: var(--bon); } .statut.attention { color: var(--vigilance); } .statut.non_conforme { color: var(--critique); }
.verdict { border-left: 4px solid var(--critique); background: var(--voile); padding: 1rem 1.2rem; display: grid; gap: .5rem; }
.verdict.ok { border-left-color: var(--bon); } .verdict.attention { border-left-color: var(--vigilance); }
.chiffres { display: grid; grid-template-columns: repeat(auto-fit, minmax(13rem, 1fr)); gap: 1px; background: var(--filet);
  border: 1px solid var(--filet); }
.chiffres > div { background: var(--papier); padding: .9rem 1rem; display: grid; gap: .2rem; align-content: start; }
.chiffres .lib { font-size: .78rem; color: var(--encre-2); }
.chiffres .val { font: 600 1.45rem/1.15 var(--f-titre); }
.chiffres .sous { font-size: .78rem; color: var(--encre-2); }
.paires { display: grid; grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr)); gap: 0 2rem; margin: 0; }
.paires > div { display: flex; justify-content: space-between; gap: 1rem; padding: .38rem 0; border-bottom: 1px solid var(--filet); }
.paires dt { color: var(--encre-2); } .paires dd { margin: 0; font-family: var(--f-donnee); font-size: .9rem; text-align: right;
  font-variant-numeric: tabular-nums; }
.tableau { overflow-x: auto; border: 1px solid var(--filet); }
table { border-collapse: collapse; width: 100%; font-size: .86rem; }
th { text-align: left; font: 600 .74rem var(--f-texte); color: var(--encre-2); text-transform: uppercase; letter-spacing: .04em;
  background: var(--voile); padding: .5rem .6rem; border-bottom: 1px solid var(--filet); white-space: nowrap; }
td { padding: .42rem .6rem; border-bottom: 1px solid var(--filet); font-variant-numeric: tabular-nums; white-space: nowrap; }
td.n { text-align: right; font-family: var(--f-donnee); font-size: .84rem; }
tbody tr:last-child td { border-bottom: 0; }
.graphe { border: 1px solid var(--filet); padding: .75rem; overflow-x: auto; }
.graphe svg { width: 100%; height: auto; max-width: 100%; display: block; }
.graphe svg text { font-family: var(--f-texte) !important; }
figcaption { font-size: .82rem; color: var(--encre-2); margin-top: .4rem; }
figure { margin: 0; min-width: 0; }
.formule { font-family: var(--f-donnee); font-size: .88rem; background: var(--voile); padding: .55rem .8rem; overflow-x: auto;
  white-space: nowrap; }
ul { margin: 0; padding-left: 1.2rem; display: grid; gap: .35rem; max-width: 72ch; }
.note { font-size: .82rem; color: var(--encre-2); }
footer { border-top: 1px solid var(--filet); padding-top: 1rem; font-size: .8rem; color: var(--encre-2); }
@media print { body { font-size: 11pt; } .page { padding: 0; gap: 1.4rem; } section { break-inside: avoid-page; }
  .graphe, .tableau { break-inside: avoid; } }
"""


# ------------------------------------------------------------------ rapport
def generer_html(etude, s: dict, courbe, tableau, document_complet: bool = True) -> str:
    p = etude.p
    seuil = float(p["seuil_dz"])
    T_ref = int(p["T_reference"])
    d0, d1 = etude.dates_travaux
    le = s["ligne_eau"]
    enj = s["enjeux"]
    statut_lib = {"ok": "Impact acceptable", "attention": "Acceptable sous conditions",
                  "non_conforme": "Mesures nécessaires"}[s["niveau"]]
    symbole = {"ok": "✓", "attention": "!", "non_conforme": "✕"}[s["niveau"]]
    methode = p["methode_ligne_eau"]
    lib_methode = "enveloppe des méthodes valides" if methode == "enveloppe" else METHODES.get(methode, methode)
    sens = etude.sensibilite(methode=methode)

    chiffres = [
        (f"Surélévation au barrage, Q{T_ref}", _cm(s["dZ_barrage"]), f"{_f(s['Q_reference'], 0, 'm³/s')} · {lib_methode}"),
        ("Surélévation maximale aux enjeux", _cm(s["dZ_enjeux_max"]),
         f"influence ≥ 1 cm sur {_f(s['distance_influence'] / 1000, 1, 'km')}"),
        (f"Débit où ΔZ atteint {seuil * 100:.0f} cm", _f(s["Q_seuil"], 0, "m³/s") if s["Q_seuil"] else "jamais atteint",
         f"période de retour {_T(s['T_seuil'])}"),
        ("Probabilité pendant les travaux", _pct(s["P_seuil"]), f"du {d0:%d/%m/%Y} au {d1:%d/%m/%Y}"),
        ("Submersion du batardeau", _f(s["Q_submersion"], 0, "m³/s") if s["Q_submersion"] else "non atteinte",
         f"{_T(s['T_submersion'])} · probabilité {_pct(s['P_submersion'])}"),
        ("Vitesse dans les passes", _f(s["erosion"]["V_passes_avec"], 2, "m/s"),
         f"contre {_f(s['erosion']['V_passes_sans'], 2, 'm/s')} sans batardeau"),
    ]
    html_chiffres = "".join(f'<div><span class="lib">{_e(a)}</span><span class="val">{b}</span>'
                            f'<span class="sous">{c}</span></div>' for a, b, c in chiffres)

    passes = _table(["Passe", "Largeur", "Cote du seuil", "Part obstruée"],
                    [[_e(x["nom"]), _f(x["largeur"], 2, "m"), _f(x["cote_seuil"], 2, "m NGF"), _pct(x["obstruction"], 0)]
                     for x in etude.passes], ["", "n", "n", "n"])
    donnees_barrage = _paires([
        ("Largeur hydraulique au droit du barrage", _f(p["largeur_riviere"], 2, "m")),
        ("Cote du fond", _f(p["cote_fond"], 2, "m NGF")),
        ("Retenue normale amont", _f(p["rn_amont"], 2, "m NGF") if p["regulation"] else "sans régulation"),
        ("Forme des piles", _e(FORMES[p["forme_piles"]]["libelle"])),
        ("Batardeau", _e(p["type_batardeau"])),
        ("Emprise", f"{_f(etude.largeur_obstruee, 1, 'm')} · {_pct(etude.taux_obstruction, 0)} des passes"),
        ("Cote de crête / revanche", f"{_f(p['cote_arase'], 2, 'm NGF')} / {_f(p['revanche'], 2, 'm')}"),
        ("Période d'installation", f"{d0:%d/%m/%Y} → {d1:%d/%m/%Y}"),
    ])
    if p["mode_bief"] == "prismatique":
        bief = [("Lit mineur", f"b = {_f(p['b_min'], 1, 'm')}, fruit {_f(p['m_berge'], 1)}, berge {_f(p['h_berge'], 2, 'm')}"),
                ("Lit majeur actif", _f(p["B_maj"], 0, "m")),
                ("Strickler mineur / majeur", f"{_f(p['K_min'], 0)} / {_f(p['K_maj'], 0)} m¹ᐟ³/s")]
    else:
        bief = [("Géométrie", f"{len(p['sections_tabulees'])} profils en travers tabulés")]
    bief += [("Pente moyenne", f"{_f(p['pente'] * 1000, 2)} m/km"),
             ("Longueur étudiée", _f(p["longueur_bief"] / 1000, 1, "km")),
             ("Condition aval", {"normale": "hauteur normale (Strickler)", "tableau": "loi hauteur-débit mesurée",
                                 "constante": "cote imposée"}[p["mode_aval"]]),
             ("Loi des crues (Gumbel)", f"u = {_f(etude.gumbel.u, 1)} · β = {_f(etude.gumbel.beta, 1)} m³/s"),
             (f"Crue de référence Q{T_ref}", _f(s["Q_reference"], 0, "m³/s")),
             (f"Crue de chantier Q{int(p['T_chantier'])}", _f(s["Q_chantier"], 0, "m³/s")),
             ("Surélévation admissible", _f(seuil * 100, 1, "cm"))]
    donnees_bief = _paires(bief)

    lignes_T = []
    for _, r in tableau.iterrows():
        lignes_T.append([_e(r["evenement"]), _f(r["Q"], 0), _pct(r["P_travaux"]), _f(r["Z_aval"], 2), _f(r["Z_amont_sans"], 2),
                         _f(r["Z_amont_avec"], 2)] + [_f(r[f"dZ_{m}"] * 100, 1) for m in etude.methodes]
                        + [f"<strong>{_f(r['dZ_enveloppe'] * 100, 1)}</strong>", _f(r["V_passes_avec"], 2)])
    table_T = _table(["Crue", "Q m³/s", "P travaux", "Z aval", "Z amont sans", "Z amont avec"]
                     + [f"ΔZ {m} cm" for m in etude.methodes] + ["ΔZ retenu cm", "V passes m/s"], lignes_T,
                     [""] + ["n"] * (7 + len(etude.methodes)))
    if enj is not None and not enj.empty:
        table_enj = _table(["Enjeu", "Distance", "Z sans", "Z avec", "ΔZ", "Premiers dommages"],
                           [[_e(r["enjeu"]), _f(r["x"] / 1000, 2, "km"), _f(r["Z_sans"], 2), _f(r["Z_avec"], 2),
                             _cm(r["dZ"]), (_f(r["cote_dommages"], 2) + (" · atteinte avec batardeau" if r["inonde_avec"]
                                                                       and not r["inonde_sans"] else
                                                                       " · déjà atteinte sans" if r["inonde_sans"] else ""))
                             if np.isfinite(r["cote_dommages"]) else "—"] for _, r in enj.iterrows()],
                           ["", "n", "n", "n", "n", ""])
    else:
        table_enj = '<p class="note">Aucun enjeu déclaré.</p>'
    table_sens = _table(["Paramètre", "ΔZ bas", "ΔZ haut"],
                        [[_e(r["parametre"]), _cm(r["dZ_bas"]), _cm(r["dZ_haut"])]
                         for _, r in sens.sort_values("ecart_max", ascending=False).iterrows()], ["", "n", "n"])
    ef = etude.efforts(s["Q_reference"])
    er = s["erosion"]

    if s["niveau"] == "ok":
        mesures = ["Informer le service police de l'eau avec la présente note et les hypothèses retenues.",
                   "Suivre les prévisions Vigicrues pendant toute la durée d'installation.",
                   "Vérifier la tenue du batardeau aux efforts calculés (note du fournisseur)."]
    else:
        mesures = [f"Prévoir une procédure de retrait ou d'effacement du batardeau déclenchée avant "
                   f"{_f(s['Q_seuil'], 0, 'm³/s')} (prévisions Vigicrues, délai de manœuvre à vérifier).",
                   "Tester une emprise réduite ou un phasage des travaux (page « Variantes d'emprise » de l'outil).",
                   "Placer l'installation en période de basses eaux et quantifier la saisonnalité réelle des crues "
                   "à partir des chroniques de la station (Hub'Eau).",
                   "Confirmer les résultats avec le modèle hydraulique de référence de la vallée (PPRI, Entente Oise-Aisne) "
                   "en y insérant le batardeau.",
                   "Définir avec le service police de l'eau le seuil d'impact admissible sur les enjeux."]

    graphe_dz = _graphe_dz(etude, courbe, seuil)
    graphe_ligne = _graphe_ligne(le, enj, seuil)
    graphe_risque = _graphe_risque(etude, s)
    q_txt = _f(s["Q_reference"], 0, "m³/s")

    corps = f"""
<div class="page">
<header class="entete">
  <span class="surtitre">Note de calcul · impact hydraulique d'un batardeau</span>
  <h1>{_e(p['nom_projet'])}</h1>
  <div class="meta"><span>{_e(p['nom_barrage'])}</span><span>Édition du {date.today():%d/%m/%Y}</span>
  {f"<span>{_e(p['auteur'])}</span>" if p.get('auteur') else ""}<span>BatCrue 1.0</span></div>
  <span class="statut {s['niveau']}" role="status"><span aria-hidden="true">{symbole}</span>Pré-diagnostic : {statut_lib}</span>
</header>

<section aria-labelledby="t-synthese">
  <h2 id="t-synthese"><span class="num">1</span>Synthèse</h2>
  <div class="verdict {s['niveau']}"><p><strong>{_e(statut_lib)}.</strong> {_e(s['verdict'])}</p></div>
  <div class="chiffres">{html_chiffres}</div>
  <p class="note">{_e(p.get('commentaire', ''))}</p>
</section>

<section aria-labelledby="t-objet">
  <h2 id="t-objet"><span class="num">2</span>Objet et contexte</h2>
  <p>Le batardeau isole {_pct(etude.taux_obstruction, 0)} de la largeur des passes du barrage pendant
  {(d1 - d0).days + 1} jours. En crue, lorsque toutes les vannes sont ouvertes, il réduit la section
  d'écoulement et surélève la ligne d'eau à l'amont. La présente note quantifie cette surélévation pour
  toute la gamme de débits, sa propagation vers l'amont et la probabilité qu'elle survienne pendant les travaux.</p>
  <p>Un ouvrage temporaire placé dans le lit mineur et faisant obstacle à l'écoulement des crues relève de la
  rubrique 3.1.1.0 de la nomenclature « loi sur l'eau » (article R.214-1 du code de l'environnement) ; le régime
  applicable et le seuil d'impact admissible sont à confirmer avec le service police de l'eau.</p>
</section>

<section aria-labelledby="t-donnees">
  <h2 id="t-donnees"><span class="num">3</span>Données d'entrée</h2>
  <h3>Barrage et batardeau</h3>{donnees_barrage}{passes}
  <h3>Rivière et hydrologie</h3>{donnees_bief}
</section>

<section aria-labelledby="t-methodes">
  <h2 id="t-methodes"><span class="num">4</span>Méthodes</h2>
  <p>Calcul en régime permanent au débit de pointe. La cote aval Z₃ est imposée par la hauteur normale de
  Manning-Strickler (ou la loi hauteur-débit mesurée), au moins égale à la retenue du bief aval. La cote amont, vannes
  ouvertes, est calculée sans puis avec batardeau par quatre méthodes indépendantes ; la cote réelle vaut
  max(RN ; Z₁) tant que le barrage régule.</p>
  <div class="formule">A · Bernoulli + Borda-Carnot : Z₂ + V₂²/2g = E₃ + (V₂ − V₃)²/2g ; E₁ = E₂ + ξ (V₂² − V₁²)/2g ; contrôle critique si étranglement</div>
  <div class="formule">B · Yarnell (1934) : Δh = 2K (K + 10ω − 0,6)(α + 15α⁴) V₃²/2g</div>
  <div class="formule">C · d'Aubuisson (1840) : Q = K_A · Σ bᵢ (Z₃ − z_s,i) · √(2g Δh + V₁²)</div>
  <div class="formule">D · Seuils : dénoyé Q = μ b √(2g) h₁^1,5 ; noyé Q = μ_s b h₂ √(2g (h₁ − h₂)), μ_s = 3√3/2 · μ</div>
  <p>La surélévation retenue est l'{_e(lib_methode)}. Elle est propagée vers l'amont par la méthode des pas
  standards (courbe de remous). Les probabilités pendant les travaux supposent des crues poissonniennes de taux
  λ(Q) = exp(−(Q − u)/β), pondéré par la part de l'aléa annuel couverte par la période d'installation
  ({_pct(s['fraction_alea'], 0)}).</p>
</section>

<section aria-labelledby="t-resultats">
  <h2 id="t-resultats"><span class="num">5</span>Résultats</h2>
  <figure><div class="graphe">{graphe_dz}</div>
  <figcaption>Surélévation au barrage selon le débit, par méthode. L'impact est nul tant que le barrage tient sa
  retenue normale ({_f(s['Q_effacement_avec'], 0, 'm³/s')} avec batardeau, {_f(s['Q_effacement_sans'], 0, 'm³/s')} sans).</figcaption></figure>
  {table_T}
  <p class="note">Cotes en m NGF. « P travaux » : probabilité qu'au moins une crue atteigne ce débit pendant l'installation.</p>
  <figure><div class="graphe">{graphe_ligne}</div>
  <figcaption>Lignes d'eau pour Q{T_ref} = {q_txt}, sans et avec batardeau, et surélévation le long du bief.</figcaption></figure>
  {table_enj}
</section>

<section aria-labelledby="t-risque">
  <h2 id="t-risque"><span class="num">6</span>Risque pendant les travaux</h2>
  <figure><div class="graphe">{graphe_risque}</div>
  <figcaption>Probabilité qu'au moins une crue dépasse le débit Q pendant la période d'installation.</figcaption></figure>
  {_paires([("Atteinte du seuil d'impact", f"{_f(s['Q_seuil'], 0, 'm³/s') if s['Q_seuil'] else '—'} · {_pct(s['P_seuil'])}"),
            ("Cote d'alerte (crête − revanche)", f"{_f(s['Q_alerte'], 0, 'm³/s') if s['Q_alerte'] else '—'} · {_pct(s['P_alerte'])}"),
            ("Submersion du batardeau", f"{_f(s['Q_submersion'], 0, 'm³/s') if s['Q_submersion'] else '—'} · {_pct(s['P_submersion'])}"),
            (f"Crue de chantier Q{int(p['T_chantier'])}", f"{_f(s['Q_chantier'], 0, 'm³/s')} · {_pct(s['P_chantier'])}")])}
</section>

<section aria-labelledby="t-ouvrage">
  <h2 id="t-ouvrage"><span class="num">7</span>Vitesses, protection et efforts (ordres de grandeur)</h2>
  {_paires([("Vitesse dans les passes sans → avec", f"{_f(er['V_passes_sans'], 2)} → {_f(er['V_passes_avec'], 2)} m/s"),
            ("Vitesse locale au nez du batardeau", _f(er["V_locale"], 2, "m/s")),
            ("Blocs stables (Isbash)", f"{_f(er['D_isbash'], 2, 'm')} · {_f(er['M_bloc'], 0, 'kg')}"),
            ("Poussée hydrostatique", _f(ef["F_hydro"] / 1000, 0, "kN/m")),
            ("Supplément dynamique", _f(ef["F_dyn"] / 1000, 1, "kN/m")),
            ("Batardeau submergé à Q" + str(T_ref), "oui" if ef["submerge"] else "non")])}
  <p class="note">Ces valeurs ne remplacent ni la note de calcul du fournisseur du batardeau ni l'étude géotechnique.</p>
</section>

<section aria-labelledby="t-sens">
  <h2 id="t-sens"><span class="num">8</span>Sensibilité</h2>
  <p>Surélévation au barrage pour Q{T_ref} quand un seul paramètre varie (valeur de base {_cm(sens.attrs.get('base'))}).</p>
  {table_sens}
</section>

<section aria-labelledby="t-conclusion">
  <h2 id="t-conclusion"><span class="num">9</span>Conclusions et suites à donner</h2>
  <ul>{"".join(f"<li>{_e(m)}</li>" for m in mesures)}</ul>
  <h3>Limites</h3>
  <ul><li>Calcul monodimensionnel en régime permanent, au débit de pointe (hypothèse majorante pour une crue lente).</li>
  <li>Tout le débit transite par les passes du barrage ; un écoulement par le lit majeur autour de l'ouvrage réduirait l'impact.</li>
  <li>Les données d'entrée conditionnent le résultat : géométrie, loi aval et statistique des crues sont à valider.</li>
  <li>Outil de pré-diagnostic : il ne remplace pas une modélisation hydraulique calée sur la vallée.</li></ul>
</section>

<footer>Généré par BatCrue 1.0, outil libre d'étude de l'impact hydraulique des batardeaux. Résultats à valider par un
ingénieur hydraulicien.</footer>
</div>"""

    titre = "Note de calcul BatCrue"
    tete = (f'<title>{titre}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600'
            '&family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;600&display=swap">\n'
            f"<style>{_STYLE}</style>")
    if not document_complet:
        return tete + corps
    return ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f"{tete}\n</head>\n<body>{corps}\n</body>\n</html>\n")
