"""Matchipy backend regression tests.

Scope: quick smoke over auth, CV upload (real LLM), job analyze (real LLM),
generation, ATS check (Affinda fallback), export PDF/DOCX, RGPD delete.
Uses the public preview URL so we test the same surface as the browser."""
import os
import io
import time
import requests
import pytest

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") \
    if "REACT_APP_BACKEND_URL" in os.environ else \
    "https://job-fit-check-12.preview.emergentagent.com"

ADMIN_EMAIL = "admin@matchipy.com"
ADMIN_PASSWORD = "Matchipy2026!"

SAMPLE_JOB = (
    "Développeur Fullstack Senior — TypeScript, React, Node.js.\n"
    "Vous rejoindrez une équipe produit pour construire une plateforme SaaS.\n"
    "Compétences requises: TypeScript, React, Node.js, PostgreSQL, Docker, AWS.\n"
    "Soft skills: autonomie, communication, esprit d'équipe.\n"
    "Basé à Paris. Poste en CDI."
)


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=20)
    assert r.status_code == 200, r.text
    return s


# ---------- Auth ----------
def test_root():
    r = requests.get(f"{BASE_URL}/api/", timeout=15)
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


def test_me_authenticated(session):
    r = session.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 200
    assert r.json()["email"] == ADMIN_EMAIL


def test_me_unauthenticated():
    r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
    assert r.status_code == 401


def test_login_returns_tokens():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")


def test_refresh_via_body():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    refresh = r.json()["refresh_token"]
    r2 = requests.post(f"{BASE_URL}/api/auth/refresh",
                       json={"refresh_token": refresh}, timeout=15)
    assert r2.status_code == 200, r2.text
    new_access = r2.json().get("access_token")
    assert new_access
    # Use it against /me
    r3 = requests.get(f"{BASE_URL}/api/auth/me",
                      headers={"Authorization": f"Bearer {new_access}"}, timeout=15)
    assert r3.status_code == 200
    assert r3.json()["email"] == ADMIN_EMAIL


# ---------- Templates ----------
def test_templates(session):
    r = session.get(f"{BASE_URL}/api/export/templates", timeout=15)
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()]
    assert set(ids) >= {"classic", "modern", "compact"}


# ---------- CV upload (real LLM, slow) ----------
@pytest.fixture(scope="module")
def cv_id(session):
    path = "/tmp/sample_cv.pdf"
    if not os.path.exists(path):
        pytest.skip("sample CV missing")
    with open(path, "rb") as f:
        r = session.post(f"{BASE_URL}/api/cv/upload",
                         files={"file": ("sample_cv.pdf", f, "application/pdf")},
                         timeout=120)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["id"]
    assert doc["structured"]["identity"]["full_name"]
    return doc["id"]


def test_list_cvs(session, cv_id):
    r = session.get(f"{BASE_URL}/api/cv", timeout=15)
    assert r.status_code == 200
    assert any(cv["id"] == cv_id for cv in r.json())


# ---------- Job analyze ----------
@pytest.fixture(scope="module")
def job_id(session):
    r = session.post(f"{BASE_URL}/api/job/analyze",
                     json={"raw_text": SAMPLE_JOB}, timeout=90)
    assert r.status_code == 200, r.text
    doc = r.json()
    a = doc["analysis"]
    assert a.get("job_title")
    # Hard skills should mention TypeScript at least
    assert any("typescript" in s.lower() for s in a.get("hard_skills", []))
    return doc["id"]


# ---------- Generate (async + polling) ----------
@pytest.fixture(scope="module")
def session_id(session, cv_id, job_id):
    t0 = time.time()
    r = session.post(f"{BASE_URL}/api/generate",
                     json={"cv_id": cv_id, "job_id": job_id}, timeout=15)
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    doc = r.json()
    # POST must return quickly (no 502, no long block)
    assert elapsed < 10, f"POST /generate too slow: {elapsed:.1f}s (should be async)"
    assert doc["status"] == "pending"
    sid = doc["id"]
    # Poll until ready
    deadline = time.time() + 120
    final = None
    while time.time() < deadline:
        time.sleep(2.5)
        r2 = session.get(f"{BASE_URL}/api/generate/{sid}", timeout=15)
        assert r2.status_code == 200
        final = r2.json()
        if final["status"] in ("ready", "error"):
            break
    assert final and final["status"] == "ready", f"Generation did not finish: {final}"
    assert final["score"]["overall"] >= 0
    return sid


def _poll_ready(session, sid, timeout=120):
    deadline = time.time() + timeout
    final = None
    while time.time() < deadline:
        time.sleep(2.5)
        r = session.get(f"{BASE_URL}/api/generate/{sid}", timeout=15)
        assert r.status_code == 200
        final = r.json()
        if final["status"] in ("ready", "error"):
            return final
    return final


# ---- ÉVOLUTION 2: skills_section present, transverse only, deduped, <=12 ----
def test_skills_section_shape(session, session_id):
    r = session.get(f"{BASE_URL}/api/generate/{session_id}", timeout=15)
    assert r.status_code == 200
    doc = r.json()
    skills = doc.get("skills_section")
    assert isinstance(skills, list), f"skills_section missing/not list: {skills}"
    assert len(skills) <= 12, f"skills_section > 12: {len(skills)}"
    # Collect keywords woven into experience rewrites (nested under bullets)
    def collect_woven(d):
        w = set()
        for rw in d.get("experience_rewrites", []) or []:
            for b in rw.get("bullets", []) or []:
                for kw in b.get("keywords_used", []) or []:
                    name = kw.get("keyword") if isinstance(kw, dict) else kw
                    if isinstance(name, str) and name.strip():
                        w.add(name.lower().strip())
        return w
    woven = collect_woven(doc)
    # No overlap between section and woven keywords
    section_names = []
    for s in skills:
        name = s.get("skill") if isinstance(s, dict) else s
        assert isinstance(name, str) and name.strip()
        section_names.append(name.lower().strip())
    overlap = set(section_names) & woven
    assert not overlap, f"Duplicated skills between section and bullets: {overlap}"


# ---- ÉVOLUTION 2: confirm-skills triggers async regeneration ----
def test_confirm_skills_triggers_regeneration(session, session_id):
    r = session.put(f"{BASE_URL}/api/generate/{session_id}/confirm-skills",
                    json={"confirmed_skills": ["Docker", "TypeScript"]}, timeout=20)
    assert r.status_code == 200
    doc = r.json()
    assert set(["Docker", "TypeScript"]).issubset(set(doc["confirmed_skills"]))
    assert doc["status"] == "pending", f"confirm-skills should set status=pending, got {doc['status']}"
    final = _poll_ready(session, session_id, timeout=150)
    assert final and final["status"] == "ready", f"Regeneration did not finish: {final}"
    # Confirmed skill should appear either woven or in skills_section, not both
    woven = set()
    for rw in final.get("experience_rewrites", []) or []:
        for b in rw.get("bullets", []) or []:
            for kw in b.get("keywords_used", []) or []:
                name = kw.get("keyword") if isinstance(kw, dict) else kw
                if isinstance(name, str) and name.strip():
                    woven.add(name.lower().strip())
    section = set()
    for s in final.get("skills_section", []):
        name = s.get("skill") if isinstance(s, dict) else s
        if isinstance(name, str):
            section.add(name.lower().strip())
    for confirmed in ["docker", "typescript"]:
        assert confirmed in woven or confirmed in section, \
            f"Confirmed skill '{confirmed}' not present in woven or section"
        assert not (confirmed in woven and confirmed in section), \
            f"Confirmed skill '{confirmed}' duplicated in both woven and section"


# ---------- MOD 2: two LLM calls (Sonnet CV + Haiku letter) ----------
def test_generation_has_cv_and_letter(session, session_id):
    r = session.get(f"{BASE_URL}/api/generate/{session_id}", timeout=15)
    assert r.status_code == 200
    doc = r.json()
    # Sonnet CV outputs
    assert isinstance(doc.get("score"), dict) and "overall" in doc["score"]
    assert isinstance(doc.get("experience_rewrites"), list)
    assert isinstance(doc.get("skills_section"), list)
    # Haiku letter output
    paras = (doc.get("cover_letter") or {}).get("paragraphs", [])
    assert isinstance(paras, list) and len(paras) >= 2, f"cover_letter.paragraphs missing: {paras}"


# ---------- MOD 4: cover letter style (no em dash, no bullets) ----------
def test_cover_letter_style_no_em_dash_no_bullets(session, session_id):
    r = session.get(f"{BASE_URL}/api/generate/{session_id}", timeout=15)
    doc = r.json()
    paras = (doc.get("cover_letter") or {}).get("paragraphs", [])
    assert paras, "no cover letter paragraphs"
    joined = "\n".join(paras)
    assert "\u2014" not in joined, "cover letter contains em dash (—)"
    assert "•" not in joined, "cover letter contains bullet (•)"
    for p in paras:
        assert not p.lstrip().startswith("- "), f"bullet '- ' at start of paragraph: {p[:80]}"


# ---------- MOD 2: extraction cleanup (unit) ----------
def test_extraction_strips_repeated_headers_and_normalizes_whitespace():
    import sys
    sys.path.insert(0, "/app/backend")
    from extraction import _strip_repeated_headers_footers, _normalize_whitespace
    page1 = "CV confidentiel\nCamille Dupont\nDéveloppeur\nExpérience A\nPage 1 / 2"
    page2 = "CV confidentiel\nSuite du parcours\nExpérience B\nPage 2 / 2"
    stripped = _strip_repeated_headers_footers([page1, page2])
    assert "CV confidentiel" not in stripped
    assert "Page 1 / 2" not in stripped and "Page 2 / 2" not in stripped
    assert "Camille Dupont" in stripped
    assert "Expérience A" in stripped and "Expérience B" in stripped
    # whitespace normalization
    raw = "Hello    world\n\n\n\nnext\t\tline   here"
    norm = _normalize_whitespace(raw)
    assert "    " not in norm and "\t\t" not in norm
    assert "\n\n\n" not in norm


# ---------- MOD 1: ATS check — NO LLM call ----------
def test_ats_service_has_no_llm_import():
    with open("/app/backend/ats_service.py", "r", encoding="utf-8") as f:
        src = f.read()
    for forbidden in ("import llm_service", "from llm_service", "emergentintegrations",
                      "anthropic", "LlmChat"):
        assert forbidden not in src, f"ats_service.py must not reference LLM: found '{forbidden}'"


def test_ats_check(session, session_id):
    t0 = time.time()
    r = session.post(f"{BASE_URL}/api/ats/check",
                     json={"generation_id": session_id, "template_id": "classic"},
                     timeout=90)
    elapsed = time.time() - t0
    assert r.status_code == 200, r.text
    body = r.json()
    # Affinda key invalid — fallback expected
    assert body["report"]["score"] >= 0
    assert "affinda_available" in body
    assert "primary" in body and "report" in body
    # MOD 1: no LLM call means the endpoint must be fast (no ~10-30s Claude latency)
    assert elapsed < 20, f"ATS check too slow ({elapsed:.1f}s) — suspect LLM call"


# ---------- Affinda EU real integration ----------
def test_ats_check_affinda_available(session, session_id):
    """AFFINDA_API_KEY is valid on the EU region; expect affinda_available=true and detected fields."""
    r = session.post(f"{BASE_URL}/api/ats/check",
                     json={"generation_id": session_id, "template_id": "classic"},
                     timeout=180)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("affinda_available") is True, f"Expected Affinda available, got: {body}"
    assert body.get("primary") == "affinda"
    report = body["report"]
    assert report["source"] == "affinda"
    assert report["score"] >= 0
    # Fields present with labels
    labels = [f["label"] for f in report["fields"]]
    assert "Nom" in labels and "Email" in labels
    # Some fields should be detected on the CV
    assert isinstance(report.get("detected"), list)
    assert isinstance(report.get("missing"), list)


# ---------- BLOC 3bis: Application tracking ----------
@pytest.fixture(scope="module")
def application_id(session, session_id):
    r = session.post(f"{BASE_URL}/api/applications",
                     json={"session_id": session_id,
                           "poste": "TEST_Développeur Fullstack",
                           "entreprise": "TEST_Acme",
                           "statut": "envoyée",
                           "notes": "TEST candidature",
                           "template_id": "classic"}, timeout=60)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc.get("id")
    assert doc["poste"] == "TEST_Développeur Fullstack"
    assert doc["statut"] == "envoyée"
    return doc["id"]


def test_application_list_and_filter(session, application_id):
    r = session.get(f"{BASE_URL}/api/applications", timeout=15)
    assert r.status_code == 200
    apps = r.json()
    assert any(a["id"] == application_id for a in apps)
    # Filter by status
    r2 = session.get(f"{BASE_URL}/api/applications?statut=envoyée", timeout=15)
    assert r2.status_code == 200
    assert any(a["id"] == application_id for a in r2.json())
    # Filter negative
    r3 = session.get(f"{BASE_URL}/api/applications?statut=refusée", timeout=15)
    assert all(a["id"] != application_id for a in r3.json())


def test_application_update(session, application_id):
    r = session.put(f"{BASE_URL}/api/applications/{application_id}",
                    json={"statut": "entretien", "notes": "TEST updated"}, timeout=20)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["statut"] == "entretien"
    assert doc["notes"] == "TEST updated"


def test_application_download_cv_pdf(session, application_id):
    r = session.post(f"{BASE_URL}/api/applications/{application_id}/download",
                     json={"doc_type": "cv", "format": "pdf"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_application_download_letter_pdf(session, application_id):
    r = session.post(f"{BASE_URL}/api/applications/{application_id}/download",
                     json={"doc_type": "cover_letter", "format": "pdf"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_application_delete(session, application_id):
    r = session.delete(f"{BASE_URL}/api/applications/{application_id}", timeout=15)
    assert r.status_code == 200
    r2 = session.get(f"{BASE_URL}/api/applications", timeout=15)
    assert all(a["id"] != application_id for a in r2.json())




# ---------- Export (ÉVOLUTION 1: 4 downloads: cv+letter × pdf+docx) ----------
def test_export_cv_pdf(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "template_id": "classic",
                           "doc_type": "cv", "format": "pdf"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_export_cv_docx(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "doc_type": "cv",
                           "format": "docx"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    assert len(r.content) > 500


def test_export_letter_pdf(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "template_id": "classic",
                           "doc_type": "cover_letter", "format": "pdf"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 500


def test_export_letter_docx(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "doc_type": "cover_letter",
                           "format": "docx"}, timeout=60)
    assert r.status_code == 200, r.text
    assert r.content[:2] == b"PK"
    assert len(r.content) > 500


# ---------- RGPD delete ----------
def test_delete_cv(session, cv_id):
    r = session.delete(f"{BASE_URL}/api/cv/{cv_id}", timeout=15)
    assert r.status_code == 200
    r2 = session.get(f"{BASE_URL}/api/cv/{cv_id}", timeout=15)
    assert r2.status_code == 404
