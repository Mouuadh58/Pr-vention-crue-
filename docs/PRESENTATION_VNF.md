# Présenter BatCrue à l'équipe VNF

Guide pour présenter l'outil en entretien ou en réunion (5 minutes de démonstration).

## Le message en 30 secondes

> « Pour les batardeaux des barrages de l'Oise, la police de l'eau demande de démontrer que
> l'ouvrage n'aggrave pas les crues. J'ai développé BatCrue, un outil qui calcule en temps réel la
> surélévation de la ligne d'eau causée par le batardeau, jusqu'où elle remonte, à partir de quel
> débit elle dépasse le seuil admissible et avec quelle probabilité pendant la période de travaux.
> Il compare quatre méthodes reconnues, produit une note de calcul imprimable, existe aussi en
> version Excel vérifiée par double calcul, et lit les débits officiels en temps réel. »

## Déroulé de la démonstration

1. **Page 1 · Données** : montrer le schéma du barrage vu de l'amont (batardeau dans la passe
   navigable), la saisie des passes et la note de calcul pas à pas (formules avec les valeurs).
2. **Page 2 · Résultats** : lire le pré-diagnostic, puis déplacer le curseur de débit :
   * en dessous du débit d'effacement, l'impact est **nul** (le barrage tient sa retenue) ;
   * juste au-dessus, l'impact **saute** : le batardeau fait perdre la régulation plus tôt ;
   * réduire l'emprise du batardeau avec le second curseur : l'impact diminue immédiatement.
3. **Onglet « Risque pendant travaux »** : probabilité que le débit seuil survienne pendant
   l'installation, et débit que le dispositif doit tenir pour un risque accepté.
4. **Onglet « Crue simulée »** : délai entre l'alerte et la submersion du batardeau, donc le temps
   disponible pour mettre le chantier en sécurité.
5. **Onglet « Sensibilité & incertitudes »** : montrer que le résultat est robuste (Monte-Carlo).
6. **Exports** : rapport HTML imprimable et classeur Excel à formules.

## Ce qui fait la différence

* **Physique française et reconnue** : Manning-Strickler, Bernoulli et Borda-Carnot, Bélanger
  (hauteur critique), Bresse (courbe de remous), d'Aubuisson (piles de pont), lois de seuil
  dénoyé/noyé, loi de Gumbel.
* **Prudence assumée** : enveloppe de quatre méthodes, domaines de validité affichés, analyse
  d'incertitude.
* **Vérifié** : 44 tests automatiques et double calcul Excel/Python (69 contrôles sur 69 conformes).
* **Opérationnel** : régulation du barrage prise en compte, seuils d'alerte du chantier, lecture des
  débits Hub'Eau, procédure crue.
* **Lucide sur ses limites** : c'est un pré-diagnostic ; pour le dossier réglementaire, la bonne
  pratique est de confirmer avec le modèle hydraulique de référence de la vallée.

## Questions à poser à l'équipe

* Sur quel barrage et quelle passe porte le premier batardeau ? Quelles dates d'installation ?
* Disposez-vous des plans des passes (largeurs, cotes de seuil) et des consignes de manœuvre en crue ?
* Avez-vous les relevés des échelles amont et aval lors des dernières crues ?
* Le service police de l'eau a-t-il déjà indiqué un seuil d'impact admissible ou une crue de référence ?
* Un modèle hydraulique de l'Oise existe-t-il déjà (PPRI, Entente Oise-Aisne, études VNF) ?
* Quel est le délai de pose et de dépose du batardeau commandé ?

## Propositions de missions de stage

1. Renseigner les données réelles des sept barrages et produire une note par barrage.
2. Comparer BatCrue au modèle hydraulique de référence et caler les coefficients.
3. Rédiger la procédure crue du chantier (seuils Vigicrues, délais, responsabilités).
4. Préparer la partie hydraulique du dossier « loi sur l'eau ».
