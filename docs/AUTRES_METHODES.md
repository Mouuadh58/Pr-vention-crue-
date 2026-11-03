# Autres méthodes et solutions existantes

BatCrue est un outil de **pré-diagnostic** : il donne en quelques secondes un ordre de grandeur
fiable, compare des variantes et prépare le dialogue avec le service police de l'eau. Selon l'enjeu,
d'autres approches existent ; elles se combinent plutôt qu'elles ne s'opposent.

## 1. Démarche recommandée, par niveaux

| Niveau | Approche | Délai typique | Quand l'utiliser |
|---|---|---|---|
| 1 | **Pré-diagnostic 1D simplifié** (BatCrue, Cassiopée) | minutes | Choisir l'emprise, la période, les seuils d'alerte ; savoir si l'impact est négligeable ou non |
| 2 | **Modèle 1D de la vallée** (HEC-RAS, MASCARET) avec le batardeau | quelques jours | Dossier réglementaire : impact sur toute la vallée, plusieurs crues, enjeux précis |
| 3 | **Modèle 2D local** (HEC-RAS 2D, TELEMAC-2D) | 1 à 3 semaines | Vitesses autour du batardeau, courants traversiers à l'entrée de l'écluse, affouillement, lit majeur actif |
| 4 | **Modèle physique** ou **CFD 3D** (OpenFOAM, FLOW-3D) | mois | Efforts et affouillements locaux d'un ouvrage exceptionnel ; rarement justifié pour un batardeau temporaire |
| + | **Mesures opérationnelles** | — | Dans tous les cas : surveillance Vigicrues, seuils d'alerte, procédure de retrait, période d'étiage |

**La solution la plus efficace est souvent de réutiliser un modèle existant.** Les études de PPRI,
les programmes d'actions de prévention des inondations portés par l'Entente Oise-Aisne et les
études de VNF (mise au gabarit de l'Oise, reconstruction des barrages) ont généralement produit un
modèle hydraulique calé de l'Oise. Y insérer le batardeau (obstruction dans les profils en travers)
et comparer les lignes d'eau pour Q10, Q100 et la crue de référence du PPRI donne le document le plus
convaincant pour l'instruction. BatCrue sert alors à préparer, contrôler et expliquer ce calcul.

## 2. Comparatif des outils

| Outil | Type | Coût | Points forts | Limites |
|---|---|---|---|---|
| **BatCrue** (cet outil, Python + Excel) | 1D simplifié, 4 méthodes, risque, temps réel | Gratuit | Instantané, transparent (note de calcul pas à pas), double calcul Excel/Python, probabilité pendant les travaux, lecture Hub'Eau | Géométrie simplifiée, régime permanent, pas de modèle de toute la vallée |
| **Cassiopée** (INRAE / OFB, web) | Calculettes hydrauliques : lois d'ouvrages, courbes de remous, sections | Gratuit | Référence française pour les lois de seuils et vannes, très simple | Pas d'analyse de risque ni d'enveloppe de méthodes ; calculs à enchaîner à la main |
| **HEC-RAS** (US Army Corps of Engineers) | 1D et 2D, permanent et transitoire | Gratuit | Standard des bureaux d'études, module ponts et obstructions (Yarnell, énergie, quantité de mouvement), cartographie | Nécessite profils en travers ou MNT ; plusieurs jours de prise en main |
| **TELEMAC-MASCARET** (consortium, open source) | 1D (MASCARET), 2D (TELEMAC-2D), 3D | Gratuit | Codes de référence français (EDF R&D, Cerema, Artelia…), très complets | Mise en œuvre lourde (maillage, calage) |
| **MIKE+ / MIKE 21** (DHI), **InfoWorks ICM**, **TUFLOW** | 1D/2D commerciaux | Licence | Interfaces abouties, utilisés par certains bureaux d'études | Coût des licences |
| **Modèle existant de l'Oise** (DDT, Entente Oise-Aisne, VNF) | 1D/2D calé | Accès à demander | Déjà calé sur les crues historiques, reconnu par les services de l'État | Dépend de la disponibilité des données et du prestataire |
| **Modèle physique réduit** (laboratoire d'hydraulique) | Physique | Élevé | Mesure directe des niveaux, vitesses, efforts | Coût et délai disproportionnés pour un ouvrage temporaire |

## 3. Retours d'expérience utiles chez VNF

* **Batardeaux des sept barrages de l'Oise** : les avis de marché de 2024 et 2025 (BOAMP) portent sur
  la fourniture de batardeaux, notamment flottants, pour les passes navigables et les pertuis de
  Venette, Verberie, Sarron, Creil, Boran-sur-Oise, L'Isle-Adam et Pontoise. Les cahiers des charges
  donnent les dimensions, cotes et procédures de pose et de dépose à reprendre dans l'outil.
* **Reconstruction des barrages de l'Aisne et de la Meuse** (programme de 29 barrages manuels) :
  chantiers réalisés en batardeaux par phases, avec des dossiers « loi sur l'eau » qui peuvent servir
  de modèle de note hydraulique.
* **Reconstructions de barrages sur la Seine et l'Yonne** (par exemple Vaux dans l'Yonne, avis de
  l'Autorité environnementale de 2018, ou Le Coudray-Montceaux sur la Seine, retour d'expérience
  publié par le Comité français des barrages et réservoirs) : traitement des impacts hydrauliques en
  phase travaux.

## 4. Données à rassembler pour passer de l'exemple au cas réel

| Donnée | Source probable |
|---|---|
| Largeur et cote de seuil de chaque passe, largeur des piles, cote de retenue normale | Plans d'ouvrage et consignes d'exploitation VNF |
| Consignes de manœuvre en crue, débit d'effacement | Règlement d'eau / consignes de crue du barrage |
| Relevés des échelles amont et aval en crue (loi hauteur-débit aval) | Supervision VNF, archives des crues |
| Profils en travers et pente du bief amont | Levés bathymétriques VNF, études PPRI |
| Débits de crue (QIX), maxima annuels, saisonnalité | HydroPortail, API Hub'Eau (page 3 de l'outil) |
| Enjeux et cotes de premiers dommages | PPRI, Entente Oise-Aisne, communes |
| Caractéristiques du batardeau (emprise, cote d'arase, délai de dépose) | Fournisseur, cahier des charges du marché |
| Seuil d'impact admissible | Service police de l'eau (DDT de l'Oise, DRIEAT pour le Val-d'Oise) |

## 5. Liens

* Cassiopée : <https://cassiopee.g-eau.fr>
* HEC-RAS : <https://www.hec.usace.army.mil/software/hec-ras/>
* TELEMAC-MASCARET : <http://www.opentelemac.org>
* HydroPortail (débits et statistiques) : <https://www.hydro.eaufrance.fr>
* API Hub'Eau Hydrométrie : <https://hubeau.eaufrance.fr/page/api-hydrometrie>
* Vigicrues : <https://www.vigicrues.gouv.fr>
* Entente Oise-Aisne : <https://www.oise-aisne.net>
