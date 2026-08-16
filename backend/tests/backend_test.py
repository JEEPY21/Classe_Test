"""Matchipy backend regression tests.

Scope: quick smoke over auth, CV upload (real LLM), job analyze (real LLM),
generation, ATS check (Affinda fallback), export PDF/DOCX, RGPD delete.
Uses the public preview URL so we test the same surface as the browser."""
import os
import io
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


# ---------- Generate ----------
@pytest.fixture(scope="module")
def session_id(session, cv_id, job_id):
    r = session.post(f"{BASE_URL}/api/generate",
                     json={"cv_id": cv_id, "job_id": job_id}, timeout=180)
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["score"]["overall"] >= 0
    return doc["id"]


def test_confirm_skills(session, session_id):
    r = session.put(f"{BASE_URL}/api/generate/{session_id}/confirm-skills",
                    json={"confirmed_skills": ["TypeScript"]}, timeout=20)
    assert r.status_code == 200
    doc = r.json()
    assert "TypeScript" in doc["confirmed_skills"]


# ---------- ATS check ----------
def test_ats_check(session, session_id):
    r = session.post(f"{BASE_URL}/api/ats/check",
                     json={"generation_id": session_id, "template_id": "classic"},
                     timeout=90)
    assert r.status_code == 200, r.text
    body = r.json()
    # Affinda key invalid — fallback expected
    assert body["report"]["score"] >= 0
    assert "affinda_available" in body


# ---------- Export ----------
def test_export_pdf(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "template_id": "classic",
                           "format": "pdf"}, timeout=60)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    assert len(r.content) > 500
    assert r.content[:4] == b"%PDF"


def test_export_docx(session, session_id):
    r = session.post(f"{BASE_URL}/api/export/download",
                     json={"generation_id": session_id, "format": "docx"},
                     timeout=60)
    assert r.status_code == 200
    # DOCX = zip => starts with PK
    assert r.content[:2] == b"PK"
    assert len(r.content) > 500


# ---------- RGPD delete ----------
def test_delete_cv(session, cv_id):
    r = session.delete(f"{BASE_URL}/api/cv/{cv_id}", timeout=15)
    assert r.status_code == 200
    r2 = session.get(f"{BASE_URL}/api/cv/{cv_id}", timeout=15)
    assert r2.status_code == 404
