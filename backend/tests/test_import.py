"""Tests d'intégration pour le flux d'import CSV/XLSX (bug bloquant iteration_3)."""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://prospectia-app-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "jp.koffi@prospectia.app"
ADMIN_PASSWORD = "Prospectia2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    tok = r.json().get("token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


# --- Auth sanity ---
def test_auth_me(headers):
    r = requests.get(f"{API}/auth/me", headers=headers, timeout=10)
    assert r.status_code == 200, r.text
    assert r.json().get("email") == ADMIN_EMAIL


# --- Import: CSV français avec point-virgule et accents ---
CSV_FR_HEADERS = "Société;Secteur;Ville;Code Postal;Site Web;Email;Téléphone;Contact;Fonction"
CSV_FR_DATA = "\n".join([
    CSV_FR_HEADERS,
    "TEST_Boulangerie Léa;Boulangerie;Créteil;94000;https://lea.fr;contact@lea.fr;0102030405;Léa Martin;Gérante",
    "TEST_Café Über;Restauration;Paris;75002;https://uber-cafe.fr;info@uber-cafe.fr;0102030406;Hänsel Grün;Directeur",
    "TEST_Épicerie Noël;Commerce;Lyon;69003;https://noel.fr;bonjour@noel.fr;0102030407;François Noël;Fondateur",
    # doublon (nom identique au 1er)
    "TEST_Boulangerie Léa;Boulangerie;Créteil;94000;https://lea.fr;contact@lea.fr;0102030405;Léa Martin;Gérante",
    # ligne invalide (nom vide)
    ";Autre;Marseille;13000;;;;;",
])


def _post_preview(headers, filename, content, content_type="text/csv"):
    files = {"file": (filename, content, content_type)}
    return requests.post(f"{API}/import/preview", headers=headers, files=files, timeout=30)


def test_import_preview_semicolon_accents(headers):
    payload = CSV_FR_DATA.encode("utf-8")
    r = _post_preview(headers, "test_fr.csv", payload)
    assert r.status_code == 200, r.text
    data = r.json()
    # meta
    assert data["meta"]["separator"] == "point-virgule"
    assert data["meta"]["encoding"] in ("utf-8", "utf-8-sig")
    assert data["meta"]["n_rows"] == 5  # 5 lignes de données
    assert data["meta"]["n_cols"] == 9
    # mapping automatique
    m = data["mapping"]
    assert m.get("name") == "Société"
    assert m.get("sector") == "Secteur"
    assert m.get("city") == "Ville"
    assert m.get("postal_code") == "Code Postal"
    assert m.get("website") == "Site Web"
    assert m.get("generic_email") == "Email"
    assert m.get("phone") == "Téléphone"
    assert m.get("contact_full_name") == "Contact"
    assert m.get("contact_role") == "Fonction"
    # sample 5 lignes
    assert len(data["sample"]) == 5
    # doublons: 1 doublon interne (Boulangerie Léa)
    assert data["internal_duplicates"] >= 1
    # 1 ligne rejetée pour nom vide -> warning_count >= 1
    assert data["warning_count"] >= 1
    # valid_rows = 4 (5 - 1 ligne sans nom)
    assert data["valid_rows"] == 4
    assert data["import_id"]
    # store for next test
    pytest.import_id_fr = data["import_id"]
    pytest.mapping_fr = m


def test_import_confirm_semicolon_ignore(headers):
    body = {"import_id": pytest.import_id_fr, "mapping": pytest.mapping_fr, "duplicate_strategy": "ignore"}
    r = requests.post(f"{API}/import/confirm", headers=headers, json=body, timeout=30)
    assert r.status_code == 200, r.text
    rep = r.json()
    assert rep["companies_created"] >= 3  # 3 uniques + 1 duplicate (ignore)
    assert rep["duplicates_ignored"] >= 1
    assert rep["rejected"] >= 1  # nom vide
    assert rep["contacts_created"] >= 3
    # verify persistence via GET companies
    r2 = requests.get(f"{API}/companies", headers=headers, timeout=15)
    assert r2.status_code == 200
    names = [c["name"] for c in r2.json()]
    assert "TEST_Boulangerie Léa" in names
    assert "TEST_Café Über" in names
    assert "TEST_Épicerie Noël" in names


# --- Import: CSV virgule anglais ---
CSV_EN = "\n".join([
    "company,industry,city,website,email",
    "TEST_AlphaTech,Technology,Paris,https://alphatech.io,hello@alphatech.io",
    "TEST_BetaCorp,Finance,Lyon,https://beta.io,contact@beta.io",
])


def test_import_preview_comma_english(headers):
    r = _post_preview(headers, "test_en.csv", CSV_EN.encode("utf-8"))
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["meta"]["separator"] == "virgule"
    assert d["mapping"].get("name") == "company"
    assert d["mapping"].get("sector") == "industry"
    assert d["mapping"].get("city") == "city"
    assert d["mapping"].get("website") == "website"
    assert d["mapping"].get("generic_email") == "email"
    assert d["valid_rows"] == 2
    pytest.import_id_en = d["import_id"]
    pytest.mapping_en = d["mapping"]


def test_import_confirm_comma_english(headers):
    body = {"import_id": pytest.import_id_en, "mapping": pytest.mapping_en, "duplicate_strategy": "ignore"}
    r = requests.post(f"{API}/import/confirm", headers=headers, json=body, timeout=30)
    assert r.status_code == 200
    rep = r.json()
    assert rep["companies_created"] == 2


# --- Empty file ---
def test_import_preview_empty_file(headers):
    r = _post_preview(headers, "empty.csv", b"")
    assert r.status_code == 400
    assert "vide" in r.text.lower()


# --- Confirm without name mapping ---
def test_import_confirm_without_name_mapping(headers):
    # start a fresh preview
    r = _post_preview(headers, "test_fr2.csv", CSV_FR_DATA.encode("utf-8"))
    assert r.status_code == 200
    d = r.json()
    bad_mapping = {k: v for k, v in d["mapping"].items() if k != "name"}
    body = {"import_id": d["import_id"], "mapping": bad_mapping, "duplicate_strategy": "ignore"}
    r2 = requests.post(f"{API}/import/confirm", headers=headers, json=body, timeout=15)
    assert r2.status_code == 400
    assert "Nom entreprise" in r2.text


# --- XLSX support ---
def test_import_preview_xlsx(headers):
    try:
        import openpyxl
    except ImportError:
        pytest.skip("openpyxl not installed")
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(["Société", "Secteur", "Ville", "Email"])
    ws.append(["TEST_XlsxOne", "Informatique", "Nantes", "contact@xlsxone.fr"])
    ws.append(["TEST_XlsxTwo", "Consulting", "Bordeaux", "hello@xlsxtwo.fr"])
    buf = io.BytesIO()
    wb.save(buf)
    r = _post_preview(headers, "test.xlsx", buf.getvalue(),
                      content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["meta"]["ext"] == "xlsx"
    assert d["mapping"].get("name") == "Société"
    assert d["valid_rows"] == 2
    body = {"import_id": d["import_id"], "mapping": d["mapping"], "duplicate_strategy": "ignore"}
    r2 = requests.post(f"{API}/import/confirm", headers=headers, json=body, timeout=15)
    assert r2.status_code == 200
    assert r2.json()["companies_created"] == 2


# --- Cleanup ---
def test_zzz_cleanup(headers):
    """Nettoyage des entreprises TEST_ créées pendant les tests."""
    r = requests.get(f"{API}/companies", headers=headers, timeout=15)
    assert r.status_code == 200
    for c in r.json():
        if c.get("name", "").startswith("TEST_"):
            cid = c["id"]
            # delete company (soft or hard)
            requests.delete(f"{API}/companies/{cid}", headers=headers, timeout=10)
