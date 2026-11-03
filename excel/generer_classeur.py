"""Génère le classeur Excel « BatCrue » : toutes les formules de l'étude, recalculées par Excel.

Usage :  python excel/generer_classeur.py [chemin_sortie.xlsx]

Le classeur reprend le moteur Python pour un barrage dont toutes les passes ont la même cote de
seuil (cas courant) : hauteur normale par une courbe de tarage de Manning-Strickler, quatre
méthodes de calcul au barrage, régulation, enveloppe, risque pendant les travaux et courbe de
remous (équation de Bresse intégrée par le schéma de Heun). Les cellules jaunes sont les seules
à modifier ; tout le reste se recalcule.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as col
from openpyxl.workbook.defined_name import DefinedName

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from batcrue.parametres import DEFAUTS  # noqa: E402

POLICE = "Arial"
F_NORMAL = Font(name=POLICE, size=10)
F_GRAS = Font(name=POLICE, size=10, bold=True)
F_TITRE = Font(name=POLICE, size=14, bold=True, color="0D5F80")
F_SECTION = Font(name=POLICE, size=11, bold=True, color="FFFFFF")
F_SAISIE = Font(name=POLICE, size=10, color="0000FF")
F_LIEN = Font(name=POLICE, size=10, color="008000")
F_NOTE = Font(name=POLICE, size=9, italic=True, color="555555")
FOND_SAISIE = PatternFill("solid", fgColor="FFFF00")
FOND_SECTION = PatternFill("solid", fgColor="0D5F80")
FOND_ENTETE = PatternFill("solid", fgColor="DDE7EC")
FOND_RESULTAT = PatternFill("solid", fgColor="E8F3E8")
BORD = Border(bottom=Side(style="thin", color="BBBBBB"))
CENTRE = Alignment(horizontal="center", vertical="center", wrap_text=True)

NB_GRILLE = 80        # débits de la grille de calcul
NB_PAS = 120          # pas de la courbe de remous
NB_TARAGE = 2000      # lignes de la courbe de tarage (pas de 1 cm, jusqu'à 20 m)


class Classeur:
    def __init__(self):
        self.wb = Workbook()
        self.noms: dict[str, str] = {}

    def nommer(self, nom: str, feuille: str, cellule: str):
        lettres = "".join(c for c in cellule if c.isalpha())
        chiffres = "".join(c for c in cellule if c.isdigit())
        ref = f"'{feuille}'!${lettres}${chiffres}"
        self.wb.defined_names[nom] = DefinedName(nom, attr_text=ref)
        self.noms[nom] = ref


def _largeurs(ws, largeurs: dict):
    for c, w in largeurs.items():
        ws.column_dimensions[c].width = w


def _titre(ws, texte, sous_titre=None):
    ws["A1"] = texte
    ws["A1"].font = F_TITRE
    if sous_titre:
        ws["A2"] = sous_titre
        ws["A2"].font = F_NOTE


def _section(ws, ligne, texte, nb_col=5):
    for c in range(1, nb_col + 1):
        ws.cell(ligne, c).fill = FOND_SECTION
    ws.cell(ligne, 1, texte).font = F_SECTION


# ====================================================================== Lisez-moi
def feuille_lisez_moi(cl: Classeur):
    ws = cl.wb.active
    ws.title = "Lisez-moi"
    _titre(ws, "BatCrue – Impact hydraulique d'un batardeau sur les crues (version Excel)")
    lignes = [
        ("Objet", "Estimer la surélévation des niveaux de crue causée par un batardeau qui occupe une partie des "
                  "passes d'un barrage de navigation, sa propagation vers l'amont et le risque pendant les travaux."),
        ("Mode d'emploi", "1) Saisir les données dans la feuille « Données » : seules les cellules JAUNES à texte BLEU "
                          "se modifient. 2) Lire la synthèse et les graphiques dans « Résultats ». 3) Le détail des "
                          "calculs est dans « Calculs » (barrage), « Remous » (ligne d'eau), « Risque » et « Tarage »."),
        ("Valeurs fournies", "Les valeurs saisies sont un EXEMPLE FICTIF réaliste (barrage type de l'Oise, 3 passes de "
                             "20 m, batardeau sur une passe). Elles doivent être remplacées par les données réelles."),
        ("Code couleur", "Jaune + texte bleu : donnée à saisir · noir : formule · vert : lien vers une autre feuille."),
        ("Méthodes", "A : Bernoulli + pertes de Borda-Carnot (+ contrôle critique) · B : Yarnell (1934) · "
                     "C : d'Aubuisson (1840) · D : lois de seuil dénoyé/noyé. Hauteur normale de Manning-Strickler, "
                     "courbe de remous de Bresse (schéma de Heun), loi de Gumbel, risque poissonnien pendant les travaux."),
        ("Hypothèses", "Régime permanent au débit de pointe ; tout le débit passe par les passes ; passes de même cote "
                       "de seuil ; sans vitesse d'approche dans la loi de seuil ; coefficient de Coriolis = 1 dans la "
                       "courbe de remous (l'application Python, plus complète, l'intègre)."),
        ("Différences avec l'application", "Les cotes au barrage sont identiques à l'application BatCrue (Python). "
                                            "La ligne d'eau Excel néglige le coefficient de Coriolis : écart de quelques "
                                            "centimètres sur les cotes absolues, de l'ordre du millimètre sur ΔZ."),
        ("Graphiques", "Le bas des axes de cotes est réglé sur l'exemple : si vos cotes NGF sont très différentes, "
                       "ajustez-le (clic droit sur l'axe > Format de l'axe > Minimum)."),
        ("Avertissement", "Outil de pré-diagnostic. Les résultats sont à valider par un ingénieur hydraulicien et par "
                          "le service police de l'eau ; ils ne remplacent pas une modélisation calée sur la vallée."),
    ]
    for i, (a, b) in enumerate(lignes, start=3):
        ws.cell(i, 1, a).font = F_GRAS
        c = ws.cell(i, 2, b)
        c.font = F_NORMAL
        c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 45
    ws.cell(13, 1, "Exemple de saisie").font = F_GRAS
    c = ws.cell(13, 2, 25.0)
    c.font, c.fill = F_SAISIE, FOND_SAISIE
    ws.cell(13, 3, "← une cellule de saisie ressemble à ceci").font = F_NOTE
    _largeurs(ws, {"A": 26, "B": 110, "C": 40})


# ====================================================================== Données
def feuille_donnees(cl: Classeur):
    ws = cl.wb.create_sheet("Données")
    d = DEFAUTS
    _titre(ws, "Données d'entrée", "Saisir uniquement les cellules jaunes. Valeurs d'exemple fictives à remplacer.")
    for j, h in enumerate(["Donnée", "Valeur", "Unité", "Nom", "Commentaire / source"], start=1):
        c = ws.cell(3, j, h)
        c.font, c.fill = F_GRAS, FOND_ENTETE
    passes = d["passes"]
    l_passes = sum(p["largeur"] for p in passes)
    l_obst = sum(p["largeur"] * p["obstruction"] for p in passes)
    blocs = [
        ("BARRAGE ET BATARDEAU", [
            ("Nom du barrage", "Nom_barrage", d["nom_barrage"], "", ""),
            ("Largeur hydraulique au droit du barrage B", "B_riv", d["largeur_riviere"], "m", "Entre culées, hors écluse."),
            ("Cote du fond au droit du barrage", "Z_fond", d["cote_fond"], "m NGF", ""),
            ("Cote du seuil des passes", "Z_seuil", passes[0]["cote_seuil"], "m NGF", "Même cote pour toutes les passes."),
            ("Largeur totale des passes", "L_passes", l_passes, "m", "Somme des largeurs libres des passes."),
            ("Largeur des passes obstruée par le batardeau", "L_obstruee", l_obst, "m", "Ex. une passe de 20 m."),
            ("Barrage régulé (1 = oui, 0 = non)", "Regulation", 1, "", "Maintien de la retenue normale tant que possible."),
            ("Retenue normale amont RN", "RN_amont", d["rn_amont"], "m NGF", ""),
            ("Cote de crête du batardeau", "Crete", d["cote_arase"], "m NGF", ""),
            ("Revanche de sécurité", "Revanche", d["revanche"], "m", ""),
            ("Date de pose du batardeau", "Date_debut", date.fromisoformat(d["debut_travaux"]), "", "Format date."),
            ("Date de dépose du batardeau", "Date_fin", date.fromisoformat(d["fin_travaux"]), "", "Durée ≤ 2 ans."),
        ]),
        ("COEFFICIENTS", [
            ("ξ contraction – piles existantes", "Xi_piles", d["xi_ref"], "", "HEC-RAS : 0,1 progressive ; 0,3 typique ; 0,6 brusque."),
            ("ξ contraction – nez du batardeau", "Xi_bat", d["xi_bat"], "", "Batardeau rectangulaire : 0,6."),
            ("K de Yarnell – piles", "K_Y_piles", d["K_yarnell_ref"], "", "0,90 arrondi ; 1,05 triangulaire ; 1,25 carré."),
            ("K de Yarnell – batardeau", "K_Y_bat", d["K_yarnell_bat"], "", "Manuel HEC-RAS, tableau des formes de piles."),
            ("Coefficient de d'Aubuisson K_A", "K_A", d["K_A"], "", "1,0 = perte totale de l'énergie cinétique ; 0,87 à 1,07."),
            ("Coefficient de seuil dénoyé μ", "Mu", d["mu"], "", "0,385 = seuil épais théorique."),
            ("Méthode A active (1/0)", "Actif_A", 1, "", "La méthode A sert de référence pour la cote sans batardeau."),
            ("Méthode B active (1/0)", "Actif_B", 1, "", ""),
            ("Méthode C active (1/0)", "Actif_C", 1, "", ""),
            ("Méthode D active (1/0)", "Actif_D", 1, "", ""),
        ]),
        ("RIVIÈRE (BIEF AMONT ET AVAL)", [
            ("Largeur au fond du lit mineur", "Lit_b", d["b_min"], "m", ""),
            ("Fruit des berges (H/V)", "Lit_m", d["m_berge"], "", ""),
            ("Hauteur de berge (plein bord)", "Lit_hb", d["h_berge"], "m", ""),
            ("Largeur du lit majeur actif (RG + RD)", "Lit_Bmaj", d["B_maj"], "m", "0 si vallée endiguée."),
            ("Strickler du lit mineur", "K_min", d["K_min"], "m^1/3/s", "Rivière canalisée : 30 à 40."),
            ("Strickler du lit majeur", "K_maj", d["K_maj"], "m^1/3/s", "Prairie : 15 à 25."),
            ("Pente moyenne", "Pente", d["pente"], "m/m", "0,0002 = 20 cm/km."),
            ("Retenue normale du bief aval", "RN_aval", d["rn_aval"], "m NGF", ""),
            ("Décalage de la cote aval (sensibilité)", "Decal_aval", d["decalage_aval"], "m", ""),
            ("Longueur étudiée vers l'amont", "L_bief", d["longueur_bief"], "m", "Pas de calcul = longueur / 120."),
        ]),
        ("HYDROLOGIE ET CRITÈRES", [
            ("Loi de Gumbel : position u", "Gu", d["gumbel_u"], "m³/s", "À ajuster sur les maxima annuels (HydroPortail)."),
            ("Loi de Gumbel : échelle β", "Gbeta", d["gumbel_beta"], "m³/s", ""),
            ("Module (débit moyen)", "Module", d["module"], "m³/s", ""),
            ("Crue de référence T", "T_ref", d["T_reference"], "ans", "Souvent Q100 ou plus forte crue connue (PPRI)."),
            ("Crue de chantier T", "T_ch", d["T_chantier"], "ans", ""),
            ("Période de retour de la ligne d'eau", "T_etude", d["T_reference"], "ans", ""),
            ("Surélévation admissible", "Seuil_dz", d["seuil_dz"], "m", "À fixer avec le service police de l'eau."),
            ("Probabilité acceptable pendant les travaux", "P_acc", d["proba_acceptable"], "", "Fraction (0,05 = 5 %)."),
        ]),
    ]
    ligne = 4
    for titre, rangees in blocs:
        _section(ws, ligne, titre)
        ligne += 1
        for lib, nom, val, unite, com in rangees:
            ws.cell(ligne, 1, lib).font = F_NORMAL
            c = ws.cell(ligne, 2, val)
            c.font, c.fill = F_SAISIE, FOND_SAISIE
            if isinstance(val, date):
                c.number_format = "DD/MM/YYYY"
            elif isinstance(val, float) and abs(val) < 0.01 and val != 0:
                c.number_format = "0.00000"
            ws.cell(ligne, 3, unite).font = F_NORMAL
            ws.cell(ligne, 4, nom).font = F_NOTE
            ws.cell(ligne, 5, com).font = F_NOTE
            cl.nommer(nom, "Données", f"B{ligne}")
            ligne += 1
    # Saisonnalité
    _section(ws, ligne, "SAISONNALITÉ DES CRUES (poids mensuels relatifs, 1 partout = uniforme)")
    ligne += 1
    mois = ["Janv.", "Févr.", "Mars", "Avr.", "Mai", "Juin", "Juil.", "Août", "Sept.", "Oct.", "Nov.", "Déc."]
    for k, m in enumerate(mois, start=1):
        ws.cell(ligne, 1, f"Poids – {m}").font = F_NORMAL
        c = ws.cell(ligne, 2, float(d["poids_mensuels"][k - 1]))
        c.font, c.fill = F_SAISIE, FOND_SAISIE
        ws.cell(ligne, 4, f"Poids_{k}").font = F_NOTE
        cl.nommer(f"Poids_{k}", "Données", f"B{ligne}")
        ligne += 1
    # Enjeux
    _section(ws, ligne, "ENJEUX À VÉRIFIER (x = distance vers l'amont depuis le barrage)")
    ligne += 1
    for j, h in enumerate(["Enjeu", "x (m)", "Cote de premiers dommages (m NGF)"], start=1):
        c = ws.cell(ligne, j, h)
        c.font, c.fill = F_GRAS, FOND_ENTETE
    ligne += 1
    cl.enjeux_ligne0 = ligne
    for k, e in enumerate(d["enjeux"][:5]):
        for j, v in enumerate([e["nom"], e["x"], e["cote_dommages"]], start=1):
            v = None if isinstance(v, float) and v != v else v
            c = ws.cell(ligne, j, v)
            c.font, c.fill = F_SAISIE, FOND_SAISIE
        ligne += 1
    for k in range(len(d["enjeux"]), 5):
        for j in range(1, 4):
            ws.cell(ligne, j).fill = FOND_SAISIE
            ws.cell(ligne, j).font = F_SAISIE
        ligne += 1
    cl.enjeux_ligne1 = ligne - 1
    # Grandeurs dérivées
    ligne += 1
    _section(ws, ligne, "GRANDEURS DÉRIVÉES (calculées, ne pas modifier)")
    ligne += 1
    derivees = [
        ("Accélération de la pesanteur g", "Gpes", 9.81, "m/s²"),
        ("Largeur libre des passes avec batardeau", "L_libre", "=L_passes-L_obstruee", "m"),
        ("Largeur des piles et culées", "L_piles", "=MAX(B_riv-L_passes,0)", "m"),
        ("ξ effectif sans batardeau", "Xi_sans", "=Xi_piles", ""),
        ("ξ effectif avec batardeau (pondéré par les largeurs)", "Xi_avec",
         "=IF(L_obstruee<=0,Xi_piles,(L_piles*Xi_piles+L_obstruee*Xi_bat)/(L_piles+L_obstruee))", ""),
        ("K Yarnell sans batardeau", "K_sans", "=K_Y_piles", ""),
        ("K Yarnell avec batardeau (pondéré)", "K_avec",
         "=IF(L_obstruee<=0,K_Y_piles,(L_piles*K_Y_piles+L_obstruee*K_Y_bat)/(L_piles+L_obstruee))", ""),
        ("Coefficient de seuil noyé μs = 3√3/2·μ", "Mu_s", "=1.5*SQRT(3)*Mu", ""),
        ("Débit minimal de la grille", "Qmin", "=MAX(1,0.3*Module)", "m³/s"),
        ("Débit maximal de la grille", "Qmax", "=1.15*MAX(Gu-Gbeta*LN(-LN(1-1/100)),Gu-Gbeta*LN(-LN(1-1/T_ref)))", "m³/s"),
        ("Pas de calcul de la courbe de remous", "Dx_r", f"=L_bief/{NB_PAS}", "m"),
    ]
    for lib, nom, val, unite in derivees:
        ws.cell(ligne, 1, lib).font = F_NORMAL
        c = ws.cell(ligne, 2, val)
        c.font = F_NORMAL
        c.number_format = "0.000"
        ws.cell(ligne, 3, unite).font = F_NORMAL
        ws.cell(ligne, 4, nom).font = F_NOTE
        cl.nommer(nom, "Données", f"B{ligne}")
        ligne += 1
    ws.freeze_panes = "A4"
    _largeurs(ws, {"A": 52, "B": 16, "C": 10, "D": 13, "E": 58})


# ====================================================================== Tarage
def _aire_min(y):
    return (f"IF(OR(Lit_Bmaj<=0,{y}<=Lit_hb),(Lit_b+Lit_m*{y})*{y},"
            f"(Lit_b+Lit_m*Lit_hb)*Lit_hb+(Lit_b+2*Lit_m*Lit_hb)*({y}-Lit_hb))")


def _perim_min(y):
    return f"IF(OR(Lit_Bmaj<=0,{y}<=Lit_hb),Lit_b+2*{y}*SQRT(1+Lit_m^2),Lit_b+2*Lit_hb*SQRT(1+Lit_m^2))"


def _aire_maj(y):
    return f"IF(AND(Lit_Bmaj>0,{y}>Lit_hb),Lit_Bmaj*({y}-Lit_hb),0)"


def _largeur_miroir(y):
    return f"IF(OR(Lit_Bmaj<=0,{y}<=Lit_hb),Lit_b+2*Lit_m*{y},Lit_b+2*Lit_m*Lit_hb+Lit_Bmaj)"


def _debitance(y):
    return (f"K_min*({_aire_min(y)})^(5/3)/({_perim_min(y)})^(2/3)"
            f"+IF(AND(Lit_Bmaj>0,{y}>Lit_hb),K_maj*(Lit_Bmaj*({y}-Lit_hb))^(5/3)/Lit_Bmaj^(2/3),0)")


def feuille_tarage(cl: Classeur):
    ws = cl.wb.create_sheet("Tarage")
    _titre(ws, "Courbe de tarage en régime uniforme (Manning-Strickler, lit composé)",
           "Q = Σ K·A·R^(2/3)·√I, lit mineur et lit majeur séparés. Sert au calcul de la hauteur normale aval.")
    entetes = ["y (m)", "A mineur (m²)", "P mineur (m)", "A majeur (m²)", "Débitance Kd (m³/s)", "Q normal (m³/s)"]
    for j, h in enumerate(entetes, start=1):
        c = ws.cell(3, j, h)
        c.font, c.fill, c.alignment = F_GRAS, FOND_ENTETE, CENTRE
    for i in range(NB_TARAGE):
        r = 4 + i
        ws.cell(r, 1, round(0.01 * (i + 1), 2))
        y = f"A{r}"
        ws.cell(r, 2, f"={_aire_min(y)}")
        ws.cell(r, 3, f"={_perim_min(y)}")
        ws.cell(r, 4, f"={_aire_maj(y)}")
        ws.cell(r, 5, f"={_debitance(y)}")
        ws.cell(r, 6, f"=E{r}*SQRT(Pente)")
        for j in range(1, 7):
            ws.cell(r, j).font = F_NORMAL
            ws.cell(r, j).number_format = "0.00" if j == 1 else "0.0"
    cl.tarage = (4, 3 + NB_TARAGE)
    ws.freeze_panes = "A4"
    _largeurs(ws, {"A": 9, "B": 15, "C": 14, "D": 15, "E": 19, "F": 16})


# ====================================================================== Calculs
def feuille_calculs(cl: Classeur):
    ws = cl.wb.create_sheet("Calculs")
    _titre(ws, "Calculs au droit du barrage, débit par débit",
           "Méthodes A (énergie + Borda-Carnot), B (Yarnell), C (d'Aubuisson), D (seuils). Une ligne = un débit.")
    t0, t1 = cl.tarage
    colonnes = []  # (clé, entête, formule(ligne, précédente) ou None, format)

    def ajout(cle, entete, fmt="0.000"):
        colonnes.append((cle, entete, fmt))

    for cle, ent, fmt in [
        ("lib", "Débit", "@"), ("T", "T (ans)", "0.0"), ("Q", "Q (m³/s)", "0.0"), ("yn", "y normale (m)", "0.000"),
        ("Z3", "Z aval (m NGF)", "0.000"), ("y3", "y aval (m)", "0.000"), ("V3", "V aval (m/s)", "0.000"),
        ("E3", "Charge aval E3", "0.000"),
    ]:
        ajout(cle, ent, fmt)
    for cas in ("s", "a"):
        ajout(f"yc_{cas}", f"A {cas} : y critique passes", "0.000")
        ajout(f"ch_{cas}", f"A {cas} : étranglement (1/0)", "0")
        for k in range(1, 7):
            ajout(f"z2{k}_{cas}", f"A {cas} : Z2 itér. {k}", "0.0000")
        ajout(f"Z2_{cas}", f"A {cas} : Z2 (m NGF)", "0.000")
        ajout(f"V2_{cas}", f"A {cas} : V2 (m/s)", "0.000")
        ajout(f"E2_{cas}", f"A {cas} : E2", "0.000")
        for k in range(1, 7):
            ajout(f"z1{k}_{cas}", f"A {cas} : Z1 itér. {k}", "0.0000")
        ajout(f"Z1A_{cas}", f"A {cas} : Z1 libre (m NGF)", "0.000")
    for cle, ent in [("om", "B : ω"), ("al_s", "B : α sans"), ("al_a", "B : α avec"), ("Z1B_s", "B : Z1 libre sans"),
                     ("Z1B_a", "B : Z1 libre avec"), ("vB", "B valide (1/0)")]:
        ajout(cle, ent, "0" if cle == "vB" else "0.000")
    ajout("Al_s", "C : A libre sans (m²)", "0.0")
    ajout("Al_a", "C : A libre avec (m²)", "0.0")
    for cas in ("s", "a"):
        for k in range(1, 7):
            ajout(f"dh{k}_{cas}", f"C {cas} : Δh itér. {k}", "0.0000")
        ajout(f"Z1C_{cas}", f"C {cas} : Z1 libre", "0.000")
    ajout("h2", "D : h2 aval (m)", "0.000")
    for cas in ("s", "a"):
        ajout(f"hd_{cas}", f"D {cas} : h1 dénoyé", "0.000")
        ajout(f"h1_{cas}", f"D {cas} : h1", "0.000")
        ajout(f"Z1D_{cas}", f"D {cas} : Z1 libre", "0.000")
    ajout("RN", "RN effective", "0.00")
    for m in "ABCD":
        ajout(f"Zs{m}", f"{m} : Z amont sans", "0.000")
        ajout(f"Za{m}", f"{m} : Z amont avec", "0.000")
        ajout(f"dZ{m}", f"{m} : ΔZ (m)", "0.000")
    for cle, ent, fmt in [("dZe", "ΔZ enveloppe (m)", "0.000"), ("Zs", "Z amont sans (m NGF)", "0.000"),
                          ("Za", "Z amont avec (m NGF)", "0.000"), ("V2s", "V passes sans (m/s)", "0.00"),
                          ("V2a", "V passes avec (m/s)", "0.00"), ("reg", "Régime avec batardeau", "@"),
                          ("TQ", "Période de retour (ans)", "0.0"), ("PT", "Proba. pendant travaux", "0.0%"),
                          ("xs", "Franchissement seuil ΔZ", "0.0"), ("xa", "Franchissement alerte", "0.0"),
                          ("xc", "Franchissement crête", "0.0"),
                          ("cmA", "ΔZ A (cm)", "0.0"), ("cmB", "ΔZ B (cm)", "0.0"), ("cmC", "ΔZ C (cm)", "0.0"),
                          ("cmD", "ΔZ D (cm)", "0.0"), ("cmE", "ΔZ enveloppe (cm)", "0.0"),
                          ("cr", "Crête du batardeau", "0.00")]:
        ajout(cle, ent, fmt)
    pos = {cle: col(j) for j, (cle, _, _) in enumerate(colonnes, start=1)}
    cl.calc_cols = pos
    for j, (_, ent, _) in enumerate(colonnes, start=1):
        c = ws.cell(4, j, ent)
        c.font, c.fill, c.alignment = F_GRAS, FOND_ENTETE, CENTRE
    ws.row_dimensions[4].height = 42

    Ts = [("Q2", "2"), ("Q5", "5"), ("Q10", "10"), ("Q20", "20"), ("Q50", "50"), ("Q100", "100"),
          ("Crue de chantier", "T_ch"), ("Crue de référence", "T_ref"), ("Débit de la ligne d'eau", "T_etude")]
    lignes_T = list(range(5, 5 + len(Ts)))
    g0 = 5 + len(Ts) + 2
    lignes_G = list(range(g0, g0 + NB_GRILLE))
    ws.cell(g0 - 1, 1, "Grille régulière de débits (graphiques, débits de franchissement)").font = F_GRAS
    cl.ligne_T = {lib: r for (lib, _), r in zip(Ts, lignes_T)}
    cl.grille = (g0, g0 + NB_GRILLE - 1)

    def f(r, prec=None):
        c = {k: f"{v}{r}" for k, v in pos.items()}
        Q, Z3 = c["Q"], c["Z3"]
        out = {}
        out["yn"] = (f"=IFERROR(INDEX(Tarage!$A${t0}:$A${t1},MATCH({Q},Tarage!$F${t0}:$F${t1},1))"
                     f"+({Q}-INDEX(Tarage!$F${t0}:$F${t1},MATCH({Q},Tarage!$F${t0}:$F${t1},1)))"
                     f"/(INDEX(Tarage!$F${t0}:$F${t1},MATCH({Q},Tarage!$F${t0}:$F${t1},1)+1)"
                     f"-INDEX(Tarage!$F${t0}:$F${t1},MATCH({Q},Tarage!$F${t0}:$F${t1},1)))*0.01,"
                     f"0.01*{Q}/Tarage!$F${t0})")
        out["Z3"] = f"=MAX(IF(Regulation=1,MAX(RN_aval,Z_fond+{c['yn']}),Z_fond+{c['yn']})+Decal_aval,Z_fond+0.05)"
        out["y3"] = f"={Z3}-Z_fond"
        out["V3"] = f"={Q}/(B_riv*{c['y3']})"
        out["E3"] = f"={Z3}+{c['V3']}^2/(2*Gpes)"
        V3, E3 = c["V3"], c["E3"]
        for cas, larg, xi in (("s", "L_passes", "Xi_sans"), ("a", "L_libre", "Xi_avec")):
            yc = c[f"yc_{cas}"]
            out[f"yc_{cas}"] = f"=({Q}^2/(Gpes*{larg}^2))^(1/3)"
            vc = f"SQRT(Gpes*{yc})"
            out[f"ch_{cas}"] = (f"=IF(OR({E3}<=Z_seuil+{yc},Z_seuil+{yc}+{vc}^2/(2*Gpes)-{E3}"
                                f"-MAX(0,{vc}-{V3})^2/(2*Gpes)>=0),1,0)")
            prec_z = Z3
            for k in range(1, 7):
                v2 = f"({Q}/({larg}*MAX({prec_z}-Z_seuil,0.001)))"
                out[f"z2{k}_{cas}"] = f"={E3}+MAX(0,{v2}-{V3})^2/(2*Gpes)-{v2}^2/(2*Gpes)"
                prec_z = c[f"z2{k}_{cas}"]
            out[f"Z2_{cas}"] = f"=IF({c[f'ch_{cas}']}=1,Z_seuil+{yc},{prec_z})"
            out[f"V2_{cas}"] = f"={Q}/({larg}*({c[f'Z2_{cas}']}-Z_seuil))"
            out[f"E2_{cas}"] = f"={c[f'Z2_{cas}']}+{c[f'V2_{cas}']}^2/(2*Gpes)"
            prec_z = c[f"E2_{cas}"]
            v2 = c[f"V2_{cas}"]
            for k in range(1, 7):
                v1 = f"({Q}/(B_riv*({prec_z}-Z_fond)))"
                out[f"z1{k}_{cas}"] = (f"={c[f'E2_{cas}']}-{v1}^2/(2*Gpes)"
                                       f"+{xi}*MAX(0,{v2}^2-{v1}^2)/(2*Gpes)")
                prec_z = c[f"z1{k}_{cas}"]
            out[f"Z1A_{cas}"] = f"={prec_z}"
        out["om"] = f"={V3}^2/(2*Gpes*{c['y3']})"
        out["al_s"] = f"=MAX(0,1-L_passes*MAX({Z3}-Z_seuil,0)/(B_riv*{c['y3']}))"
        out["al_a"] = f"=MAX(0,1-L_libre*MAX({Z3}-Z_seuil,0)/(B_riv*{c['y3']}))"
        for cas, K in (("s", "K_sans"), ("a", "K_avec")):
            al = c[f"al_{cas}"]
            out[f"Z1B_{cas}"] = (f"={Z3}+2*{K}*MAX(0,{K}+10*{c['om']}-0.6)*({al}+15*{al}^4)"
                                 f"*{V3}^2/(2*Gpes)")
        out["vB"] = (f"=IF(AND({c['al_s']}<=0.5,{c['al_a']}<=0.5,{c['ch_a']}=0,{Z3}>Z_seuil),1,0)")
        out["Al_s"] = f"=L_passes*MAX({Z3}-Z_seuil,0)"
        out["Al_a"] = f"=L_libre*MAX({Z3}-Z_seuil,0)"
        for cas in ("s", "a"):
            al = c[f"Al_{cas}"]
            prec = "0"
            for k in range(1, 7):
                out[f"dh{k}_{cas}"] = (f"=MAX(0,(({Q}/(K_A*MAX({al},0.001)))^2"
                                       f"-({Q}/(B_riv*({Z3}+{prec}-Z_fond)))^2)/(2*Gpes))")
                prec = c[f"dh{k}_{cas}"]
            out[f"Z1C_{cas}"] = f"={Z3}+{prec}"
        out["h2"] = f"={Z3}-Z_seuil"
        for cas, larg in (("s", "L_passes"), ("a", "L_libre")):
            hd = c[f"hd_{cas}"]
            out[f"hd_{cas}"] = f"=({Q}/(Mu*{larg}*SQRT(2*Gpes)))^(2/3)"
            out[f"h1_{cas}"] = (f"=IF({c['h2']}<=2/3*{hd},{hd},{c['h2']}"
                                f"+({Q}/(Mu_s*{larg}*{c['h2']}))^2/(2*Gpes))")
            out[f"Z1D_{cas}"] = f"=Z_seuil+{c[f'h1_{cas}']}"
        out["RN"] = "=IF(Regulation=1,RN_amont,-1000000)"
        for m in "ABCD":
            out[f"Zs{m}"] = f"=MAX({c['RN']},{c[f'Z1{m}_s']})"
            out[f"Za{m}"] = f"=MAX({c['RN']},{c[f'Z1{m}_a']})"
            out[f"dZ{m}"] = f"={c[f'Za{m}']}-{c[f'Zs{m}']}"
        out["dZe"] = (f"=MAX(IF(Actif_A=1,{c['dZA']},-1),IF(AND(Actif_B=1,{c['vB']}=1),{c['dZB']},-1),"
                      f"IF(Actif_C=1,{c['dZC']},-1),IF(Actif_D=1,{c['dZD']},-1))")
        out["Zs"] = f"={c['ZsA']}"
        out["Za"] = f"={c['Zs']}+{c['dZe']}"
        out["V2s"] = f"={c['V2_s']}"
        out["V2a"] = f"={c['V2_a']}"
        out["reg"] = f"=IF({c['ch_a']}=1,\"dénoyé\",\"noyé\")"
        out["TQ"] = f"=1/(1-EXP(-EXP(-({Q}-Gu)/Gbeta)))"
        out["PT"] = f"=1-EXP(-EXP(-({Q}-Gu)/Gbeta)*Frac_alea)"
        if prec is not None and prec != "0":
            pass
        out["cmA"] = f"={c['dZA']}*100"
        out["cmB"] = f"={c['dZB']}*100"
        out["cmC"] = f"={c['dZC']}*100"
        out["cmD"] = f"={c['dZD']}*100"
        out["cmE"] = f"={c['dZe']}*100"
        out["cr"] = "=Crete"
        return out

    for (lib, tref), r in zip(Ts, lignes_T):
        formules = f(r)
        ws[f"{pos['lib']}{r}"] = lib
        ws[f"{pos['T']}{r}"] = f"={tref}" if not tref.isdigit() else float(tref)
        ws[f"{pos['Q']}{r}"] = f"=Gu-Gbeta*LN(-LN(1-1/{pos['T']}{r}))"
        for k, v in formules.items():
            ws[f"{pos[k]}{r}"] = v
    for i, r in enumerate(lignes_G):
        formules = f(r)
        ws[f"{pos['lib']}{r}"] = f"Grille {i + 1}"
        ws[f"{pos['Q']}{r}"] = f"=Qmin+{i}*(Qmax-Qmin)/{NB_GRILLE - 1}"
        ws[f"{pos['T']}{r}"] = f"={pos['TQ']}{r}"
        for k, v in formules.items():
            ws[f"{pos[k]}{r}"] = v
        Q = f"{pos['Q']}{r}"
        if i == 0:
            ws[f"{pos['xs']}{r}"] = f"=IF({pos['dZe']}{r}>=Seuil_dz,{Q},1E+9)"
            ws[f"{pos['xa']}{r}"] = f"=IF({pos['Za']}{r}>=Crete-Revanche,{Q},1E+9)"
            ws[f"{pos['xc']}{r}"] = f"=IF({pos['Za']}{r}>=Crete,{Q},1E+9)"
        else:
            rp = r - 1
            Qp = f"{pos['Q']}{rp}"
            for cle, val, seuil in (("xs", "dZe", "Seuil_dz"), ("xa", "Za", "(Crete-Revanche)"), ("xc", "Za", "Crete")):
                v, vp = f"{pos[val]}{r}", f"{pos[val]}{rp}"
                ws[f"{pos[cle]}{r}"] = (f"=IF(AND({v}>={seuil},{vp}<{seuil}),"
                                        f"{Qp}+({seuil}-{vp})/({v}-{vp})*({Q}-{Qp}),1E+9)")
    for r in lignes_T + lignes_G:
        for j, (cle, _, fmt) in enumerate(colonnes, start=1):
            cell = ws.cell(r, j)
            cell.font = F_NORMAL
            cell.number_format = fmt
        ws.cell(r, 1).font = F_GRAS
    ws.freeze_panes = "D5"
    for j in range(1, len(colonnes) + 1):
        ws.column_dimensions[col(j)].width = 11
    ws.column_dimensions["A"].width = 22


# ====================================================================== Risque
def feuille_risque(cl: Classeur):
    ws = cl.wb.create_sheet("Risque")
    _titre(ws, "Risque de crue pendant l'installation du batardeau",
           "Crues poissonniennes de taux λ(Q) = exp(-(Q-u)/β) ; part de l'aléa annuel f = Σ poids du mois × jours/jours du mois.")
    ent = ["Année", "Mois", "Premier jour", "Dernier jour", "Jours de travaux", "Jours du mois", "Poids normalisé",
           "Contribution à f"]
    for j, h in enumerate(ent, start=1):
        c = ws.cell(3, j, h)
        c.font, c.fill, c.alignment = F_GRAS, FOND_ENTETE, CENTRE
    somme_poids = "(" + "+".join(f"Poids_{k}" for k in range(1, 13)) + ")"
    r = 4
    for a in range(2):
        for m in range(1, 13):
            ws.cell(r, 1, f"=YEAR(Date_debut)+{a}")
            ws.cell(r, 2, m)
            ws.cell(r, 3, f"=DATE(A{r},B{r},1)")
            ws.cell(r, 4, f"=EOMONTH(C{r},0)")
            ws.cell(r, 5, f"=MAX(0,MIN(Date_fin,D{r})-MAX(Date_debut,C{r})+1)")
            ws.cell(r, 6, f"=DAY(D{r})")
            ws.cell(r, 7, f"=CHOOSE(B{r},{','.join(f'Poids_{k}' for k in range(1, 13))})/{somme_poids}")
            ws.cell(r, 8, f"=G{r}*E{r}/F{r}")
            for j in range(1, 9):
                ws.cell(r, j).font = F_NORMAL
            ws.cell(r, 3).number_format = "DD/MM/YYYY"
            ws.cell(r, 4).number_format = "DD/MM/YYYY"
            ws.cell(r, 7).number_format = "0.0000"
            ws.cell(r, 8).number_format = "0.0000"
            r += 1
    ws.cell(r, 7, "Part de l'aléa f").font = F_GRAS
    c = ws.cell(r, 8, f"=SUM(H4:H{r - 1})")
    c.font, c.fill, c.number_format = F_GRAS, FOND_RESULTAT, "0.0000"
    cl.nommer("Frac_alea", "Risque", f"H{r}")
    r += 2
    pos = cl.calc_cols
    g0, g1 = cl.grille
    ws.cell(r, 1, "Événement").font = F_GRAS
    for j, h in enumerate(["Événement", "Débit (m³/s)", "Période de retour (ans)", "Probabilité pendant les travaux"], 1):
        c = ws.cell(r, j, h)
        c.font, c.fill = F_GRAS, FOND_ENTETE
    r += 1
    evts = [
        ("Atteinte du seuil d'impact", f"=MIN(Calculs!${pos['xs']}${g0}:${pos['xs']}${g1})", "Q_seuil"),
        ("Cote d'alerte (crête − revanche)", f"=MIN(Calculs!${pos['xa']}${g0}:${pos['xa']}${g1})", "Q_alerte"),
        ("Submersion du batardeau", f"=MIN(Calculs!${pos['xc']}${g0}:${pos['xc']}${g1})", "Q_sub"),
        ("Crue de chantier", "=Gu-Gbeta*LN(-LN(1-1/T_ch))", "Q_chantier"),
    ]
    for lib, form, nom in evts:
        ws.cell(r, 1, lib).font = F_NORMAL
        c = ws.cell(r, 2, form)
        c.number_format = "0.0"
        cl.nommer(nom, "Risque", f"B{r}")
        ws.cell(r, 3, f"=IF(B{r}>=1E+9,\"jamais atteint\",1/(1-EXP(-EXP(-(B{r}-Gu)/Gbeta))))").number_format = "0.0"
        ws.cell(r, 4, f"=IF(B{r}>=1E+9,0,1-EXP(-EXP(-(B{r}-Gu)/Gbeta)*Frac_alea))").number_format = "0.0%"
        for j in range(1, 5):
            ws.cell(r, j).font = F_NORMAL
        r += 1
    r += 1
    ws.cell(r, 1, "Débit que le dispositif doit tenir pour un risque égal à P_acc").font = F_GRAS
    c = ws.cell(r, 2, "=Gu-Gbeta*LN(-LN(1-P_acc)/Frac_alea)")
    c.font, c.fill, c.number_format = F_GRAS, FOND_RESULTAT, "0.0"
    cl.nommer("Q_projet_travaux", "Risque", f"B{r}")
    ws.cell(r, 3, "m³/s").font = F_NORMAL
    _largeurs(ws, {"A": 38, "B": 14, "C": 20, "D": 18, "E": 16, "F": 13, "G": 15, "H": 16})


# ====================================================================== Remous
def feuille_remous(cl: Classeur):
    ws = cl.wb.create_sheet("Remous")
    _titre(ws, "Courbe de remous vers l'amont (équation de Bresse, schéma de Heun)",
           "dy/ds = −(I − J)/(1 − Fr²), J = (Q/Kd)², Fr² = Q²·T/(g·A³) ; s = distance vers l'amont depuis le barrage.")
    pos = cl.calc_cols
    r_et = cl.ligne_T["Débit de la ligne d'eau"]
    ws["A3"] = "Débit étudié Q (m³/s)"
    ws["B3"] = f"=Calculs!{pos['Q']}{r_et}"
    ws["C3"] = "Cote amont de départ sans / avec (m NGF)"
    ws["D3"] = f"=Calculs!{pos['Zs']}{r_et}"
    ws["E3"] = f"=Calculs!{pos['Za']}{r_et}"
    for a in ("A3", "C3"):
        ws[a].font = F_GRAS
    for a in ("B3", "D3", "E3"):
        ws[a].font = F_LIEN
        ws[a].number_format = "0.000"
    cl.nommer("Q_r", "Remous", "B3")
    ent = ["s (m)", "Fond (m NGF)", "Haut de berge"]
    for cas in ("sans", "avec"):
        ent += [f"y {cas}", f"A {cas}", f"T {cas}", f"Kd {cas}", f"k1 {cas}", f"y prédit {cas}", f"A* {cas}",
                f"T* {cas}", f"Kd* {cas}", f"k2 {cas}"]
    ent += ["Z sans (m NGF)", "Z avec (m NGF)", "ΔZ (m)", "ΔZ (cm)", "Repère < 1 cm", "s (km)"]
    for j, h in enumerate(ent, start=1):
        c = ws.cell(5, j, h)
        c.font, c.fill, c.alignment = F_GRAS, FOND_ENTETE, CENTRE
    ws.row_dimensions[5].height = 32
    r0 = 6
    base = {"sans": 4, "avec": 14}

    def fpente(Y, A, T, Kd):
        return f"=-(Pente-(Q_r/{Kd})^2)/(1-Q_r^2*{T}/(Gpes*{A}^3))"

    for i in range(NB_PAS + 1):
        r = r0 + i
        ws.cell(r, 1, f"={i}*Dx_r")
        ws.cell(r, 2, f"=Z_fond+Pente*A{r}")
        ws.cell(r, 3, f"=B{r}+Lit_hb")
        for cas, j0 in base.items():
            cy, cA, cT, cK, ck1, cyp, cAp, cTp, cKp, ck2 = (col(j0 + k) for k in range(10))
            if i == 0:
                ws.cell(r, j0, f"={'D3' if cas == 'sans' else 'E3'}-Z_fond")
            else:
                rp = r - 1
                ws.cell(r, j0, f"={cy}{rp}+Dx_r/2*({ck1}{rp}+{ck2}{rp})")
            Y = f"{cy}{r}"
            ws.cell(r, j0 + 1, f"={_aire_min(Y)}+{_aire_maj(Y)}")
            ws.cell(r, j0 + 2, f"={_largeur_miroir(Y)}")
            ws.cell(r, j0 + 3, f"={_debitance(Y)}")
            ws.cell(r, j0 + 4, fpente(Y, f"{cA}{r}", f"{cT}{r}", f"{cK}{r}"))
            ws.cell(r, j0 + 5, f"={Y}+Dx_r*{ck1}{r}")
            Yp = f"{cyp}{r}"
            ws.cell(r, j0 + 6, f"={_aire_min(Yp)}+{_aire_maj(Yp)}")
            ws.cell(r, j0 + 7, f"={_largeur_miroir(Yp)}")
            ws.cell(r, j0 + 8, f"={_debitance(Yp)}")
            ws.cell(r, j0 + 9, fpente(Yp, f"{cAp}{r}", f"{cTp}{r}", f"{cKp}{r}"))
        ws.cell(r, 24, f"=B{r}+D{r}")
        ws.cell(r, 25, f"=B{r}+N{r}")
        ws.cell(r, 26, f"=Y{r}-X{r}")
        ws.cell(r, 27, f"=Z{r}*100")
        ws.cell(r, 28, f"=IF(Z{r}<0.01,A{r},1E+9)")
        ws.cell(r, 29, f"=A{r}/1000")
        for j in range(1, 30):
            c = ws.cell(r, j)
            c.font = F_NORMAL
            c.number_format = "0.0000" if j in (8, 12, 18, 22) else "0.000"
        ws.cell(r, 1).number_format = "0"
        ws.cell(r, 27).number_format = "0.0"
    r1 = r0 + NB_PAS
    cl.remous = (r0, r1)
    # Enjeux
    re_ = r1 + 2
    ws.cell(re_, 1, "Enjeux").font = F_GRAS
    for j, h in enumerate(["Enjeu", "x (m)", "Z sans", "Z avec", "ΔZ (cm)", "Cote dommages", "Atteinte"], start=1):
        c = ws.cell(re_ + 1, j, h)
        c.font, c.fill = F_GRAS, FOND_ENTETE
    rr = re_ + 2
    plage_s = f"$A${r0}:$A${r1}"
    cl.enjeux_remous = (rr, rr + (cl.enjeux_ligne1 - cl.enjeux_ligne0))
    for k, rd in enumerate(range(cl.enjeux_ligne0, cl.enjeux_ligne1 + 1)):
        r = rr + k
        nom, x, cd = f"'Données'!A{rd}", f"'Données'!B{rd}", f"'Données'!C{rd}"
        ws.cell(r, 1, f"=IF({nom}=\"\",\"\",{nom})")
        ws.cell(r, 2, f"=IF({x}=\"\",\"\",MIN(MAX({x},0),L_bief))")

        def interp(colonne):
            plage = f"${colonne}${r0}:${colonne}${r1}"
            i = f"MATCH(B{r},{plage_s},1)"
            return (f"=IF(B{r}=\"\",\"\",IF({i}>={NB_PAS + 1},INDEX({plage},{NB_PAS + 1}),"
                    f"INDEX({plage},{i})+(B{r}-INDEX({plage_s},{i}))/Dx_r*(INDEX({plage},{i}+1)-INDEX({plage},{i}))))")
        ws.cell(r, 3, interp("X"))
        ws.cell(r, 4, interp("Y"))
        ws.cell(r, 5, f"=IF(B{r}=\"\",\"\",(D{r}-C{r})*100)")
        ws.cell(r, 6, f"=IF({cd}=\"\",\"\",{cd})")
        ws.cell(r, 7, f"=IF(OR(B{r}=\"\",F{r}=\"\"),\"\",IF(C{r}>F{r},\"déjà sans batardeau\","
                      f"IF(D{r}>F{r},\"atteinte avec batardeau\",\"non atteinte\")))")
        for j in range(1, 8):
            ws.cell(r, j).font = F_NORMAL
            ws.cell(r, j).number_format = "0.00" if j != 5 else "0.0"
    rd_ = rr + 6
    ws.cell(rd_, 1, "Distance d'influence ΔZ ≥ 1 cm (m)").font = F_GRAS
    c = ws.cell(rd_, 2, f"=IF(MIN(AB{r0}:AB{r1})>=1E+9,L_bief,MIN(AB{r0}:AB{r1}))")
    c.font, c.fill, c.number_format = F_GRAS, FOND_RESULTAT, "0"
    cl.nommer("Dist_influence", "Remous", f"B{rd_}")
    ws.cell(rd_, 3, "(égale à la longueur étudiée si ΔZ reste ≥ 1 cm partout)").font = F_NOTE
    ws.freeze_panes = "B6"
    for j in range(1, 30):
        ws.column_dimensions[col(j)].width = 11
    ws.column_dimensions["A"].width = 26


# ====================================================================== Résultats
def feuille_resultats(cl: Classeur):
    ws = cl.wb.create_sheet("Résultats", 1)
    _titre(ws, "Synthèse des résultats", "Tout est calculé à partir de la feuille « Données ».")
    pos = cl.calc_cols
    rr = cl.ligne_T["Crue de référence"]
    e0, e1 = cl.enjeux_remous
    ws_r = cl.wb["Risque"]
    lig_ev = {row[0].value: row[0].row for row in ws_r.iter_rows(min_col=1, max_col=1) if row[0].value}
    rs, rsub = lig_ev["Atteinte du seuil d'impact"], lig_ev["Submersion du batardeau"]
    lignes = [
        ("nom", "Barrage", "=Nom_barrage", "@", ""),
        ("Q", "Crue de référence Q (m³/s)", f"=Calculs!{pos['Q']}{rr}", "0", "période de retour T_ref"),
        ("Z3", "Cote aval (m NGF)", f"=Calculs!{pos['Z3']}{rr}", "0.00", ""),
        ("Zs", "Cote amont sans batardeau (m NGF)", f"=Calculs!{pos['Zs']}{rr}", "0.00", "méthode A"),
        ("Za", "Cote amont avec batardeau (m NGF)", f"=Calculs!{pos['Za']}{rr}", "0.00", "méthode A + ΔZ enveloppe"),
        ("dZ", "Surélévation au barrage – enveloppe (cm)", f"=Calculs!{pos['cmE']}{rr}", "0.0", "valeur retenue"),
        ("dZA", "   méthode A – Borda-Carnot (cm)", f"=Calculs!{pos['cmA']}{rr}", "0.0", ""),
        ("dZB", "   méthode B – Yarnell (cm)", f"=Calculs!{pos['cmB']}{rr}", "0.0", ""),
        ("dZC", "   méthode C – d'Aubuisson (cm)", f"=Calculs!{pos['cmC']}{rr}", "0.0", ""),
        ("dZD", "   méthode D – seuils (cm)", f"=Calculs!{pos['cmD']}{rr}", "0.0", ""),
        ("enj", "Surélévation maximale aux enjeux (cm)",
         f"=IF(COUNT(Remous!E{e0}:E{e1})=0,\"—\",MAX(Remous!E{e0}:E{e1}))", "0.0",
         "à la période de retour de la ligne d'eau"),
        ("dist", "Distance d'influence ΔZ ≥ 1 cm (km)", "=Dist_influence/1000", "0.0", ""),
        ("Qs", "Débit où ΔZ atteint le seuil (m³/s)", "=IF(Q_seuil>=1E+9,\"jamais atteint\",Q_seuil)", "0", ""),
        ("Ts", "   période de retour (ans)", f"=Risque!C{rs}", "0.0", ""),
        ("Ps", "   probabilité pendant les travaux", f"=Risque!D{rs}", "0.0%", ""),
        ("Qc", "Débit de submersion du batardeau (m³/s)", "=IF(Q_sub>=1E+9,\"jamais atteint\",Q_sub)", "0", ""),
        ("Pc", "   probabilité pendant les travaux", f"=Risque!D{rsub}", "0.0%", ""),
        ("V2s", "Vitesse dans les passes sans batardeau (m/s)", f"=Calculs!{pos['V2s']}{rr}", "0.00", ""),
        ("V2a", "Vitesse dans les passes avec batardeau (m/s)", f"=Calculs!{pos['V2a']}{rr}", "0.00", ""),
        ("f", "Part de l'aléa annuel couverte par les travaux", "=Frac_alea", "0.0%", ""),
        ("Qp", "Débit à tenir pour un risque P_acc pendant les travaux (m³/s)", "=Q_projet_travaux", "0", ""),
        ("verdict", "Pré-diagnostic", None, "@", "Seuil et probabilité acceptable : feuille Données."),
    ]
    ligne_de = {}
    r = 3
    for cle, lib, form, fmt, note in lignes:
        ligne_de[cle] = r
        ws.cell(r, 1, lib).font = F_NORMAL if lib.startswith("   ") else F_GRAS
        if form:
            c = ws.cell(r, 2, form)
            c.font = F_LIEN
            c.number_format = fmt
        ws.cell(r, 3, note).font = F_NOTE
        r += 1
    b = {k: f"B{v}" for k, v in ligne_de.items()}
    crit = f"IF(ISNUMBER({b['enj']}),{b['enj']}/100,{b['dZ']}/100)"
    c = ws.cell(ligne_de["verdict"], 2, (f"=IF({crit}<=Seuil_dz,\"Impact inférieur au seuil admissible\","
                                         f"IF({b['Ps']}<P_acc,\"Acceptable sous conditions (procédure crue)\","
                                         f"\"Mesures nécessaires\"))"))
    c.font, c.fill = F_GRAS, FOND_RESULTAT
    cl.resultats = ligne_de
    _largeurs(ws, {"A": 46, "B": 22, "C": 40})

    # Graphiques
    wsc = cl.wb["Calculs"]
    g0, g1 = cl.grille
    xref = Reference(wsc, min_col=_idx(pos["Q"]), min_row=g0, max_row=g1)
    ch = ScatterChart()
    ch.title = "Surélévation au barrage selon le débit"
    ch.x_axis.title = "Débit Q (m³/s)"
    ch.y_axis.title = "ΔZ (cm)"
    ch.style = 13
    ch.height, ch.width = 9, 18
    couleurs = {"cmA": "2A78D6", "cmB": "EB6834", "cmC": "1BAF7A", "cmD": "EDA100", "cmE": "111111"}
    noms = {"cmA": "A · Borda-Carnot", "cmB": "B · Yarnell", "cmC": "C · d'Aubuisson", "cmD": "D · seuils",
            "cmE": "Enveloppe"}
    for cle in ("cmA", "cmB", "cmC", "cmD", "cmE"):
        yref = Reference(wsc, min_col=_idx(pos[cle]), min_row=g0, max_row=g1)
        s = Series(yref, xref, title=noms[cle])
        s.marker.symbol = "none"
        s.graphicalProperties.line.solidFill = couleurs[cle]
        s.graphicalProperties.line.width = 28000 if cle == "cmE" else 16000
        s.smooth = False
        ch.series.append(s)
    _axes_visibles(ch)
    ws.add_chart(ch, "E3")

    ch2 = ScatterChart()
    ch2.title = "Cote amont au barrage selon le débit"
    ch2.x_axis.title = "Débit Q (m³/s)"
    ch2.y_axis.title = "Cote (m NGF)"
    ch2.height, ch2.width = 9, 18
    for cle, nom, coul in (("Z3", "Aval", "898781"), ("Zs", "Amont sans batardeau", "2A78D6"),
                           ("Za", "Amont avec batardeau", "EB6834"), ("cr", "Crête du batardeau", "D03B3B")):
        yref = Reference(wsc, min_col=_idx(pos[cle]), min_row=g0, max_row=g1)
        s = Series(yref, xref, title=nom)
        s.marker.symbol = "none"
        s.graphicalProperties.line.solidFill = coul
        s.graphicalProperties.line.width = 16000
        if cle == "cr":
            s.graphicalProperties.line.dashStyle = "dash"
        ch2.series.append(s)
    ch2.y_axis.scaling.min = cl.min_cotes  # à ajuster si les cotes du barrage changent beaucoup
    _axes_visibles(ch2)
    ws.add_chart(ch2, "E22")

    wsr = cl.wb["Remous"]
    r0, r1 = cl.remous
    xr = Reference(wsr, min_col=29, min_row=r0, max_row=r1)
    ch3 = ScatterChart()
    ch3.title = "Surélévation le long du bief (ligne d'eau étudiée)"
    ch3.x_axis.title = "Distance vers l'amont (km)"
    ch3.y_axis.title = "ΔZ (cm)"
    ch3.height, ch3.width = 9, 18
    s = Series(Reference(wsr, min_col=27, min_row=r0, max_row=r1), xr, title="ΔZ")
    s.marker.symbol = "none"
    s.graphicalProperties.line.solidFill = "EB6834"
    s.graphicalProperties.line.width = 20000
    ch3.series.append(s)
    _axes_visibles(ch3)
    ws.add_chart(ch3, "E41")

    ch4 = ScatterChart()
    ch4.title = "Lignes d'eau sans et avec batardeau"
    ch4.x_axis.title = "Distance vers l'amont (km)"
    ch4.y_axis.title = "Cote (m NGF)"
    ch4.height, ch4.width = 9, 18
    for c_, nom, coul in ((3, "Haut de berge", "898781"), (24, "Sans batardeau", "2A78D6"), (25, "Avec batardeau", "EB6834")):
        s = Series(Reference(wsr, min_col=c_, min_row=r0, max_row=r1), xr, title=nom)
        s.marker.symbol = "none"
        s.graphicalProperties.line.solidFill = coul
        s.graphicalProperties.line.width = 16000
        if c_ == 3:
            s.graphicalProperties.line.dashStyle = "dash"
        ch4.series.append(s)
    ch4.y_axis.scaling.min = cl.min_ligne
    _axes_visibles(ch4)
    ws.add_chart(ch4, "E60")


def _axes_visibles(ch):
    """openpyxl ≥ 3.1 masque les axes par défaut : on les rend visibles."""
    for ax in (ch.x_axis, ch.y_axis):
        ax.delete = False
    ch.legend.position = "b"


def _idx(lettre: str) -> int:
    from openpyxl.utils import column_index_from_string
    return column_index_from_string(lettre)


def _bornes_axes(cl: Classeur):
    """Bas des axes de cotes, déduit des données d'exemple (Excel et LibreOffice partent sinon de 0)."""
    import math
    from batcrue import EtudeBatardeau
    e = EtudeBatardeau(DEFAUTS)
    q_min = max(1.0, 0.3 * float(DEFAUTS["module"]))
    cl.min_cotes = float(math.floor(e.cote_aval(q_min) - 0.5))
    cl.min_ligne = float(math.floor(min(e.section_ref.cote_berge, e.cote_aval(e.Q_reference)) - 1.0))


def generer(sortie: Path) -> Path:
    cl = Classeur()
    _bornes_axes(cl)
    feuille_lisez_moi(cl)
    feuille_donnees(cl)
    feuille_tarage(cl)
    feuille_calculs(cl)
    feuille_risque(cl)
    feuille_remous(cl)
    feuille_resultats(cl)
    cl.wb.calculation.fullCalcOnLoad = True
    for ws in cl.wb.worksheets:
        ws.sheet_view.zoomScale = 90
    sortie.parent.mkdir(parents=True, exist_ok=True)
    cl.wb.save(sortie)
    return sortie


if __name__ == "__main__":
    cible = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent / "BatCrue_etude_batardeau.xlsx"
    print(generer(cible))
