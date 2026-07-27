"""Discovery Agent V1 — recherche d'entreprises réelles via l'API Recherche d'Entreprises (data.gouv.fr / Sirene INSEE).
RÈGLES : aucune donnée inventée, scoring figé, source citée, RGPD de base. Aucune génération LLM d'entreprises."""
import httpx
from difflib import SequenceMatcher
from datetime import datetime, timezone

API_URL = "https://recherche-entreprises.api.gouv.fr/search"
TIMEOUT = 10.0
MAX_API_CALLS = 50
MAX_RESULTS = 20
PER_PAGE = 25

now_iso = lambda: datetime.now(timezone.utc).isoformat()

# ---- Mapping secteur -> code NAF (déterministe, corrigeable par l'utilisateur) ----
NAF_LABELS = {
    "69.20Z": "Activités comptables", "69.10Z": "Activités juridiques",
    "70.22Z": "Conseil pour les affaires et la gestion", "73.11Z": "Activités des agences de publicité",
    "62.01Z": "Programmation informatique", "62.02A": "Conseil en systèmes et logiciels informatiques",
    "78.10Z": "Activités des agences de placement de main-d'œuvre", "71.11Z": "Activités d'architecture",
    "66.19B": "Autres activités auxiliaires de services financiers", "70.21Z": "Conseil en relations publiques et communication",
}
SECTOR_TO_NAF = [
    (["expertise comptable", "expert comptable", "comptable", "comptabilité", "cabinet comptable"], "69.20Z"),
    (["avocat", "juridique", "droit", "notaire", "cabinet juridique"], "69.10Z"),
    (["conseil", "consultant", "cabinet de conseil", "conseil en gestion", "stratégie"], "70.22Z"),
    (["ressources humaines", "recrutement", "rh", "cabinet rh"], "78.10Z"),
    (["agence de communication", "communication", "publicité", "agence marketing", "marketing"], "73.11Z"),
    (["logiciel", "éditeur de logiciels", "développement informatique", "programmation"], "62.01Z"),
    (["architecte", "architecture"], "71.11Z"),
    (["relations publiques", "rp"], "70.21Z"),
]
# Codes NAF voisins par cible (proposés, à valider avant production)
ADJACENT_NAF = {
    "69.20Z": ["70.22Z", "69.10Z", "66.19B"],
    "69.10Z": ["69.20Z", "70.22Z"],
    "70.22Z": ["69.20Z", "73.11Z", "62.02A"],
    "73.11Z": ["70.21Z", "70.22Z"],
    "62.01Z": ["62.02A", "70.22Z"],
}
REGION_DEPARTEMENTS = {
    "île-de-france": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "ile-de-france": ["75", "77", "78", "91", "92", "93", "94", "95"],
    "idf": ["75", "77", "78", "91", "92", "93", "94", "95"],
}
# Codes tranche d'effectif salarié INSEE -> (min, max) salariés
TRANCHE_EFFECTIF = {
    "00": (0, 0), "01": (1, 2), "02": (3, 5), "03": (6, 9), "11": (10, 19), "12": (20, 49),
    "21": (50, 99), "22": (100, 199), "31": (200, 249), "32": (250, 499), "41": (500, 999),
    "42": (1000, 1999), "51": (2000, 4999), "52": (5000, 9999), "53": (10000, 1000000),
}
DEPT_NAMES = {"paris": "75", "seine-et-marne": "77", "yvelines": "78", "essonne": "91",
              "hauts-de-seine": "92", "seine-saint-denis": "93", "val-de-marne": "94", "val-d'oise": "95"}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def interpret_mission(text: str) -> dict:
    """Étape 1 — Compréhension : extrait NAF, localisation, nombre max, exclusions. Déterministe, aucune invention."""
    import re
    t = _norm(text)
    # secteur -> NAF
    naf_codes = []
    matched_label = None
    for keywords, code in SECTOR_TO_NAF:
        if any(k in t for k in keywords):
            naf_codes.append(code)
            matched_label = ", ".join(keywords[:1])
            break
    # localisation
    departements, region = [], None
    for rk, deps in REGION_DEPARTEMENTS.items():
        if rk in t:
            departements = deps
            region = "Île-de-France"
            break
    if not departements:
        for name, dep in DEPT_NAMES.items():
            if name in t:
                departements.append(dep)
                region = name.title()
    # fourchette de taille demandée (nécessite un mot "salariés/employés/collaborateurs" pour éviter les faux positifs)
    size_range = None
    unit = r"(?:salari[ée]s?|employ[ée]s?|collaborateurs?|personnes?)"
    sm = re.search(r"(?:de\s+)?(\d{1,6})\s*(?:à|a|-|au?)\s*(\d{1,6})\s*" + unit, t)
    if sm:
        lo, hi = int(sm.group(1)), int(sm.group(2))
        size_range = (min(lo, hi), max(lo, hi))
    else:
        sm2 = re.search(r"(?:moins de|jusqu['’]?à|au maximum|maximum|max)\s*(\d{1,6})\s*" + unit, t)
        sm3 = re.search(r"(?:plus de|au moins|à partir de|minimum)\s*(\d{1,6})\s*" + unit, t)
        if sm2:
            size_range = (0, int(sm2.group(1)))
        elif sm3:
            size_range = (int(sm3.group(1)), 1000000)

    # nombre max (exige un mot-clé explicite ou un nom d'entité pour ne pas confondre avec la taille)
    m = re.search(r"(?:jusqu['’]?à|jusqua|au maximum|maximum|max|top)\s*(\d{1,3})", t)
    if not m:
        m = re.search(r"(\d{1,3})\s*(?:entreprises?|cabinets?|soci[ée]t[ée]s?|structures?|prospects?|r[ée]sultats?|contacts?)", t)
    max_results = min(int(m.group(1)), MAX_RESULTS) if m else MAX_RESULTS
    # exclusions
    exclusions = []
    ex = re.search(r"(?:sauf|hors|excl(?:ure|us)?|à l'exclusion de)\s+([\w\s,]+)", t)
    if ex:
        exclusions = [w.strip() for w in re.split(r"[,;]| et ", ex.group(1)) if w.strip()][:5]

    adjacent = ADJACENT_NAF.get(naf_codes[0], []) if naf_codes else []
    return {
        "mission_text": text,
        "naf_codes": naf_codes,
        "naf_labels": {c: NAF_LABELS.get(c, "?") for c in naf_codes},
        "adjacent_naf": adjacent,
        "adjacent_labels": {c: NAF_LABELS.get(c, "?") for c in adjacent},
        "departements": departements,
        "region": region,
        "max_results": max_results,
        "exclusions": exclusions,
        "size_range": list(size_range) if size_range else None,
        "recognized": bool(naf_codes),
    }


async def _api_call(client, params, call_counter):
    call_counter[0] += 1
    r = await client.get(API_URL, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


async def search_companies(interp: dict, exclusion_sirens: set):
    """Étapes 2-3-4 : recherche réelle, vérification, scoring figé. Renvoie (candidats, meta)."""
    naf_codes = interp.get("naf_codes") or []
    target_naf = naf_codes[0] if naf_codes else None
    departements = interp.get("departements") or []
    max_results = min(interp.get("max_results") or MAX_RESULTS, MAX_RESULTS)
    exclusions = [_norm(e) for e in (interp.get("exclusions") or [])]
    adjacent = interp.get("adjacent_naf") or []
    size_range = interp.get("size_range")

    if not target_naf:
        return [], {"error": "Aucun code NAF reconnu — précisez le secteur ou saisissez un code NAF."}

    call_counter = [0]
    candidates, seen_sirens = [], set()
    meta = {"api_calls": 0, "total_api_results": 0, "endpoint": API_URL, "timestamp": now_iso(),
            "source_unavailable": False, "error": None}

    dep_param = ",".join(departements) if departements else None
    try:
        async with httpx.AsyncClient() as client:
            page = 1
            while len(candidates) < max_results and call_counter[0] < MAX_API_CALLS:
                params = {"activite_principale": target_naf, "etat_administratif": "A",
                          "per_page": PER_PAGE, "page": page}
                if dep_param:
                    params["departement"] = dep_param
                data = await _api_call(client, params, call_counter)
                meta["total_api_results"] = data.get("total_results", 0)
                results = data.get("results", [])
                if not results:
                    break
                for e in results:
                    siren = e.get("siren")
                    if not siren or siren in seen_sirens:
                        continue
                    seen_sirens.add(siren)
                    cand = _build_candidate(e, target_naf, departements, exclusions, adjacent, exclusion_sirens, size_range)
                    # Filtre géographique STRICT côté client : l'API 'departement' n'est qu'un tri, pas un filtre dur
                    if departements:
                        cp = cand.get("code_postal") or ""
                        if cp[:2] not in departements:
                            continue
                    candidates.append(cand)
                    if len(candidates) >= max_results:
                        break
                if page >= data.get("total_pages", 1):
                    break
                page += 1
    except (httpx.TimeoutException, httpx.HTTPError) as ex:
        meta["source_unavailable"] = True
        meta["error"] = f"Source Sirene indisponible : {type(ex).__name__}"
    meta["api_calls"] = call_counter[0]
    return candidates, meta


def _crit(label, pts, mx, status=None, note=None):
    """Critère de score traçable. status: ok | ko | neutral (exclu du dénominateur)."""
    if status is None:
        status = "ok" if pts >= mx and mx > 0 else "ko"
    return {"label": label, "pts": pts, "max": mx, "status": status, "note": note}


def _score(crits: dict):
    earned = sum(c["pts"] for c in crits.values())
    possible = sum(c["max"] for c in crits.values() if c["status"] != "neutral")
    return {"total": earned, "max_total": possible, "detail": crits}


def _build_candidate(e: dict, target_naf, departements, exclusions, adjacent, exclusion_sirens, size_range=None):
    siege = e.get("siege") or {}
    siren = e.get("siren")
    siret = siege.get("siret")
    raison = e.get("nom_raison_sociale") or e.get("nom_complet") or ""
    nom_complet = e.get("nom_complet") or raison
    naf = e.get("activite_principale") or siege.get("activite_principale")
    etat = siege.get("etat_administratif")
    adresse = siege.get("adresse")
    cp = siege.get("code_postal")
    commune = siege.get("libelle_commune")
    date_creation = e.get("date_creation")
    tranche = e.get("tranche_effectif_salarie")
    dep_ok = (cp[:2] in departements) if (cp and departements) else (not departements)

    # Vérification
    name_ratio = SequenceMatcher(None, _norm(raison), _norm(nom_complet)).ratio()
    identity_ok = bool(siren)
    activity_exact = (naf == target_naf)
    is_adjacent = (not activity_exact) and (naf in adjacent)
    status_active = (etat == "A")
    address_complete = bool(adresse and cp)
    excl_triggered = any(x in _norm(nom_complet) or x in _norm(naf or "") for x in exclusions)

    contradictions = []  # source unique (Sirene) : aucune détection de contradiction inter-sources possible

    # --- SCORE CONFIANCE (table figée) ---
    conf = {}
    conf["entreprise_api_sirene"] = _crit("Entreprise trouvée via API Sirene", 25 if identity_ok else 0, 25)
    conf["statut_actif"] = _crit("Statut actif confirmé", 15 if status_active else 0, 15)
    conf["raison_sociale_concordante"] = _crit(
        "Raison sociale concordante",
        10 if (name_ratio >= 0.9 or _norm(raison) in _norm(nom_complet)) else 0, 10)
    conf["code_naf_concordant"] = _crit("Code NAF concordant avec la mission", 20 if activity_exact else 0, 20)
    conf["adresse_confirmee"] = _crit("Adresse confirmée (Sirene)", 10 if address_complete else 0, 10)
    conf["site_officiel_confirme"] = _crit(
        "Site officiel confirmé", 0, 10, note="Source secondaire non intégrée (non disponible via Sirene)")
    conf["telephone_email_public"] = _crit(
        "Téléphone ou email public trouvé", 0, 5, note="Non disponible via Sirene")
    conf["coherence_sources"] = _crit(
        "Cohérence entre sources", 0, 5, status="neutral",
        note="Non vérifiable — une seule source active (Sirene)")

    # --- SCORE CORRESPONDANCE MISSION (table figée) ---
    tranche_bounds = TRANCHE_EFFECTIF.get(tranche) if tranche else None
    tranche_txt = (f"{tranche_bounds[0]}–{tranche_bounds[1]} salariés" if tranche_bounds
                   else "tranche non renseignée")
    if size_range:
        lo, hi = int(size_range[0]), int(size_range[1])
        rng_txt = f"{lo}–{hi} salariés"
        if tranche_bounds:
            tlo, thi = tranche_bounds
            in_range = (tlo <= hi and thi >= lo)
            size_crit = _crit(
                f"Taille dans la fourchette souhaitée ({rng_txt})",
                15 if in_range else 0, 15,
                note=None if in_range else f"Tranche Sirene {tranche_txt} hors fourchette demandée")
        else:
            size_crit = _crit(
                f"Taille dans la fourchette souhaitée ({rng_txt})", 0, 15,
                note="Tranche d'effectif non renseignée dans Sirene — non comparable")
    else:
        size_crit = _crit(
            f"Tranche d'effectif renseignée ({tranche_txt})", 0, 15, status="neutral",
            note="Aucune fourchette de taille demandée dans la mission — critère non évalué")

    match = {}
    match["code_naf_cible"] = _crit("Code NAF = code cible exact", 40 if activity_exact else 0, 40)
    match["localisation"] = _crit("Localisation dans le périmètre demandé", 30 if dep_ok else 0, 30)
    match["taille"] = size_crit
    match["aucune_exclusion"] = _crit("Aucune exclusion déclenchée", 15 if not excl_triggered else 0, 15)

    # --- SCORE COMPLÉTUDE (table figée) ---
    comp = {}
    comp["siren_siret"] = _crit("SIREN/SIRET", 20 if (siren and siret) else 0, 20)
    comp["adresse_complete"] = _crit("Adresse complète", 15 if address_complete else 0, 15)
    comp["site_officiel"] = _crit("Site officiel", 0, 15, note="Non disponible via Sirene")
    comp["telephone"] = _crit("Téléphone", 0, 15, note="Non disponible via Sirene")
    comp["email"] = _crit("Email", 0, 15, note="Non disponible via Sirene")
    comp["code_naf"] = _crit("Code NAF", 10 if naf else 0, 10)
    comp["date_creation"] = _crit("Date de création", 10 if date_creation else 0, 10)

    return {
        "siren": siren, "siret": siret, "raison_sociale": raison, "nom_complet": nom_complet,
        "naf": naf, "naf_label": NAF_LABELS.get(naf, ""), "etat": etat,
        "adresse": adresse, "code_postal": cp, "commune": commune, "region": None,
        "date_creation": date_creation, "forme_juridique": e.get("nature_juridique"),
        "tranche_effectif": tranche,
        "website": None, "phone": None, "email": None,  # non disponibles via Sirene (jamais inventés)
        "dirigeants_count": len(e.get("dirigeants") or []),
        "is_adjacent": is_adjacent,
        "is_duplicate": siren in exclusion_sirens,
        "contradictions": contradictions,
        "verification": {
            "identite": "Vérifiée (SIREN)" if identity_ok else "Non vérifiée",
            "activite": "Exacte" if activity_exact else ("Cible adjacente pertinente" if is_adjacent else "Non concordante"),
            "statut": "Actif" if status_active else "Non actif",
            "site_officiel": "Non trouvé (source secondaire indisponible)",
            "coordonnees": "Non disponibles via Sirene",
        },
        "scores": {
            "confidence": _score(conf),
            "match": _score(match),
            "completeness": _score(comp),
        },
        "source": {"endpoint": API_URL, "collected_at": now_iso(), "mode": "réel"},
    }


SCORE_LABELS = {
    "entreprise_api_sirene": ("Entreprise trouvée via API Sirene", 25),
    "statut_actif": ("Statut actif confirmé", 15),
    "raison_sociale_concordante": ("Raison sociale concordante", 10),
    "code_naf_concordant": ("Code NAF concordant avec la mission", 20),
    "adresse_confirmee": ("Adresse confirmée (Sirene)", 10),
    "site_officiel_confirme": ("Site officiel confirmé", 10),
    "telephone_email_public": ("Téléphone ou email public trouvé", 5),
    "aucune_contradiction": ("Aucune contradiction entre sources", 5),
    "code_naf_cible": ("Code NAF = code cible exact", 40),
    "localisation": ("Localisation dans le périmètre demandé", 30),
    "taille": ("Taille dans la fourchette souhaitée", 15),
    "aucune_exclusion": ("Aucune exclusion déclenchée", 15),
    "siren_siret": ("SIREN/SIRET", 20),
    "adresse_complete": ("Adresse complète", 15),
    "site_officiel": ("Site officiel", 15),
    "telephone": ("Téléphone", 15),
    "email": ("Email", 15),
    "code_naf": ("Code NAF", 10),
    "date_creation": ("Date de création", 10),
}
