"""Accès aux données hydrométriques officielles via l'API publique Hub'Eau.

API « Hydrométrie » v2 (https://hubeau.eaufrance.fr/page/api-hydrometrie) :
  * ``referentiel/stations`` : liste des stations ;
  * ``observations_tr``      : observations en temps réel (hauteur H en mm, débit Q en l/s) ;
  * ``obs_elab``             : observations élaborées, dont le débit moyen
    journalier QmnJ (l/s) sur tout l'historique disponible.

Aucune clé n'est nécessaire. Les fonctions lèvent ``HubEauErreur`` avec un
message explicite en cas d'échec (réseau, code inconnu, données absentes).
"""
from __future__ import annotations

from datetime import date, datetime

import requests

BASE = "https://hubeau.eaufrance.fr/api/v2/hydrometrie"
DELAI = 30  # secondes


class HubEauErreur(RuntimeError):
    pass


def _get(chemin: str, params: dict, session=None) -> dict:
    url = f"{BASE}/{chemin}"
    getter = session.get if session is not None else requests.get
    try:
        r = getter(url, params=params, timeout=DELAI)
    except requests.RequestException as exc:  # pragma: no cover - dépend du réseau
        raise HubEauErreur(f"Hub'Eau injoignable ({exc.__class__.__name__}). Vérifiez la connexion.") from exc
    if r.status_code not in (200, 206):
        raise HubEauErreur(f"Hub'Eau a répondu {r.status_code} : {r.text[:200]}")
    try:
        return r.json()
    except ValueError as exc:
        raise HubEauErreur("Réponse Hub'Eau illisible.") from exc


def _pages(chemin: str, params: dict, session=None, max_pages: int = 20) -> list:
    """Récupère toutes les pages (lien ``next``) d'une requête Hub'Eau."""
    donnees = []
    js = _get(chemin, params, session)
    donnees.extend(js.get("data", []))
    n = 1
    suivant = js.get("next")
    getter = session.get if session is not None else requests.get
    while suivant and n < max_pages:
        try:
            r = getter(suivant, timeout=DELAI)
            js = r.json()
        except (requests.RequestException, ValueError) as exc:  # pragma: no cover
            raise HubEauErreur(f"Pagination Hub'Eau interrompue : {exc}") from exc
        donnees.extend(js.get("data", []))
        suivant = js.get("next")
        n += 1
    return donnees


def stations(code_departement: str | None = None, filtre_cours_eau: str | None = "Oise",
             en_service: bool = True, session=None) -> list[dict]:
    """Stations hydrométriques d'un département, filtrées sur le nom du cours d'eau."""
    params = {"format": "json", "size": 1000,
              "fields": "code_station,libelle_station,libelle_cours_eau,en_service,code_site"}
    if code_departement:
        params["code_departement"] = code_departement
    if en_service:
        params["en_service"] = "true"
    data = _get("referentiel/stations", params, session).get("data", [])
    if filtre_cours_eau:
        f = filtre_cours_eau.lower()
        data = [d for d in data if f in str(d.get("libelle_cours_eau") or "").lower()
                or f in str(d.get("libelle_station") or "").lower()]
    return sorted(data, key=lambda d: str(d.get("libelle_station")))


def _date_iso(texte: str) -> datetime:
    return datetime.fromisoformat(str(texte).replace("Z", "+00:00"))


def observations_temps_reel(code_station: str, grandeur: str = "Q", taille: int = 2000,
                            session=None) -> list[tuple[datetime, float]]:
    """Observations récentes (les plus récentes d'abord). Débits convertis en m³/s, hauteurs en m."""
    params = {"code_entite": code_station.strip(), "grandeur_hydro": grandeur, "size": taille,
              "sort": "desc", "format": "json", "fields": "date_obs,resultat_obs"}
    data = _pages("observations_tr", params, session, max_pages=5)
    if not data:
        raise HubEauErreur(f"Aucune observation temps réel « {grandeur} » pour la station {code_station}.")
    facteur = 1000.0
    serie = [(_date_iso(d["date_obs"]), float(d["resultat_obs"]) / facteur)
             for d in data if d.get("resultat_obs") is not None]
    return sorted(serie, key=lambda t: t[0], reverse=True)


def debit_actuel(code_station: str, session=None) -> tuple[datetime, float]:
    """Dernier débit observé (date, m³/s)."""
    return observations_temps_reel(code_station, "Q", taille=50, session=session)[0]


def debits_journaliers(code_station: str, debut: date, fin: date, session=None):
    """Débits moyens journaliers QmnJ (m³/s) : renvoie (liste de dates, liste de débits)."""
    params = {"code_entite": code_station.strip(), "grandeur_hydro_elab": "QmnJ",
              "date_debut_obs_elab": debut.isoformat(), "date_fin_obs_elab": fin.isoformat(),
              "size": 20000, "format": "json", "fields": "date_obs_elab,resultat_obs_elab"}
    data = _pages("obs_elab", params, session, max_pages=10)
    if not data:
        raise HubEauErreur(f"Aucun débit journalier pour la station {code_station} sur la période.")
    dates, debits = [], []
    for d in data:
        v = d.get("resultat_obs_elab")
        if v is None:
            continue
        dates.append(date.fromisoformat(str(d["date_obs_elab"])[:10]))
        debits.append(float(v) / 1000.0)
    ordre = sorted(range(len(dates)), key=lambda i: dates[i])
    return [dates[i] for i in ordre], [debits[i] for i in ordre]
