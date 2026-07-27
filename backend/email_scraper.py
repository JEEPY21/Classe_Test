"""Extraction d'email PUBLIC depuis le site officiel d'une entreprise (une fois l'URL confirmée par Google Places).
RÈGLES STRICTES :
- Aucune invention / aucune déduction (jamais de contact@domaine construit).
- Uniquement un email réellement affiché en texte ou en lien mailto sur une page publique.
- Respect du robots.txt : si l'accès automatisé est interdit, on ne fetch pas et on le dit honnêtement.
- Traçabilité : URL exacte de la page où l'email est trouvé, date de collecte, mode réel.
Coût : 0 (simple fetch HTTP). Aucun service tiers.
"""
import re
import httpx
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from datetime import datetime, timezone

now_iso = lambda: datetime.now(timezone.utc).isoformat()

USER_AGENT = "ProspectiaBot/1.0 (+prospection B2B; respecte robots.txt)"
TIMEOUT = 8.0
MAX_PAGES = 5
MAX_BYTES = 600_000

CANDIDATE_PATHS = ["/contact", "/nous-contacter", "/contactez-nous", "/contact-us",
                   "/mentions-legales", "/a-propos", "/"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
MAILTO_RE = re.compile(r"mailto:([^\"'?>\s]+)", re.IGNORECASE)

# Faux positifs fréquents (assets, placeholders, services tiers) à exclure
_BAD_SUBSTR = ("example.com", "example.org", "sentry", "wixpress", "wix.com", "cloudflare",
               "godaddy", "yourdomain", "domain.com", "email.com", "test.com", "sentry.io",
               "@2x", "@3x", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js", ".ico")
_GENERIC_PREFIXES = ("contact", "info", "bonjour", "hello", "accueil", "cabinet",
                     "secretariat", "secrétariat", "commercial", "contactez")


def _is_plausible(email: str) -> bool:
    e = email.lower()
    if any(b in e for b in _BAD_SUBSTR):
        return False
    if len(e) > 100 or e.count("@") != 1:
        return False
    local, _, domain = e.partition("@")
    if "." not in domain or len(local) < 1:
        return False
    return True


def _rank(email: str) -> int:
    local = email.lower().split("@")[0]
    return 0 if any(local.startswith(p) for p in _GENERIC_PREFIXES) else 1


def _extract_from_html(html: str):
    found = []
    for m in MAILTO_RE.findall(html or ""):
        addr = m.split("?")[0].strip()
        if EMAIL_RE.fullmatch(addr) and _is_plausible(addr):
            found.append(addr.lower())
    for m in EMAIL_RE.findall(html or ""):
        if _is_plausible(m):
            found.append(m.lower())
    # dédup en conservant l'ordre, priorité aux boîtes génériques
    seen, uniq = set(), []
    for e in found:
        if e not in seen:
            seen.add(e)
            uniq.append(e)
    uniq.sort(key=_rank)
    return uniq


async def _load_robots(client, base):
    rp = RobotFileParser()
    try:
        r = await client.get(urljoin(base, "/robots.txt"), timeout=TIMEOUT)
        if r.status_code == 200 and r.text:
            rp.parse(r.text.splitlines())
        else:
            rp.parse([])  # pas de robots.txt => tout autorisé
    except Exception:
        rp.parse([])
    return rp


async def extract_public_email(website_url: str) -> dict:
    """Renvoie un dict traçable : {email, source_url, collected_at, mode, robots_blocked, pages_checked, note}."""
    result = {"email": None, "source_url": None, "collected_at": now_iso(), "mode": "réel",
              "robots_blocked": False, "pages_checked": [], "note": None}
    if not website_url:
        result["note"] = "Aucun site officiel — extraction impossible"
        return result

    parsed = urlparse(website_url if "://" in website_url else "https://" + website_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # liste d'URLs à tester : la page fournie d'abord, puis les pages contact probables
    urls, seen = [], set()
    for u in [website_url] + [urljoin(base + "/", p.lstrip("/")) for p in CANDIDATE_PATHS]:
        if u not in seen:
            seen.add(u)
            urls.append(u)

    blocked_any = False
    async with httpx.AsyncClient(follow_redirects=True, timeout=TIMEOUT,
                                 headers={"User-Agent": USER_AGENT}) as client:
        rp = await _load_robots(client, base)
        for url in urls:
            if len(result["pages_checked"]) >= MAX_PAGES:
                break
            allowed = True
            try:
                allowed = rp.can_fetch(USER_AGENT, url) and rp.can_fetch("*", url)
            except Exception:
                allowed = True
            if not allowed:
                blocked_any = True
                continue
            try:
                r = await client.get(url)
            except Exception:
                continue
            result["pages_checked"].append(url)
            if r.status_code != 200:
                continue
            html = r.text[:MAX_BYTES] if r.text else ""
            emails = _extract_from_html(html)
            if emails:
                result["email"] = emails[0]
                result["source_url"] = str(r.url)
                return result

    if not result["pages_checked"] and blocked_any:
        result["robots_blocked"] = True
        result["note"] = "Extraction impossible — accès automatisé restreint par le site (robots.txt)"
    else:
        result["note"] = "Email non trouvé sur le site officiel"
        if blocked_any:
            result["note"] += " (certaines pages sont bloquées par robots.txt)"
    return result
