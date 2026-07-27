"""Tests backend Discovery Agent — Fix scoring (size_range + coherence_sources neutral)."""
import os, pytest, requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or os.environ.get("BACKEND_URL", "").rstrip("/")
# Fallback: read from file if env not injected in pytest environment
if not BASE_URL:
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
    except Exception:
        pass

ADMIN_EMAIL = "jp.koffi@prospectia.app"
ADMIN_PASSWORD = "Prospectia2026!"


@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- interpret_mission ----------
def _interpret(auth, text):
    r = requests.post(f"{BASE_URL}/api/discovery/interpret", json={"mission_text": text}, headers=auth, timeout=15)
    assert r.status_code == 200, r.text
    return r.json()


def test_interpret_with_size_range_1_to_20(auth):
    d = _interpret(auth, "Trouver 5 cabinets d'expertise comptable en Île-de-France de 1 à 20 salariés")
    assert d["size_range"] == [1, 20]
    assert "69.20Z" in d["naf_codes"]
    assert d["max_results"] == 5
    assert set(d["departements"]) == {"75", "77", "78", "91", "92", "93", "94", "95"}


def test_interpret_no_size_range(auth):
    d = _interpret(auth, "Trouver jusqu'à 15 cabinets comptables en Île-de-France")
    assert d["size_range"] is None
    assert d["max_results"] == 15


def test_interpret_moins_de_50(auth):
    d = _interpret(auth, "cabinets comptables moins de 50 salariés à Paris")
    assert d["size_range"] == [0, 50]


def test_interpret_plus_de_200(auth):
    d = _interpret(auth, "cabinets comptables plus de 200 salariés à Paris")
    assert d["size_range"] == [200, 1000000]


# ---------- discovery/run simulation ----------
def _run_sim(auth, mission_text):
    interp = _interpret(auth, mission_text)
    r = requests.post(f"{BASE_URL}/api/discovery/run",
                      json={"interpretation": interp, "mode": "simulation"}, headers=auth, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


def test_run_sim_size_in_range(auth):
    """1-20 salariés, tranche simulée 03 (6-9) DANS la fourchette."""
    m = _run_sim(auth, "Trouver 5 cabinets d'expertise comptable en Île-de-France de 1 à 20 salariés")
    assert m["candidates"], "no simulation candidates"
    c = m["candidates"][0]
    taille = c["scores"]["match"]["detail"]["taille"]
    assert taille["status"] == "ok", taille
    assert taille["pts"] == 15 and taille["max"] == 15
    assert c["scores"]["match"]["total"] == 100
    assert c["scores"]["match"]["max_total"] == 100


def test_run_sim_size_out_of_range(auth):
    """50-100 salariés, tranche simulée 03 (6-9) HORS fourchette."""
    m = _run_sim(auth, "Trouver 5 cabinets d'expertise comptable en Île-de-France de 50 à 100 salariés")
    c = m["candidates"][0]
    taille = c["scores"]["match"]["detail"]["taille"]
    assert taille["status"] == "ko", taille
    assert taille["pts"] == 0 and taille["max"] == 15
    assert (taille.get("note") or "").lower().find("hors fourchette") >= 0
    assert c["scores"]["match"]["total"] == 85
    assert c["scores"]["match"]["max_total"] == 100


def test_run_sim_no_size_range_neutral(auth):
    """Aucune fourchette demandée -> taille status neutral, exclu du dénominateur."""
    m = _run_sim(auth, "Trouver jusqu'à 15 cabinets comptables en Île-de-France")
    c = m["candidates"][0]
    taille = c["scores"]["match"]["detail"]["taille"]
    assert taille["status"] == "neutral", taille
    assert taille["label"].startswith("Tranche d'effectif renseignée")
    assert c["scores"]["match"]["total"] == 85
    assert c["scores"]["match"]["max_total"] == 85


def test_confidence_coherence_sources_neutral_all_cases(auth):
    """coherence_sources doit toujours être neutral, 0 pt, max_total confiance == 95."""
    for txt in [
        "Trouver 5 cabinets d'expertise comptable en Île-de-France de 1 à 20 salariés",
        "Trouver jusqu'à 15 cabinets comptables en Île-de-France",
        "Trouver 5 cabinets comptables en Île-de-France de 50 à 100 salariés",
    ]:
        m = _run_sim(auth, txt)
        c = m["candidates"][0]
        conf = c["scores"]["confidence"]
        coh = conf["detail"]["coherence_sources"]
        assert coh["status"] == "neutral", (txt, coh)
        assert coh["pts"] == 0
        assert "une seule source active" in (coh.get("note") or "").lower()
        assert conf["max_total"] == 95, (txt, conf["max_total"])
