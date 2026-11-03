# Note méthodologique – BatCrue

*Impact hydraulique d'un batardeau sur les crues au droit d'un barrage de navigation.*

## 1. Le problème posé

Pour entretenir ou reconstruire une passe d'un barrage de l'Oise, VNF isole cette passe par un
batardeau. Pendant toute la durée d'installation, le batardeau occupe environ **un tiers de la
largeur d'écoulement**. Tant que le barrage régule le plan d'eau, l'effet est nul : les vannes
restantes s'ouvrent davantage et la retenue normale (RN) est maintenue. Mais en crue, quand toutes
les vannes sont ouvertes (barrage « effacé »), le batardeau **rétrécit la section** : l'eau doit
accélérer dans les passes restantes, ce qui crée une perte de charge supplémentaire et **relève la
ligne d'eau à l'amont**. Cette surélévation se propage vers l'amont en s'atténuant (courbe de remous)
et peut aggraver l'inondation des enjeux riverains : c'est la garantie demandée par le service police
de l'eau.

L'outil répond à six questions :

1. de combien la ligne d'eau monte-t-elle au barrage, pour chaque débit ?
2. jusqu'où vers l'amont, et de combien aux enjeux (ponts, quartiers, barrage amont) ?
3. à partir de quel débit le seuil d'impact admissible est-il dépassé ?
4. quelle est la probabilité que ce débit survienne pendant la période d'installation ?
5. à partir de quel débit le batardeau est-il submergé ?
6. quelles vitesses, quels efforts et quelle protection contre l'érosion ?

## 2. Schéma de calcul

```
        amont                 barrage                  aval
  ───────────────┐   ┌──┐ passe ┌──┐ passe ┌──┐   ┌───────────────
   section 1     │   │▓▓│ libre │  │ libre │  │   │   section 3
   (approche)    │   │▓▓│  (2)  │  │  (2)  │  │   │ (ré-épanouissement)
  ───────────────┘   └──┘       └──┘       └──┘   └───────────────
                     batardeau   piles
   Z1 = ?            Z2 dans les passes            Z3 imposée par l'aval
```

Calcul en **régime permanent au débit de pointe** (hypothèse majorante pour les crues lentes de
l'Oise), section par section : la cote aval Z₃ est connue, on en déduit la cote dans les passes
Z₂ puis la cote amont Z₁, **sans** puis **avec** batardeau. La différence donne la surélévation.

## 3. Condition aval : hauteur normale de Manning-Strickler

$$Q = K\,A\,R_h^{2/3}\,\sqrt{I}$$

avec $K$ le coefficient de Strickler (m¹ᐟ³/s), $A$ la surface mouillée, $R_h = A/P$ le rayon
hydraulique et $I$ la pente. En lit composé (lit mineur + lit majeur), on applique la **méthode des
lits séparés** : $Q = \sqrt{I}\,\sum_i K_i A_i R_i^{2/3}$, et le coefficient de Coriolis
$\alpha = \dfrac{\sum K_{d,i}^3/A_i^2}{K_d^3/A^2}$ corrige l'énergie cinétique.

La cote aval vaut $Z_3 = \max(z_f + y_n\,;\,RN_{aval}) + \delta$ : le barrage aval maintient sa
retenue tant qu'il le peut ; $\delta$ est un décalage de sensibilité. On peut aussi saisir une
**loi hauteur-débit mesurée** à l'échelle aval (préférable si elle existe).

## 4. Régulation du barrage

Tant que les vannes ne sont pas toutes ouvertes, le barrage tient la retenue normale :

$$Z_{amont} = \max(RN\,;\,Z_1)$$

où $Z_1$ est la cote « vannes ouvertes ». Le **débit d'effacement** est celui pour lequel
$Z_1 = RN$. Avec batardeau, il est atteint plus tôt : entre les deux débits d'effacement, le
batardeau fait perdre la régulation alors que, sans lui, la RN serait tenue. C'est là que l'impact
apparaît brutalement.

## 5. Quatre méthodes de calcul au droit du barrage

### A. Bernoulli + pertes singulières (Borda-Carnot), avec contrôle critique

Élargissement brusque à la sortie des passes (perte de Borda-Carnot) :

$$Z_2 + \frac{V_2^2}{2g} = Z_3 + \frac{V_3^2}{2g} + \frac{(V_2 - V_3)^2}{2g}$$

Contraction à l'entrée (coefficient $\xi$ : 0,1 progressive, 0,3 typique, 0,6 brusque) :

$$Z_1 + \frac{V_1^2}{2g} = Z_2 + \frac{V_2^2}{2g} + \xi\,\frac{V_2^2 - V_1^2}{2g}$$

Si aucune solution fluviale n'existe dans les passes, l'écoulement est **étranglé** : la hauteur
critique $y_c = \left(Q^2/(g\,b_2^2)\right)^{1/3}$ s'établit dans les passes (principe de Bélanger)
et $E_2 = z_s + \tfrac{3}{2} y_c$. Sans perte, on retrouve exactement la loi du seuil épais
$Q = 0{,}385\,b\sqrt{2g}\,H^{3/2}$ (vérifié par les tests).

Avec des passes de cotes de seuil différentes, le débit se répartit entre groupes de passes de
façon que tous partagent la même charge amont.

### B. Formule de Yarnell (1934)

Calée sur des essais de piles de pont (contractions de 11,7 à 50 %), utilisée par HEC-RAS :

$$\Delta h = 2K\,(K + 10\,\omega - 0{,}6)\,(\alpha + 15\,\alpha^4)\,\frac{V_3^2}{2g},\qquad \omega = \frac{V_3^2}{2g\,y_3}$$

$\alpha$ = surface obstruée / surface totale à l'aval ; $K$ = coefficient de forme (0,90 nez
arrondi, 1,05 triangulaire, 1,25 carré). Domaine de validité : $\alpha \le 0{,}5$ et écoulement non
étranglé ; hors domaine, le résultat est affiché en pointillé et exclu de l'enveloppe.

### C. Formule de d'Aubuisson (1840)

Formule française classique de l'exhaussement dû aux piles :

$$Q = K_A\,\sum_i b_i\,(Z_3 - z_{s,i})\,\sqrt{2g\,\Delta h + V_1^2}$$

résolue par point fixe ($V_1$ dépend de $Z_3 + \Delta h$). $K_A = 1$ correspond à la perte totale de
l'énergie cinétique dans le rétrécissement (prudent) ; les valeurs publiées pour des piles à nez
carré vont d'environ 0,87 à 1,07 selon le taux de contraction.

### D. Lois de seuil dénoyé / noyé (passes en parallèle)

Formulation usuelle en France (logiciels SIC et Cassiopée) :

$$\text{dénoyé } (h_2 \le \tfrac{2}{3}h_1) : Q = \mu\,b\,\sqrt{2g}\,h_1^{3/2} \qquad \text{noyé} : Q = \mu_s\,b\,h_2\,\sqrt{2g\,(h_1 - h_2)}$$

avec $\mu_s = \tfrac{3\sqrt{3}}{2}\,\mu$ pour assurer la continuité entre les deux régimes
($\mu = 0{,}385 \Rightarrow \mu_s = 1$).

### Enveloppe

Les quatre méthodes reposent sur des hypothèses différentes (récupération d'énergie à l'aval pour A,
calage expérimental pour B, perte totale de l'énergie cinétique pour C et D). Leur accord est un
contrôle de vraisemblance ; on retient **l'enveloppe des méthodes valides** (valeur la plus
défavorable). La cote « sans batardeau » de référence est celle de la méthode A.

Les coefficients du cas « avec batardeau » ($\xi$, $K$) sont pondérés par les largeurs obstruées
(piles existantes / batardeau) ; sans obstruction, l'impact est exactement nul.

## 6. Propagation vers l'amont : courbe de remous

Équation de Bernoulli entre deux sections successives (méthode des pas standards), intégrée de
l'aval vers l'amont en régime fluvial :

$$Z_u + \alpha_u\frac{V_u^2}{2g} = Z_d + \alpha_d\frac{V_d^2}{2g} + \Delta x\,\bar J + C\,\left|\alpha_u\frac{V_u^2}{2g} - \alpha_d\frac{V_d^2}{2g}\right|, \qquad \bar J = \left(\frac{2Q}{K_{d,u} + K_{d,d}}\right)^2$$

($C$ = 0,1 en contraction, 0,3 en élargissement pour des profils tabulés). On calcule deux lignes
d'eau (départ $Z_{amont}$ sans et avec batardeau) et leur différence $\Delta Z(x)$, interpolée aux
enjeux. Le classeur Excel intègre directement l'équation de **Bresse**
$\dfrac{dy}{dx} = \dfrac{I - J}{1 - Fr^2}$ (schéma de Heun) ; l'écart sur $\Delta Z$ avec
l'application est de l'ordre du millimètre.

## 7. Hydrologie et risque pendant les travaux

**Loi de Gumbel** des débits maximaux annuels (usage courant en France, HydroPortail) :

$$F(Q) = \exp\!\left[-\exp\!\left(-\frac{Q - u}{\beta}\right)\right],\qquad Q_T = u - \beta\,\ln\!\left(-\ln\left(1 - \frac{1}{T}\right)\right)$$

Ajustement possible par les moments ($\beta = \sqrt{6}\,s/\pi$, $u = \bar Q - 0{,}5772\,\beta$), par
le maximum de vraisemblance ou par moindres carrés sur un tableau $Q(T)$.

**Risque pendant les travaux.** Une loi de Gumbel équivaut à des dépassements poissonniens de taux
annuel $\lambda(Q) = \exp(-(Q - u)/\beta)$. Si la période d'installation couvre une fraction $f$ de
l'aléa annuel :

$$P(\text{au moins une crue} > Q \text{ pendant les travaux}) = 1 - e^{-\lambda(Q)\,f}$$

$f$ = 1 pour une année complète ; sinon $f = \sum_{\text{jours}} w_{mois}/n_{jours\,du\,mois}$
avec des poids mensuels $w$ (uniformes par défaut, ce qui est prudent pour des travaux d'été ; à
calculer sur la chronique de la station pour tenir compte des crues d'hiver de l'Oise). On en
déduit aussi le débit que le dispositif doit tenir pour un risque accepté donné :
$Q = u - \beta\,\ln\left(-\ln(1 - P)/f\right)$.

## 8. Simulation d'un événement de crue

Hydrogramme synthétique en cloche (forme de type SOCOSE) $Q(t) = Q_b + (Q_p - Q_b)\,\dfrac{2s^4}{1 + s^8}$,
$s = t/t_{pic}$, ou hydrogramme importé (CSV). Calcul **quasi-permanent** (succession d'états
permanents), adapté aux crues lentes : il donne les instants de franchissement de la cote d'alerte
(crête − revanche) et de la crête, donc **le délai disponible pour mettre le chantier en sécurité**.

## 9. Vitesses, érosion et efforts (ordres de grandeur)

* **Vitesses** dans les passes restantes et survitesse locale au nez du batardeau (facteur ≈ 1,5).
* **Isbash** (Guide Enrochement CIRIA/CUR/CETMEF) : $D = \dfrac{V^2}{2g\,\Delta\,C^2}$,
  $\Delta = (\rho_s - \rho_w)/\rho_w$, $C$ = 0,86 (blocs exposés) ou 1,20 (blocs encastrés).
* **Affouillement de contraction** (Laursen, repris par HEC-18), si le fond est affouillable :
  $y_2/y_1 = (W_1/W_2)^{k_1}$, $k_1$ = 0,59 à 0,69.
* **Poussée hydrostatique** $F = \tfrac{1}{2}\rho g h^2$ (enceinte à sec) et pression d'arrêt
  $\tfrac{1}{2}\rho V^2 h$.
* **Renard** (règle de Lane) si le batardeau repose sur sol meuble :
  $L_v + L_h/3 \ge C_L\,\Delta H$.

Ces vérifications ne remplacent ni la note de calcul du fournisseur ni l'étude géotechnique.

## 10. Incertitudes

* **Sensibilité** « un paramètre à la fois » (diagramme en tornade) : Strickler ±20 %, débit ±10 %,
  cote aval ±0,20 m, pente ±30 %, coefficients $\xi$, $K_A$, $\mu$, $K$, emprise.
* **Monte-Carlo** : tirages simultanés de tous ces paramètres → médiane, 90ᵉ et 95ᵉ centiles de
  ΔZ et probabilité de dépasser le seuil. Utile car la crue centennale elle-même est incertaine
  (à Venette, les estimations publiées vont d'environ 620 à 770 m³/s selon les études).

## 11. Vérifications réalisées

* **44 tests automatiques** (`pytest`) sur des cas analytiques : hauteur normale et critique,
  régime uniforme conservé par la courbe de remous, courbe M1 qui tend vers la hauteur normale,
  équivalence méthode A / loi de seuil théorique en écoulement dénoyé, continuité seuil
  dénoyé/noyé, formules de Yarnell et de d'Aubuisson recalculées à la main, impact nul sans
  obstruction, Gumbel, probabilités, lecture Hub'Eau simulée.
* **Double calcul indépendant** : le classeur Excel (22 807 formules) recalculé par LibreOffice
  et comparé au moteur Python : **69 contrôles sur 69 conformes** (écarts inférieurs au
  millimètre sur les cotes), y compris après modification des données.

## 12. Hypothèses et limites

* Monodimensionnel, régime permanent au débit de pointe (pas d'effet de laminage).
* Tout le débit transite par les passes du barrage (hypothèse majorante : un écoulement par le lit
  majeur autour de l'ouvrage réduirait l'impact).
* Géométrie simplifiée (section type ou profils tabulés) : la qualité des données conditionne le
  résultat.
* Le barrage amont n'est pas modélisé : la surélévation calculée à son pied indique s'il faut
  prolonger l'étude au bief suivant.
* Outil de **pré-diagnostic** : pour l'instruction réglementaire, il est conseillé de confirmer
  les résultats avec le modèle hydraulique de référence de la vallée (voir « Autres méthodes »).

## 13. Références

* Barré de Saint-Venant A. (1871). *Théorie du mouvement non permanent des eaux.* Comptes rendus de
  l'Académie des sciences, 73.
* Bélanger J.-B. (1828). *Essai sur la solution numérique de quelques problèmes relatifs au
  mouvement permanent des eaux courantes.* Paris.
* Bresse J. (1860). *Cours de mécanique appliquée, 2ᵉ partie : hydraulique.* Paris.
* d'Aubuisson de Voisins J.-F. (1840). *Traité d'hydraulique à l'usage des ingénieurs.* Paris.
* Carlier M. (1972). *Hydraulique générale et appliquée.* Eyrolles.
* Lencastre A. (1999). *Hydraulique générale.* Eyrolles.
* Graf W. H., Altinakar M. S. (2000). *Hydraulique fluviale.* Traité de génie civil, vol. 16, PPUR.
* Idel'cik I. E. (1969). *Mémento des pertes de charge.* Eyrolles.
* Chow V. T. (1959). *Open-Channel Hydraulics.* McGraw-Hill.
* Yarnell D. L. (1934). *Bridge piers as channel obstructions.* USDA Technical Bulletin 442.
* Charbeneau R. J., Holley E. R. (2001). *Backwater effects of bridge piers in subcritical flow.*
  Rapport FHWA/TX-0-1805, Université du Texas à Austin.
* US Army Corps of Engineers, HEC. *HEC-RAS Hydraulic Reference Manual* (chapitre « Modeling Bridges »).
* CIRIA, CUR, CETMEF (2009). *Guide Enrochement : l'utilisation des enrochements dans les ouvrages
  hydrauliques* (version française du Rock Manual).
* Arneson L. A. et al. (2012). *Evaluating Scour at Bridges*, HEC-18, 5ᵉ éd., FHWA.
* Laursen E. M. (1960). Scour at bridge crossings. *Journal of the Hydraulics Division*, ASCE, 86.
* Lane E. W. (1935). Security from under-seepage – masonry dams on earth foundations.
  *Transactions ASCE*, 100.
* Gumbel E. J. (1958). *Statistics of Extremes.* Columbia University Press.
