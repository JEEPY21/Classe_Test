"""Test dashboard include_demo toggle and demo seed/clear endpoints."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prospectia-app-1.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "jp.koffi@prospectia.app"
ADMIN_PASSWORD = "Prospectia2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def h(token):
    return {"Authorization": f"Bearer {token}"}


# --- dashboard behavior ---
class TestDashboardDemoToggle:
    def test_seed_demo(self, h):
        r = requests.post(f"{BASE_URL}/api/demo/seed", headers=h, timeout=30)
        assert r.status_code == 200, r.text

    def test_dashboard_excludes_demo_by_default(self, h):
        # include_demo defaults to False
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["demo_count"] == 10, f"demo_count expected 10, got {d['demo_count']}"
        assert d["kpis"]["total_prospects"] == 0, f"total_prospects when excluding demo expected 0, got {d['kpis']['total_prospects']}"

    def test_dashboard_includes_demo(self, h):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=h, params={"include_demo": "true"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["demo_count"] == 10
        assert d["kpis"]["total_prospects"] == 10, f"total_prospects when including demo expected 10, got {d['kpis']['total_prospects']}"
        # Sector/status charts should be populated
        assert len(d["by_sector"]) > 0
        assert len(d["by_status"]) > 0

    def test_priority_erreurs_automatisation_is_zero(self, h):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=h, params={"include_demo": "true"}, timeout=30)
        assert r.status_code == 200
        d = r.json()
        # Note: value can rise if this or previous test triggered errors
        assert d["priority"]["erreurs_automatisation"] == 0, f"erreurs_automatisation should be 0, got {d['priority']['erreurs_automatisation']}"

    def test_companies_list_still_shows_demo(self, h):
        # Companies list is independent of include_demo toggle
        r = requests.get(f"{BASE_URL}/api/companies", headers=h, timeout=30)
        assert r.status_code == 200
        cos = r.json()
        demo = [c for c in cos if c.get("is_demo")]
        assert len(demo) == 10, f"Companies endpoint should still return 10 demo, got {len(demo)}"

    def test_clear_demo(self, h):
        r = requests.delete(f"{BASE_URL}/api/demo/clear", headers=h, timeout=30)
        assert r.status_code == 200

    def test_dashboard_after_clear(self, h):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["demo_count"] == 0
        assert d["kpis"]["total_prospects"] == 0
