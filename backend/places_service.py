"""Google Places API (New) — source SECONDAIRE de confirmation (site web + téléphone public).
RÈGLES : aucune donnée inventée ; si aucune correspondance, renvoie des valeurs nulles honnêtes.
Clé stockée en variable d'environnement uniquement. Champs demandés limités (SKU Enterprise) pour maîtriser le coût."""
import os
import httpx

API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
BASE = "https://places.googleapis.com/v1"
TIMEOUT = 20.0

_SEARCH_FIELDMASK = "places.id,places.displayName,places.formattedAddress,places.websiteUri,places.nationalPhoneNumber"
_DETAILS_FIELDMASK = "displayName,formattedAddress,websiteUri,nationalPhoneNumber"


async def lookup_company_place(company_name: str, address: str):
    """Text Search (New) puis Place Details en repli si un champ manque.
    Renvoie (data, api_calls). data = {match, websiteUri, nationalPhoneNumber}."""
    if not API_KEY:
        raise RuntimeError("Clé Google Places absente (GOOGLE_MAPS_API_KEY)")
    text_query = f"{company_name}, {address}".strip().strip(",").strip()
    headers_search = {"Content-Type": "application/json", "X-Goog-Api-Key": API_KEY,
                      "X-Goog-FieldMask": _SEARCH_FIELDMASK}
    headers_details = {"Content-Type": "application/json", "X-Goog-Api-Key": API_KEY,
                       "X-Goog-FieldMask": _DETAILS_FIELDMASK}
    calls = 0
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{BASE}/places:searchText", headers=headers_search,
                              json={"textQuery": text_query, "languageCode": "fr",
                                    "regionCode": "FR", "maxResultCount": 1})
        calls += 1
        r.raise_for_status()
        places = r.json().get("places", [])
        if not places:
            return {"match": None, "websiteUri": None, "nationalPhoneNumber": None}, calls
        best = places[0]
        website = best.get("websiteUri")
        phone = best.get("nationalPhoneNumber")
        place_id = best.get("id")
        if (not website or not phone) and place_id:
            d = await client.get(f"{BASE}/places/{place_id}", headers=headers_details)
            calls += 1
            d.raise_for_status()
            det = d.json()
            website = website or det.get("websiteUri")
            phone = phone or det.get("nationalPhoneNumber")
        return {
            "match": {"placeId": place_id,
                      "name": (best.get("displayName") or {}).get("text"),
                      "formattedAddress": best.get("formattedAddress")},
            "websiteUri": website,
            "nationalPhoneNumber": phone,
        }, calls
