"""Figures Plotly de l'application (une seule échelle verticale par graphique)."""
from __future__ import annotations

import math

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from batcrue.ouvrage import METHODES
from ui.commun import couleur_methode, palette


def _mise_en_page(fig: go.Figure, hauteur: int = 430, titre_x: str | None = None,
                  titre_y: str | None = None) -> go.Figure:
    fig.update_layout(separators=", ", hovermode="x unified", height=hauteur,
                      margin=dict(l=10, r=10, t=56, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                                  title_text=""))
    if titre_x:
        fig.update_xaxes(title_text=titre_x)
    if titre_y:
        fig.update_yaxes(title_text=titre_y)
    return fig


def _seuil_h(fig, y, texte, couleur, row=None, col=None, dash="dash", position="top left"):
    kw = {} if row is None else {"row": row, "col": col}
    fig.add_hline(y=y, line=dict(color=couleur, width=1.5, dash=dash), annotation_text=texte,
                  annotation_position=position, annotation_font_size=11, **kw)


def _reperes_debits(fig, etude, pal):
    for T in (2, 10, 100):
        q = etude.debit_T(T)
        fig.add_vline(x=q, line=dict(color=pal["discret"], width=1, dash="dot"),
                      annotation_text=f"Q{T}", annotation_position="top", annotation_font_size=10)


# ---------------------------------------------------------------- ΔZ(Q)
def dz_debit(courbe, etude, methodes, seuil_m: float) -> go.Figure:
    pal = palette()
    fig = go.Figure()
    for m in methodes:
        y = courbe[f"dZ_{m}"].to_numpy() * 100
        ok = courbe[f"valide_{m}"].to_numpy().astype(bool)
        fig.add_trace(go.Scatter(x=courbe["Q"], y=np.where(ok, y, np.nan), mode="lines",
                                 name=f"{m} · {METHODES[m]}", legendgroup=m,
                                 line=dict(color=couleur_methode(m), width=2),
                                 hovertemplate="%{y:.1f} cm"))
        if (~ok).any():
            fig.add_trace(go.Scatter(x=courbe["Q"], y=np.where(~ok, y, np.nan), mode="lines",
                                     name=f"{m} hors domaine", legendgroup=m, showlegend=False,
                                     line=dict(color=couleur_methode(m), width=1.5, dash="dot"),
                                     hovertemplate="%{y:.1f} cm (hors domaine)"))
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["dZ_enveloppe"] * 100, mode="lines",
                             name="Enveloppe retenue", line=dict(color=pal["encre"], width=3),
                             hovertemplate="<b>%{y:.1f} cm</b>"))
    _seuil_h(fig, seuil_m * 100, f"Seuil admissible {seuil_m * 100:.0f} cm", pal["critique"])
    _reperes_debits(fig, etude, pal)
    return _mise_en_page(fig, 450, "Débit Q (m³/s)", "Surélévation au barrage ΔZ (cm)")


# ---------------------------------------------------------------- cotes au barrage
def cotes_debit(courbe, etude) -> go.Figure:
    pal = palette()
    p = etude.p
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["Z_aval"], name="Cote aval Z3", mode="lines",
                             line=dict(color=pal["discret"], width=2), hovertemplate="%{y:.2f} m NGF"))
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["Z_amont_sans"], name="Amont sans batardeau",
                             mode="lines", line=dict(color=pal["serie"][0], width=2),
                             hovertemplate="%{y:.2f} m NGF"))
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["Z_amont_avec"], name="Amont avec batardeau",
                             mode="lines", line=dict(color=pal["serie"][1], width=2),
                             hovertemplate="%{y:.2f} m NGF"))
    if p["regulation"]:
        _seuil_h(fig, float(p["rn_amont"]), "Retenue normale amont", pal["discret"], dash="dot",
                 position="bottom right")
    _seuil_h(fig, float(p["cote_arase"]), "Crête du batardeau", pal["critique"])
    _seuil_h(fig, float(p["cote_arase"]) - float(p["revanche"]), "Crête − revanche (alerte)",
             pal["encre2"], dash="dot", position="bottom left")
    _reperes_debits(fig, etude, pal)
    return _mise_en_page(fig, 450, "Débit Q (m³/s)", "Cote (m NGF)")


# ---------------------------------------------------------------- ligne d'eau
def ligne_eau(df, enjeux, seuil_m: float, afficher_normale: bool = True) -> go.Figure:
    pal = palette()
    xk = df["x"] / 1000.0
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.68, 0.32], vertical_spacing=0.06)
    bas = float(df["z_fond"].min()) - 1.0
    fig.add_trace(go.Scatter(x=xk, y=np.full(len(df), bas), mode="lines", line=dict(width=0),
                             showlegend=False, hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=xk, y=df["z_fond"], name="Fond du lit", mode="lines", fill="tonexty",
                             fillcolor=pal["fond_lit"], line=dict(color=pal["discret"], width=1),
                             hovertemplate="%{y:.2f} m"), row=1, col=1)
    if np.isfinite(df["z_berge"]).all():
        fig.add_trace(go.Scatter(x=xk, y=df["z_berge"], name="Haut de berge", mode="lines",
                                 line=dict(color=pal["discret"], width=1.5, dash="dot"),
                                 hovertemplate="%{y:.2f} m"), row=1, col=1)
    if afficher_normale and "Z_normale" in df and np.isfinite(df["Z_normale"]).all():
        fig.add_trace(go.Scatter(x=xk, y=df["Z_normale"], name="Régime uniforme (sans barrage)",
                                 mode="lines", line=dict(color=pal["encre2"], width=1, dash="dash"),
                                 hovertemplate="%{y:.2f} m"), row=1, col=1)
    fig.add_trace(go.Scatter(x=xk, y=df["Z_sans"], name="Sans batardeau", mode="lines",
                             line=dict(color=pal["serie"][0], width=2), hovertemplate="%{y:.3f} m"),
                  row=1, col=1)
    fig.add_trace(go.Scatter(x=xk, y=df["Z_avec"], name="Avec batardeau", mode="lines",
                             line=dict(color=pal["serie"][1], width=2), hovertemplate="%{y:.3f} m"),
                  row=1, col=1)
    if enjeux is not None and not enjeux.empty:
        x_max = float(df["x"].max()) or 1.0
        positions = ["top left" if x > 0.85 * x_max else "top right" if x < 0.1 * x_max else "top center"
                     for x in enjeux["x"]]
        fig.add_trace(go.Scatter(x=enjeux["x"] / 1000.0, y=enjeux["Z_avec"], mode="markers+text",
                                 name="Enjeux", text=enjeux["enjeu"], textposition=positions,
                                 textfont=dict(size=11),
                                 marker=dict(size=9, color=pal["encre"], symbol="diamond",
                                             line=dict(width=2, color="rgba(255,255,255,0.9)")),
                                 hovertemplate="%{text}<br>%{y:.2f} m NGF<extra></extra>"), row=1, col=1)
        cd = enjeux[np.isfinite(enjeux["cote_dommages"])]
        if not cd.empty:
            fig.add_trace(go.Scatter(x=cd["x"] / 1000.0, y=cd["cote_dommages"], mode="markers",
                                     name="Cote de premiers dommages",
                                     marker=dict(size=9, color=pal["critique"], symbol="line-ew-open",
                                                 line=dict(width=3, color=pal["critique"])),
                                     hovertemplate="Dommages dès %{y:.2f} m NGF<extra></extra>"),
                          row=1, col=1)
    fig.add_trace(go.Scatter(x=xk, y=df["dZ"] * 100, name="ΔZ", mode="lines", showlegend=False,
                             line=dict(color=pal["serie"][1], width=2), hovertemplate="%{y:.1f} cm"),
                  row=2, col=1)
    _seuil_h(fig, seuil_m * 100, f"Seuil {seuil_m * 100:.0f} cm", pal["critique"], row=2, col=1)
    fig.update_xaxes(title_text="Distance vers l'amont depuis le barrage (km)", row=2, col=1)
    fig.update_yaxes(rangemode="tozero", title_text="ΔZ (cm)", row=2, col=1)
    # Cadrage sur la surface libre : le fond n'apparaît que s'il est proche de la ligne d'eau.
    berge = df["z_berge"].to_numpy()
    bas_eau = float(df["Z_sans"].min())
    if np.isfinite(berge).all():
        bas_eau = min(bas_eau, float(berge.min()))
    zmin = max(float(df["z_fond"].min()) - 0.3, bas_eau - 1.2)
    zmax = float(df["Z_avec"].max()) + 0.7
    fig.update_yaxes(range=[zmin, zmax], title_text="Cote (m NGF)", row=1, col=1)
    return _mise_en_page(fig, 620)


# ---------------------------------------------------------------- vitesses
def vitesses(courbe, etude) -> go.Figure:
    pal = palette()
    p = etude.p
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["V_passes_sans"], name="Passes, sans batardeau",
                             line=dict(color=pal["serie"][0], width=2), hovertemplate="%{y:.2f} m/s"))
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["V_passes_avec"], name="Passes, avec batardeau",
                             line=dict(color=pal["serie"][1], width=2), hovertemplate="%{y:.2f} m/s"))
    fig.add_trace(go.Scatter(x=courbe["Q"], y=courbe["V_passes_avec"] * float(p["k_vitesse_locale"]),
                             name=f"Locale au nez du batardeau (× {p['k_vitesse_locale']})",
                             line=dict(color=pal["serie"][1], width=1.5, dash="dot"),
                             hovertemplate="%{y:.2f} m/s"))
    _seuil_h(fig, float(p["vitesse_admissible"]), "Vitesse admissible", pal["critique"])
    _reperes_debits(fig, etude, pal)
    return _mise_en_page(fig, 420, "Débit Q (m³/s)", "Vitesse moyenne (m/s)")


# ---------------------------------------------------------------- risque
def risque(etude, synthese) -> go.Figure:
    pal = palette()
    q = np.linspace(max(1.0, 0.5 * etude.debit_T(2)), 1.3 * etude.debit_T(100), 200)
    pr = np.array([etude.proba_travaux(v) for v in q]) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=q, y=pr, mode="lines", name="Probabilité pendant les travaux",
                             line=dict(color=pal["serie"][0], width=2), showlegend=False,
                             hovertemplate="Q ≥ %{x:.0f} m³/s : %{y:.1f} %<extra></extra>"))
    reperes = [("Seuil d'impact", synthese.get("Q_seuil")), ("Alerte (crête − revanche)", synthese.get("Q_alerte")),
               ("Submersion du batardeau", synthese.get("Q_submersion")),
               (f"Crue de chantier Q{int(synthese['T_chantier'])}", synthese.get("Q_chantier"))]
    for i, (nom, qv) in enumerate(reperes):
        if qv is None or not math.isfinite(qv):
            continue
        pv = etude.proba_travaux(qv) * 100
        fig.add_trace(go.Scatter(x=[qv], y=[pv], mode="markers", name=nom, showlegend=False,
                                 marker=dict(size=10, color=pal["encre"],
                                             line=dict(width=2, color="rgba(255,255,255,0.9)")),
                                 hovertemplate=f"{nom}<br>%{{x:.0f}} m³/s · %{{y:.1f}} %<extra></extra>"))
        fig.add_annotation(x=qv, y=pv, text=f"{nom}<br>{pv:.1f} %".replace(".", ","), showarrow=True,
                           arrowhead=0, ax=40 if i % 2 == 0 else -40, ay=-38 - 12 * (i % 2),
                           font=dict(size=11))
    fig.update_yaxes(rangemode="tozero")
    return _mise_en_page(fig, 420, "Débit Q (m³/s)", "Probabilité d'au moins un dépassement (%)")


# ---------------------------------------------------------------- hydrogramme
def hydrogramme(sim, p) -> go.Figure:
    pal = palette()
    j = sim["t"] / 24.0
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.32, 0.4, 0.28],
                        subplot_titles=("Débit (m³/s)", "Cote amont au barrage (m NGF)", "Surélévation (cm)"))
    fig.add_trace(go.Scatter(x=j, y=sim["Q"], name="Débit", showlegend=False,
                             line=dict(color=pal["discret"], width=2), hovertemplate="%{y:.0f} m³/s"), row=1, col=1)
    fig.add_trace(go.Scatter(x=j, y=sim["Z_sans"], name="Sans batardeau",
                             line=dict(color=pal["serie"][0], width=2), hovertemplate="%{y:.2f} m"), row=2, col=1)
    fig.add_trace(go.Scatter(x=j, y=sim["Z_avec"], name="Avec batardeau",
                             line=dict(color=pal["serie"][1], width=2), hovertemplate="%{y:.2f} m"), row=2, col=1)
    _seuil_h(fig, float(p["cote_arase"]), "Crête", pal["critique"], row=2, col=1)
    _seuil_h(fig, float(p["cote_arase"]) - float(p["revanche"]), "Alerte", pal["encre2"], row=2, col=1,
             dash="dot", position="bottom left")
    fig.add_trace(go.Scatter(x=j, y=sim["dZ"] * 100, name="ΔZ", showlegend=False,
                             line=dict(color=pal["serie"][1], width=2), hovertemplate="%{y:.1f} cm"), row=3, col=1)
    _seuil_h(fig, float(p["seuil_dz"]) * 100, "Seuil", pal["critique"], row=3, col=1)
    for t, nom in ((sim["t_alerte"], "Alerte"), (sim["t_submersion"], "Submersion")):
        if t is not None:
            fig.add_vline(x=t / 24.0, line=dict(color=pal["encre2"], width=1, dash="dot"),
                          annotation_text=nom, annotation_position="top right", annotation_font_size=10)
    fig.update_xaxes(title_text="Temps depuis le début de l'événement (jours)", row=3, col=1)
    return _mise_en_page(fig, 640)


# ---------------------------------------------------------------- variantes
def variantes(var: dict, seuil_m: float, taux_nominal: float) -> go.Figure:
    pal = palette()
    fig = go.Figure()
    rampe = pal["rampe"]
    for i, (f, df) in enumerate(sorted(var.items())):
        nominal = abs(f - taux_nominal) < 1e-3
        fig.add_trace(go.Scatter(x=df["Q"], y=df["dZ_enveloppe"] * 100,
                                 name=f"Emprise {f * 100:.0f} % des passes" + (" (projet)" if nominal else ""),
                                 line=dict(color=rampe[min(i, len(rampe) - 1)], width=3 if nominal else 2),
                                 hovertemplate="%{y:.1f} cm"))
    _seuil_h(fig, seuil_m * 100, f"Seuil {seuil_m * 100:.0f} cm", pal["critique"])
    return _mise_en_page(fig, 420, "Débit Q (m³/s)", "Surélévation au barrage, enveloppe (cm)")


# ---------------------------------------------------------------- sensibilité
def tornade(sens) -> go.Figure:
    pal = palette()
    base = sens.attrs.get("base", 0.0) * 100
    lo = np.minimum(sens["dZ_bas"], sens["dZ_haut"]) * 100
    hi = np.maximum(sens["dZ_bas"], sens["dZ_haut"]) * 100
    fig = go.Figure(go.Bar(y=sens["parametre"], x=np.maximum(hi - lo, 0.05), base=lo, orientation="h",
                           marker=dict(color=pal["serie"][0], cornerradius=4),
                           customdata=np.stack([lo, hi], axis=1),
                           hovertemplate="%{y}<br>%{customdata[0]:.1f} à %{customdata[1]:.1f} cm<extra></extra>"))
    fig.add_vline(x=base, line=dict(color=pal["encre"], width=1.5),
                  annotation_text=f"Valeur de base {base:.1f} cm".replace(".", ","), annotation_position="top")
    fig.update_layout(hovermode="closest", bargap=0.35)
    return _mise_en_page(fig, 440, "Surélévation au barrage (cm)")


def histogramme_mc(mc: dict, seuil_m: float) -> go.Figure:
    pal = palette()
    fig = go.Figure(go.Histogram(x=mc["tirages"] * 100, nbinsx=30, marker=dict(color=pal["serie"][0]),
                                 hovertemplate="%{x} cm : %{y} tirages<extra></extra>"))
    _v = [(seuil_m * 100, f"Seuil {seuil_m * 100:.0f} cm", pal["critique"]),
          (mc["p95"] * 100, "95ᵉ centile", pal["encre"])]
    for x, nom, c in _v:
        fig.add_vline(x=x, line=dict(color=c, width=1.5, dash="dash"), annotation_text=nom,
                      annotation_position="top")
    fig.update_layout(hovermode="closest", bargap=0.06)
    return _mise_en_page(fig, 380, "Surélévation au barrage (cm)", "Nombre de tirages")


# ---------------------------------------------------------------- schéma du barrage
def schema_barrage(etude, resultat=None) -> go.Figure:
    """Vue de face depuis l'amont : passes, piles, seuils, batardeau et niveaux d'eau."""
    pal = palette()
    p = etude.p
    B = float(p["largeur_riviere"])
    zf = float(p["cote_fond"])
    passes = etude.passes
    n = len(passes)
    larg_passes = sum(x["largeur"] for x in passes)
    e_pile = (B - larg_passes) / (n - 1) if n > 1 else 0.0
    marge = (B - larg_passes) / 2 if n == 1 else 0.0
    niveaux = [float(p["cote_arase"]), float(p["rn_amont"])]
    if resultat is not None:
        niveaux += [resultat.Z_bat_env, resultat.Z_ref_base, resultat.Z3]
    haut = max(niveaux) + 1.0
    fig = go.Figure()
    x = marge
    for i, ps in enumerate(passes):
        b = ps["largeur"]
        zs = ps["cote_seuil"]
        if zs > zf + 1e-6:
            fig.add_shape(type="rect", x0=x, x1=x + b, y0=zf, y1=zs, fillcolor=pal["fond_lit"],
                          line=dict(width=0))
        ob = b * ps["obstruction"]
        if ob > 0:
            fig.add_shape(type="rect", x0=x + 0.3, x1=x + ob - 0.3, y0=zs, y1=float(p["cote_arase"]),
                          fillcolor="rgba(235,104,52,0.35)", line=dict(color=pal["serie"][1], width=2))
            fig.add_annotation(x=x + ob / 2, y=(zs + float(p["cote_arase"])) / 2, text="Batardeau",
                               showarrow=False, font=dict(size=12))
        fig.add_annotation(x=x + b / 2, y=zf - 0.5, text=f"{ps['nom']} · {b:.0f} m".replace(".", ","),
                           showarrow=False, font=dict(size=10))
        x += b
        if i < n - 1:
            fig.add_shape(type="rect", x0=x, x1=x + e_pile, y0=zf, y1=haut, fillcolor=pal["discret"],
                          line=dict(width=0))
            x += e_pile
    fig.add_shape(type="rect", x0=-2, x1=0, y0=zf - 0.1, y1=haut, fillcolor=pal["discret"], line=dict(width=0))
    fig.add_shape(type="rect", x0=B, x1=B + 2, y0=zf - 0.1, y1=haut, fillcolor=pal["discret"], line=dict(width=0))
    lignes = []
    if p["regulation"]:
        lignes.append((float(p["rn_amont"]), "RN amont", pal["discret"], "dot"))
    if resultat is not None:
        lignes += [(resultat.Z3, "Aval", pal["encre2"], "dot"),
                   (resultat.Z_ref_base, "Amont sans batardeau", pal["serie"][0], "solid"),
                   (resultat.Z_bat_env, "Amont avec batardeau", pal["serie"][1], "solid")]
    for z, nom, c, d in lignes:
        fig.add_trace(go.Scatter(x=[0, B], y=[z, z], mode="lines", name=f"{nom} : {z:.2f} m".replace(".", ","),
                                 line=dict(color=c, width=2, dash=d), hovertemplate=f"{nom} %{{y:.2f}} m<extra></extra>"))
    fig.update_xaxes(range=[-3, B + 3], title_text="Position en travers (m), vue depuis l'amont", zeroline=False)
    fig.update_yaxes(range=[zf - 0.9, haut], title_text="Cote (m NGF)")
    fig.update_layout(hovermode="closest")
    return _mise_en_page(fig, 380)
