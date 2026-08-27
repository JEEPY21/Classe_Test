"""France Travail « Offres d'emploi v2 » — pure REST, NO AI.
Fetches CDI marketing offers in France. Credentials via env vars."""
import os
import requests
from datetime import datetime, timezone, timedelta

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
SCOPE = "api_offresdemploiv2 o2dsoffre"

_token = {}


def _get_token() -> str:
    now = datetime.now(timezone.utc)
    if _token.get("value") and now < _token.get("expires_at", now):
        return _token["value"]
    resp = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": os.environ["FRANCE_TRAVAIL_CLIENT_ID"],
        "client_secret": os.environ["FRANCE_TRAVAIL_CLIENT_SECRET"],
        "scope": SCOPE,
    }, timeout=20)
    resp.raise_for_status()
    body = resp.json()
    lifetime = max(int(body.get("expires_in", 300)) - 60, 30)
    _token["value"] = body["access_token"]
    _token["expires_at"] = now + timedelta(seconds=lifetime)
    return _token["value"]


def _project(offer: dict) -> dict:
    return {
        "id": offer.get("id"),
        "intitule": offer.get("intitule") or "",
        "entreprise": (offer.get("entreprise") or {}).get("nom") or "",
        "lieu": (offer.get("lieuTravail") or {}).get("libelle") or "",
        "date_publication": offer.get("dateCreation") or offer.get("dateActualisation") or "",
        "description": offer.get("description") or "",
    }


def fetch_offers(mots_cles: str = "marketing", type_contrat: str = "CDI", count: int = 10) -> list:
    """Return up to `count` offers. Raises on network/auth errors."""
    params = {
        "typeContrat": type_contrat,
        "motsCles": mots_cles,
        "paysContinent": "01",
        "range": f"0-{max(count - 1, 0)}",
    }
    resp = requests.get(SEARCH_URL, params=params,
                        headers={"Authorization": f"Bearer {_get_token()}"}, timeout=25)
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    results = (resp.json() or {}).get("resultats", [])
    return [_project(o) for o in results if o.get("id")][:count]
