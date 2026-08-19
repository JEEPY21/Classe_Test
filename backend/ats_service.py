"""BLOC 4 — Real ATS quality control.
Primary: Affinda professional parsing API (when the API key is valid).
Fallback: an internal readability audit that re-extracts the generated PDF's text layer
(pdfplumber) and verifies that every key field is actually machine-readable — a genuine,
transparent check, not a checkbox. Results are detailed and human-understandable."""
import os
import unicodedata
import requests

from extraction import extract_text_from_pdf

AFFINDA_BASE = os.environ.get("AFFINDA_BASE_URL", "https://api.eu1.affinda.com")
_COLLECTION_CACHE = None


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def _present(needle: str, haystack: str) -> bool:
    n = _norm(needle)
    return bool(n) and n in haystack


def internal_readability_check(pdf_bytes: bytes, cv: dict) -> dict:
    """Re-parse the produced PDF and confirm each critical field is extractable as native text."""
    try:
        text = extract_text_from_pdf(pdf_bytes)
    except Exception:
        text = ""
    hay = _norm(text)
    ident = cv.get("identity", {})
    fields = []

    def check(label, value, critical=True):
        value = (value or "").strip()
        if not value:
            return
        fields.append({"label": label, "value": value,
                       "status": "read" if _present(value, hay) else "missed",
                       "critical": critical})

    check("Nom complet", ident.get("full_name"))
    check("Email", ident.get("email"))
    check("Téléphone", ident.get("phone"), critical=False)
    check("Intitulé / titre", ident.get("title"), critical=False)

    for exp in cv.get("experiences", [])[:6]:
        if exp.get("role"):
            check(f"Poste : {exp.get('role')}", exp.get("role"))
        if exp.get("company"):
            check(f"Entreprise : {exp.get('company')}", exp.get("company"))
        if exp.get("start_date"):
            check(f"Date ({exp.get('company') or exp.get('role')})", exp.get("start_date"), critical=False)

    for ed in cv.get("education", [])[:3]:
        if ed.get("degree"):
            check(f"Diplôme : {ed.get('degree')}", ed.get("degree"), critical=False)

    for sk in cv.get("skills", [])[:15]:
        check(f"Compétence : {sk}", sk, critical=False)

    total = len(fields)
    read = sum(1 for f in fields if f["status"] == "read")
    critical_missed = [f for f in fields if f["status"] == "missed" and f["critical"]]
    score = round((read / total) * 100) if total else 0
    return {
        "source": "internal",
        "score": score,
        "total_fields": total,
        "read_fields": read,
        "fields": fields,
        "critical_issues": [f["label"] for f in critical_missed],
        "extracted_char_count": len(text),
        "has_text_layer": len(text) > 50,
    }


def _get_collection(headers: dict) -> str:
    """Resolve (and cache) the Affinda collection used for resume parsing. Auto-provisions the
    organization's workspace + a resume-extractor collection on first use."""
    global _COLLECTION_CACHE
    if _COLLECTION_CACHE:
        return _COLLECTION_CACHE
    env_col = os.environ.get("AFFINDA_COLLECTION")
    if env_col:
        _COLLECTION_CACHE = env_col
        return env_col

    def _items(resp):
        j = resp.json()
        return j.get("results", j) if isinstance(j, dict) else j

    orgs = _items(requests.get(f"{AFFINDA_BASE}/v3/organizations", headers=headers, timeout=25))
    org = orgs[0].get("identifier")
    ws_items = _items(requests.get(f"{AFFINDA_BASE}/v3/workspaces", headers=headers,
                                   params={"organization": org}, timeout=25))
    ws = next((w.get("identifier") for w in ws_items if w.get("name") == "Matchipy"), None)
    if not ws:
        ws = requests.post(f"{AFFINDA_BASE}/v3/workspaces", headers=headers,
                           json={"organization": org, "name": "Matchipy"}, timeout=30).json()["identifier"]
    col_items = _items(requests.get(f"{AFFINDA_BASE}/v3/collections", headers=headers,
                                    params={"workspace": ws}, timeout=25))
    col = next((c.get("identifier") for c in col_items), None)
    if not col:
        col = requests.post(f"{AFFINDA_BASE}/v3/collections", headers=headers,
                            json={"workspace": ws, "name": "CV", "extractor": "resume"},
                            timeout=30).json()["identifier"]
    _COLLECTION_CACHE = col
    return col


def affinda_parse(pdf_bytes: bytes, filename: str) -> dict:
    """Live Affinda parse. Returns the RAW parsed result mapped to detected/missing fields
    (no AI reprocessing). Returns {available: bool, ...}."""
    key = os.environ.get("AFFINDA_API_KEY")
    if not key:
        return {"available": False, "reason": "Aucune clé Affinda configurée."}
    headers = {"Authorization": f"Bearer {key}"}
    try:
        collection = _get_collection(headers)
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        data = {"collection": collection, "wait": "true"}
        resp = requests.post(f"{AFFINDA_BASE}/v3/documents", headers=headers,
                             files=files, data=data, timeout=120)
        if resp.status_code not in (200, 201):
            return {"available": False,
                    "reason": f"Affinda a refusé la requête (HTTP {resp.status_code})."}
        body = resp.json()
        parsed = body.get("data", {}) or {}
        doc_id = (body.get("meta") or {}).get("identifier")

        fields = []

        def add(label, val, critical=True):
            fields.append({"label": label, "value": str(val) if val not in (None, "", []) else "",
                           "status": "read" if val not in (None, "", [], 0) else "missed",
                           "critical": critical})

        name = parsed.get("name")
        add("Nom", (name or {}).get("raw") if isinstance(name, dict) else name)
        add("Email", (parsed.get("emails") or [None])[0])
        add("Téléphone", (parsed.get("phoneNumbers") or [None])[0], critical=False)
        work = parsed.get("workExperience") or []
        add("Expériences détectées", len(work) if work else 0)
        edu = parsed.get("education") or []
        add("Formations détectées", len(edu) if edu else 0, critical=False)
        skills = parsed.get("skills") or []
        add("Compétences détectées", len(skills) if skills else 0, critical=False)

        # RGPD / data minimisation: delete the uploaded document from Affinda after parsing.
        if doc_id:
            try:
                requests.delete(f"{AFFINDA_BASE}/v3/documents/{doc_id}", headers=headers, timeout=20)
            except Exception:
                pass

        read = sum(1 for f in fields if f["status"] == "read")
        detected = [f["label"] for f in fields if f["status"] == "read"]
        missing = [f["label"] for f in fields if f["status"] == "missed"]
        critical_missed = [f["label"] for f in fields if f["status"] == "missed" and f["critical"]]
        return {"available": True, "source": "affinda",
                "score": round((read / len(fields)) * 100) if fields else 0,
                "total_fields": len(fields), "read_fields": read,
                "fields": fields, "detected": detected, "missing": missing,
                "critical_issues": critical_missed, "has_text_layer": True,
                "raw": {"work_count": len(work), "skills_count": len(skills), "education_count": len(edu)}}
    except Exception as e:
        return {"available": False, "reason": f"Affinda indisponible : {str(e)[:150]}"}


def run_ats_check(pdf_bytes: bytes, filename: str, cv: dict) -> dict:
    affinda = affinda_parse(pdf_bytes, filename)
    internal = internal_readability_check(pdf_bytes, cv)
    if affinda.get("available"):
        primary = "affinda"
        report = affinda
    else:
        primary = "internal"
        report = internal
    return {
        "primary": primary,
        "affinda_available": affinda.get("available", False),
        "affinda_message": affinda.get("reason"),
        "report": report,
        "internal": internal,
    }
