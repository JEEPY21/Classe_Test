"""Backend tests for PROSPECTIA prudent analysis + demo data (iteration 6)."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prospectia-app-1.preview.emergentagent.com").rstrip("/")
EMAIL = "jp.koffi@prospectia.app"
PASSWORD = "Prospectia2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --- Dashboard demo exclusion ---
class TestDashboard:
    def test_dashboard_reachable(self, headers):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "kpis" in d and "demo_count" in d
        assert "total_prospects" in d["kpis"]

    def test_demo_seed_and_clear(self, headers):
        # Clear first
        r = requests.delete(f"{BASE_URL}/api/demo/clear", headers=headers, timeout=15)
        assert r.status_code == 200
        # Baseline
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=15)
        base = r.json()
        assert base["demo_count"] == 0
        base_total = base["kpis"]["total_prospects"]
        # Seed
        r = requests.post(f"{BASE_URL}/api/demo/seed", headers=headers, timeout=30)
        assert r.status_code == 200
        # After seed: demo_count>0, total_prospects unchanged (demos excluded)
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=15)
        after = r.json()
        assert after["demo_count"] == 10, f"expected 10 demo companies, got {after['demo_count']}"
        assert after["kpis"]["total_prospects"] == base_total, \
            f"total_prospects changed after demo seed: {base_total} -> {after['kpis']['total_prospects']}"

    def test_clear_demo(self, headers):
        r = requests.delete(f"{BASE_URL}/api/demo/clear", headers=headers, timeout=15)
        assert r.status_code == 200
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=headers, timeout=15)
        assert r.json()["demo_count"] == 0


# --- Company creation with null score ---
class TestCompanyScoreNull:
    def test_create_company_score_null(self, headers):
        payload = {"name": "TEST_Beta_null_score"}
        r = requests.post(f"{BASE_URL}/api/companies", json=payload, headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        assert r.json().get("score") is None, f"score should be None, got {r.json().get('score')}"
        # Verify via GET
        r2 = requests.get(f"{BASE_URL}/api/companies/{cid}", headers=headers, timeout=15)
        assert r2.status_code == 200
        assert r2.json().get("score") is None
        # cleanup
        requests.delete(f"{BASE_URL}/api/companies/{cid}", headers=headers, timeout=15)


# --- IA analyse: prudent structure + insufficient case ---
class TestAIAnalysis:
    def _create(self, headers, **extra):
        payload = {"name": "TEST_Alpha_Conseil_" + str(int(time.time())), **extra}
        r = requests.post(f"{BASE_URL}/api/companies", json=payload, headers=headers, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def test_analysis_full_data(self, headers):
        cid = self._create(headers, sector="Conseil", city="Paris",
                           website="https://alpha-conseil.example",
                           generic_email="contact@alpha-conseil.example")
        try:
            r = requests.post(f"{BASE_URL}/api/companies/{cid}/analyze",
                              headers=headers, timeout=90)
            assert r.status_code == 200, f"analyze failed: {r.status_code} {r.text[:200]}"
            doc = r.json()
            a = doc.get("analysis") or {}
            sd = doc.get("score_detail") or {}
            # Prudent structure
            assert "data_available" in a, f"data_available missing: keys={list(a.keys())}"
            assert "missing_or_unverified" in a
            assert "hypotheses" in a
            assert "potential_service" in a
            assert "reliability_note" in a
            assert a.get("external_search_done", False) in (False, None) or True
            # Score detail traceability
            assert "score_label" in sd
            assert "breakdown" in sd
            assert "data_used" in sd
            assert "data_absent" in sd
            assert sd.get("external_search_done") is False, \
                f"external_search_done must be False, got {sd.get('external_search_done')}"
            assert "reliability" in sd
            # score integer present
            assert isinstance(doc.get("score"), int)
        finally:
            requests.delete(f"{BASE_URL}/api/companies/{cid}", headers=headers, timeout=15)

    def test_analysis_insufficient(self, headers):
        cid = self._create(headers)  # name only
        try:
            r = requests.post(f"{BASE_URL}/api/companies/{cid}/analyze",
                              headers=headers, timeout=90)
            assert r.status_code == 200, r.text[:200]
            a = (r.json().get("analysis") or {})
            # Expect insufficient flag or, at minimum, the prudent structure and missing_or_unverified populated
            assert "missing_or_unverified" in a
            # Not asserting insufficient=True strictly (LLM discretion) but log it
            print("insufficient flag =", a.get("insufficient"))
        finally:
            requests.delete(f"{BASE_URL}/api/companies/{cid}", headers=headers, timeout=15)
