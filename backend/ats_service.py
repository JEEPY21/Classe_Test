"""BLOC 4 — Real ATS quality control.
Primary: Affinda professional parsing API (when the API key is valid).
Fallback: an internal readability audit that re-extracts the generated PDF's text layer
(pdfplumber) and verifies that every key field is actually machine-readable — a genuine,
transparent check, not a checkbox. Results are detailed and human-understandable."""
import os
import unicodedata
import requests

from extraction import extract_text_from_pdf

AFFINDA_BASE = "https://api.affinda.com"


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


def affinda_parse(pdf_bytes: bytes, filename: str) -> dict:
    """Attempt a live Affinda parse. Returns {available: bool, ...}."""
    key = os.environ.get("AFFINDA_API_KEY")
    if not key:
        return {"available": False, "reason": "Aucune clé Affinda configurée."}
    headers = {"Authorization": f"Bearer {key}"}
    try:
        ws = requests.get(f"{AFFINDA_BASE}/v3/workspaces", headers=headers, timeout=25)
        if ws.status_code != 200:
            return {"available": False,
                    "reason": f"Affinda a refusé la clé API (HTTP {ws.status_code}). "
                              f"Vérifiez le token dans les paramètres Affinda."}
        workspaces = ws.json()
        items = workspaces.get("results", workspaces) if isinstance(workspaces, dict) else workspaces
        if not items:
            return {"available": False, "reason": "Aucun workspace Affinda disponible pour cette clé."}
        workspace_id = items[0].get("identifier") or items[0].get("id")
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        data = {"workspace": workspace_id, "wait": "true", "deleteAfterParse": "true"}
        resp = requests.post(f"{AFFINDA_BASE}/v3/documents", headers=headers,
                             files=files, data=data, timeout=90)
        if resp.status_code not in (200, 201):
            return {"available": False, "reason": f"Erreur de parsing Affinda (HTTP {resp.status_code})."}
        parsed = resp.json().get("data", {})
        fields = []

        def add(label, val):
            fields.append({"label": label, "value": str(val) if val else "",
                           "status": "read" if val else "missed", "critical": True})

        add("Nom", (parsed.get("name") or {}).get("raw") if isinstance(parsed.get("name"), dict) else parsed.get("name"))
        add("Email", (parsed.get("emails") or [None])[0])
        add("Téléphone", (parsed.get("phoneNumbers") or [None])[0])
        work = parsed.get("workExperience") or []
        add("Expériences détectées", len(work) if work else "")
        skills = parsed.get("skills") or []
        add("Compétences détectées", len(skills) if skills else "")
        read = sum(1 for f in fields if f["status"] == "read")
        return {"available": True, "source": "affinda",
                "score": round((read / len(fields)) * 100) if fields else 0,
                "fields": fields, "raw": {"work_count": len(work), "skills_count": len(skills)}}
    except Exception as e:
        return {"available": False, "reason": f"Affinda indisponible : {str(e)[:120]}"}


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
