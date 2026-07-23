"""
PROSPECTIA - Backend API pytest suite.
Covers: auth, companies, contacts, AI analyze/generate/validate/followups/replies,
opportunities, campaigns, templates, exclusions, activity, errors, settings, dashboard, demo seed.
"""
import os
import io
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://prospectia-app-1.preview.emergentagent.com').rstrip('/')
ADMIN_EMAIL = "jp.koffi@prospectia.app"
ADMIN_PASSWORD = "Prospectia2026!"

# Shared state across tests
STATE = {}


@pytest.fixture(scope="session")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["email"] == ADMIN_EMAIL
    return data["token"]


@pytest.fixture(scope="session")
def h(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------- Auth ----------
class TestAuth:
    def test_login_wrong_password(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN_EMAIL, "password": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 401

    def test_me_ok(self, h):
        r = requests.get(f"{BASE_URL}/api/auth/me", headers=h, timeout=15)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


# ---------- Dashboard & Demo seed ----------
class TestDashboardAndDemo:
    def test_dashboard(self, h):
        r = requests.get(f"{BASE_URL}/api/dashboard", headers=h, timeout=30)
        assert r.status_code == 200
        d = r.json()
        for k in ("kpis", "by_status", "by_sector", "funnel", "priority"):
            assert k in d

    def test_demo_seed_creates_data(self, h):
        r = requests.post(f"{BASE_URL}/api/demo/seed", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        # verify 10 companies exist
        r2 = requests.get(f"{BASE_URL}/api/companies", headers=h, timeout=20)
        assert r2.status_code == 200
        demos = [c for c in r2.json() if c.get("is_demo")]
        assert len(demos) >= 10, f"expected >=10 demo companies, got {len(demos)}"
        STATE["demo_companies"] = demos


# ---------- Companies CRUD ----------
class TestCompanies:
    def test_list_companies(self, h):
        r = requests.get(f"{BASE_URL}/api/companies", headers=h, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_company_and_persistence(self, h):
        payload = {"name": "TEST_Alpha Corp", "sector": "SaaS", "city": "Paris",
                   "website": "https://alpha.test", "generic_email": "contact@alpha.test"}
        r = requests.post(f"{BASE_URL}/api/companies", headers=h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["name"] == payload["name"]
        assert "id" in d
        STATE["company_id"] = d["id"]
        # persistence
        g = requests.get(f"{BASE_URL}/api/companies/{d['id']}", headers=h, timeout=15)
        assert g.status_code == 200
        assert g.json()["name"] == payload["name"]

    def test_duplicate_detected(self, h):
        payload = {"name": "TEST_Alpha Corp", "sector": "SaaS", "city": "Paris",
                   "website": "https://alpha.test"}
        r = requests.post(f"{BASE_URL}/api/companies", headers=h, json=payload, timeout=15)
        assert r.status_code == 409

    def test_filter_search(self, h):
        r = requests.get(f"{BASE_URL}/api/companies?search=TEST_Alpha", headers=h, timeout=15)
        assert r.status_code == 200
        names = [c["name"] for c in r.json()]
        assert "TEST_Alpha Corp" in names

    def test_bulk_status(self, h):
        cid = STATE.get("company_id")
        r = requests.post(f"{BASE_URL}/api/companies/bulk-status", headers=h,
                          json={"data": {"ids": [cid], "status": "Qualifié"}}, timeout=15)
        assert r.status_code == 200
        g = requests.get(f"{BASE_URL}/api/companies/{cid}", headers=h, timeout=15)
        assert g.json()["status"] == "Qualifié"

    def test_import_csv(self, h):
        csv_data = "nom,secteur,ville,site\nTEST_ImportedCo,Retail,Lyon,https://imported.test\n"
        files = {"file": ("companies.csv", io.BytesIO(csv_data.encode()), "text/csv")}
        # For file upload, don't use application/json content-type
        auth = {"Authorization": h["Authorization"]}
        r = requests.post(f"{BASE_URL}/api/companies/import-csv", headers=auth, files=files, timeout=20)
        assert r.status_code == 200, r.text
        assert r.json().get("imported", 0) >= 1

    def test_export_csv(self, h):
        r = requests.get(f"{BASE_URL}/api/companies-export/csv", headers=h, timeout=20)
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")
        assert "name" in r.text.splitlines()[0]


# ---------- Contacts ----------
class TestContacts:
    def test_create_contact(self, h):
        cid = STATE["company_id"]
        payload = {"company_id": cid, "first_name": "TEST_John", "last_name": "Doe",
                   "role": "CEO", "decision_level": "décideur", "email": "john@alpha.test"}
        r = requests.post(f"{BASE_URL}/api/contacts", headers=h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        STATE["contact_id"] = r.json()["id"]

    def test_list_contacts(self, h):
        r = requests.get(f"{BASE_URL}/api/contacts", headers=h, timeout=15)
        assert r.status_code == 200
        assert any(c["first_name"] == "TEST_John" for c in r.json())


# ---------- AI: analyze, generate email, validate → follow-ups ----------
class TestAI:
    def test_analyze_company(self, h):
        cid = STATE["company_id"]
        r = requests.post(f"{BASE_URL}/api/companies/{cid}/analyze", headers=h, timeout=90)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("analysis") is not None
        assert d.get("score_detail") is not None
        assert isinstance(d.get("score"), int)

    def test_generate_email_requires_analysis(self, h):
        # Create a fresh unanalyzed company
        payload = {"name": "TEST_NoAnalysis", "sector": "SaaS", "generic_email": "x@na.test"}
        c = requests.post(f"{BASE_URL}/api/companies", headers=h, json=payload, timeout=15).json()
        r = requests.post(f"{BASE_URL}/api/emails/generate", headers=h,
                          json={"data": {"company_id": c["id"]}}, timeout=30)
        assert r.status_code == 400
        STATE["no_analysis_cid"] = c["id"]

    def test_generate_email_ok(self, h):
        cid = STATE["company_id"]
        r = requests.post(f"{BASE_URL}/api/emails/generate", headers=h,
                          json={"data": {"company_id": cid}}, timeout=90)
        assert r.status_code == 200, r.text
        res = r.json()["result"]
        assert res.get("subject") and res.get("body")
        STATE["email_subject"] = res["subject"]
        STATE["email_body"] = res["body"]

    def test_save_email_draft(self, h):
        cid = STATE["company_id"]
        payload = {"company_id": cid, "subject": STATE["email_subject"],
                   "body": STATE["email_body"], "status": "À valider"}
        r = requests.post(f"{BASE_URL}/api/emails", headers=h, json=payload, timeout=15)
        assert r.status_code == 200, r.text
        STATE["email_id"] = r.json()["id"]

    def test_validate_and_send_creates_followups(self, h):
        eid = STATE["email_id"]
        r = requests.post(f"{BASE_URL}/api/emails/{eid}/validate", headers=h,
                          json={"data": {"action": "send"}}, timeout=30)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "Envoyé"
        # 3 follow-ups programmed
        fs = requests.get(f"{BASE_URL}/api/followups", headers=h, timeout=15).json()
        my_fs = [f for f in fs if f["email_id"] == eid]
        assert len(my_fs) == 3, f"expected 3 follow-ups, got {len(my_fs)}"
        STATE["followup_id"] = my_fs[0]["id"]


# ---------- Follow-ups ----------
class TestFollowups:
    def test_generate_followup(self, h):
        fid = STATE["followup_id"]
        r = requests.post(f"{BASE_URL}/api/followups/{fid}/generate", headers=h, timeout=60)
        assert r.status_code == 200, r.text
        assert r.json().get("subject") and r.json().get("body")


# ---------- Replies (AI classification) ----------
class TestReplies:
    def test_create_reply_interested_creates_opportunity(self, h):
        cid = STATE["company_id"]
        r = requests.post(f"{BASE_URL}/api/replies", headers=h,
                          json={"company_id": cid,
                                "text": "Bonjour, oui je suis très intéressé, planifions un rendez-vous."},
                          timeout=90)
        assert r.status_code == 200, r.text
        cat = r.json().get("category")
        assert cat in ("Intéressé", "Souhaite un rendez-vous", "Demande d'informations")
        # opportunity created
        opps = requests.get(f"{BASE_URL}/api/opportunities", headers=h, timeout=15).json()
        assert any(o["company_id"] == cid for o in opps), "opportunity not created"
        # follow-ups cancelled
        fs = requests.get(f"{BASE_URL}/api/followups", headers=h, timeout=15).json()
        my_fs = [f for f in fs if f["company_id"] == cid]
        assert all(f["status"] != "Programmée" for f in my_fs)


# ---------- Opportunities ----------
class TestOpportunities:
    def test_update_opportunity_stage(self, h):
        opps = requests.get(f"{BASE_URL}/api/opportunities", headers=h, timeout=15).json()
        assert opps, "no opportunities"
        oid = opps[0]["id"]
        r = requests.put(f"{BASE_URL}/api/opportunities/{oid}", headers=h,
                         json={"data": {"stage": "Rendez-vous planifié"}}, timeout=15)
        assert r.status_code == 200


# ---------- Campaigns ----------
class TestCampaigns:
    def test_create_campaign(self, h):
        r = requests.post(f"{BASE_URL}/api/campaigns", headers=h,
                         json={"name": "TEST_Campaign", "sector": "SaaS", "geo_zone": "France"},
                         timeout=15)
        assert r.status_code == 200
        STATE["campaign_id"] = r.json()["id"]

    def test_list_campaigns(self, h):
        r = requests.get(f"{BASE_URL}/api/campaigns", headers=h, timeout=15)
        assert r.status_code == 200
        assert any(c["name"] == "TEST_Campaign" for c in r.json())


# ---------- Templates / Services / Exclusions ----------
class TestMisc:
    def test_templates(self, h):
        r = requests.get(f"{BASE_URL}/api/templates", headers=h, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_services(self, h):
        r = requests.get(f"{BASE_URL}/api/services", headers=h, timeout=15)
        assert r.status_code == 200

    def test_exclusion_add_and_list(self, h):
        r = requests.post(f"{BASE_URL}/api/exclusions", headers=h,
                          json={"data": {"email": "TEST_excl@example.com", "reason": "Test"}},
                          timeout=15)
        assert r.status_code == 200
        STATE["excl_id"] = r.json()["id"]
        lst = requests.get(f"{BASE_URL}/api/exclusions", headers=h, timeout=15).json()
        assert any(e.get("email") == "TEST_excl@example.com" for e in lst)


# ---------- Activity / Errors / Settings ----------
class TestLogsSettings:
    def test_activity(self, h):
        r = requests.get(f"{BASE_URL}/api/activity", headers=h, timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_errors(self, h):
        r = requests.get(f"{BASE_URL}/api/errors", headers=h, timeout=15)
        assert r.status_code == 200

    def test_get_settings(self, h):
        r = requests.get(f"{BASE_URL}/api/settings", headers=h, timeout=15)
        assert r.status_code == 200
        assert r.json().get("id") == "global"

    def test_update_settings(self, h):
        r = requests.put(f"{BASE_URL}/api/settings", headers=h,
                         json={"data": {"prospection": {"followup_delays": [3, 7, 14]}}}, timeout=15)
        assert r.status_code == 200


# ---------- Cleanup ----------
class TestCleanup:
    def test_cleanup_test_data(self, h):
        # delete test companies
        cs = requests.get(f"{BASE_URL}/api/companies?search=TEST_", headers=h, timeout=15).json()
        for c in cs:
            requests.delete(f"{BASE_URL}/api/companies/{c['id']}", headers=h, timeout=15)
        # delete test campaign
        if STATE.get("campaign_id"):
            requests.delete(f"{BASE_URL}/api/campaigns/{STATE['campaign_id']}", headers=h, timeout=15)
        # delete test exclusion
        if STATE.get("excl_id"):
            requests.delete(f"{BASE_URL}/api/exclusions/{STATE['excl_id']}", headers=h, timeout=15)
