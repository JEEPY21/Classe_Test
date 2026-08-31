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


# France Travail 'publieeDepuis' only accepts these values (in days).
_ALLOWED_SINCE = [1, 3, 7, 14, 31]


def _publiee_depuis(max_days: int) -> int:
    for v in _ALLOWED_SINCE:
        if v >= max_days:
            return v
    return 31


def _within_days(date_str: str, max_days: int) -> bool:
    if not date_str:
        return True
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - d) <= timedelta(days=max_days)
    except Exception:
        return True


def fetch_offers(keywords=None, contrats=None, max_days: int = 4, count: int = 10) -> list:
    """Fetch offers for one or more keywords / contract types, published within `max_days`.
    Merges + dedups results, sorts by publication date (newest first), caps at `count`.
    Raises on network/auth errors."""
    keywords = keywords or ["marketing", "analyste marketing"]
    contrats = contrats or ["CDI"]
    since = _publiee_depuis(max_days)
    token = _get_token()
    headers = {"Authorization": f"Bearer {token}"}
    collected = {}
    for kw in keywords:
        for ct in contrats:
            params = {
                "typeContrat": ct,
                "motsCles": kw,
                "paysContinent": "01",
                "publieeDepuis": since,
                "range": "0-49",
            }
            resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=25)
            if resp.status_code == 204:
                continue
            resp.raise_for_status()
            for o in (resp.json() or {}).get("resultats", []):
                if o.get("id") and o["id"] not in collected:
                    collected[o["id"]] = _project(o)
    offers = [o for o in collected.values() if _within_days(o["date_publication"], max_days)]
    offers.sort(key=lambda x: x.get("date_publication") or "", reverse=True)
    return offers[:count]
