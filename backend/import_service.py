"""Service d'import robuste PROSPECTIA : détection format/encodage/séparateur, mappage par synonymes,
normalisation, détection de doublons. Étape 1 = aperçu, étape 2 = confirmation."""
import io
import csv
import re
import unicodedata
import pandas as pd

MAX_ROWS = 5000


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norm_header(h) -> str:
    h = strip_accents(str(h)).lower().strip()
    h = re.sub(r"[\s_\-\.]+", " ", h)
    return h.strip()


# Champ cible -> liste de synonymes (normalisés sans accent)
COMPANY_SYNONYMS = {
    "name": ["entreprise", "societe", "nom societe", "nom entreprise", "company", "company name", "business", "business name", "enseigne", "nom", "raison sociale", "nom de l entreprise"],
    "legal_name": ["raison sociale", "legal name", "denomination"],
    "sector": ["secteur", "activite", "industry", "business sector", "domaine d activite", "domaine", "secteur d activite"],
    "sub_sector": ["sous secteur", "sub sector", "specialite"],
    "description": ["description", "activite description", "presentation"],
    "address": ["adresse", "address", "rue", "adresse postale"],
    "city": ["ville", "city", "locality", "commune"],
    "postal_code": ["code postal", "cp", "postal code", "zip", "zipcode", "code_postal"],
    "region": ["region", "departement", "department"],
    "country": ["pays", "country"],
    "website": ["site", "site web", "website", "web", "url", "website url", "domaine", "domain", "site internet"],
    "linkedin": ["linkedin", "url linkedin", "linkedin url", "linkedin entreprise"],
    "facebook": ["facebook", "url facebook", "page facebook"],
    "instagram": ["instagram", "url instagram"],
    "phone": ["telephone", "tel", "phone", "telephone entreprise", "numero", "tel entreprise"],
    "generic_email": ["email", "mail", "e mail", "adresse mail", "adresse email", "contact email", "email generique", "courriel"],
    "founded_year": ["annee de creation", "annee creation", "founded", "year", "creation"],
    "employees": ["nombre de salaries", "salaries", "employees", "effectif", "nb salaries"],
    "size": ["taille", "taille estimee", "size", "company size"],
    "source": ["source", "origine", "source url"],
    "tags": ["tags", "etiquettes", "mots cles"],
    "notes": ["notes", "note", "commentaire", "commentaires", "remarques"],
}

CONTACT_SYNONYMS = {
    "contact_full_name": ["contact", "contact name", "full name", "nom contact", "nom du contact", "interlocuteur", "nom complet"],
    "contact_first_name": ["prenom", "first name", "firstname", "prenom contact"],
    "contact_last_name": ["nom contact", "last name", "lastname", "nom de famille"],
    "contact_role": ["fonction", "poste", "role", "title", "job title", "titre"],
    "contact_email": ["email contact", "email professionnel", "contact email", "email du contact", "mail contact"],
    "contact_phone": ["mobile", "telephone mobile", "portable", "tel contact"],
    "contact_linkedin": ["linkedin contact", "profil linkedin"],
    "contact_decision_level": ["niveau de decision", "decision level", "seniorite"],
    "contact_department": ["departement contact", "service"],
}

ALL_SYNONYMS = {**COMPANY_SYNONYMS, **CONTACT_SYNONYMS}

FIELD_LABELS = {
    "name": "Nom entreprise *", "legal_name": "Raison sociale", "sector": "Secteur",
    "sub_sector": "Sous-secteur", "description": "Description", "address": "Adresse",
    "city": "Ville", "postal_code": "Code postal", "region": "Région", "country": "Pays",
    "website": "Site internet", "linkedin": "LinkedIn", "facebook": "Facebook",
    "instagram": "Instagram", "phone": "Téléphone", "generic_email": "Email générique",
    "founded_year": "Année création", "employees": "Nb salariés", "size": "Taille",
    "source": "Source", "tags": "Tags", "notes": "Notes",
    "contact_full_name": "Contact — nom complet", "contact_first_name": "Contact — prénom",
    "contact_last_name": "Contact — nom", "contact_role": "Contact — fonction",
    "contact_email": "Contact — email", "contact_phone": "Contact — téléphone",
    "contact_linkedin": "Contact — LinkedIn", "contact_decision_level": "Contact — niveau décision",
    "contact_department": "Contact — département",
}


def parse_file(content: bytes, filename: str):
    """Détecte format/encodage/séparateur et renvoie (rows_as_dicts, headers, meta)."""
    ext = (filename.rsplit(".", 1)[-1] or "").lower()
    meta = {"filename": filename, "ext": ext, "size": len(content)}

    if ext in ("xlsx", "xls"):
        try:
            df = pd.read_excel(io.BytesIO(content), dtype=str)
        except Exception as e:
            raise ValueError(f"Fichier Excel illisible : {e}")
        meta.update({"encoding": "xlsx", "separator": "n/a"})
        df = df.fillna("")
        headers = [str(c) for c in df.columns]
        rows = df.astype(str).to_dict("records")
        meta["n_rows"] = len(rows)
        meta["n_cols"] = len(headers)
        return rows, headers, meta

    # CSV : détection encodage
    text = None
    used_enc = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = content.decode(enc)
            used_enc = enc
            break
        except (UnicodeDecodeError, LookupError):
            continue
    if text is None:
        raise ValueError("Encodage non pris en charge (essayez UTF-8).")
    if not text.strip():
        raise ValueError("Le fichier est vide.")

    # détection séparateur
    sample = "\n".join(text.splitlines()[:20])
    sep = ","
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        sep = dialect.delimiter
    except Exception:
        # heuristique : compter les occurrences sur la 1re ligne
        first = text.splitlines()[0] if text.splitlines() else ""
        counts = {d: first.count(d) for d in [";", ",", "\t", "|"]}
        sep = max(counts, key=counts.get) if max(counts.values()) > 0 else ","

    reader = csv.reader(io.StringIO(text), delimiter=sep)
    all_rows = [r for r in reader]
    if not all_rows:
        raise ValueError("Aucune donnée détectée dans le fichier.")
    headers = [h.strip() for h in all_rows[0]]
    if not any(headers):
        raise ValueError("En-têtes de colonnes absents.")

    rows = []
    for r in all_rows[1:]:
        if not any((c or "").strip() for c in r):
            continue  # ligne vide
        d = {}
        for i, h in enumerate(headers):
            d[h] = (r[i].strip() if i < len(r) else "")
        rows.append(d)
        if len(rows) >= MAX_ROWS:
            break

    meta.update({"encoding": used_enc, "separator": {",": "virgule", ";": "point-virgule", "\t": "tabulation", "|": "pipe"}.get(sep, sep),
                 "n_rows": len(rows), "n_cols": len(headers)})
    return rows, headers, meta


def auto_map(headers):
    """Propose un mappage {champ_cible: header_source}. Renvoie aussi les colonnes non reconnues."""
    mapping = {}
    used_headers = set()
    norm_to_orig = {norm_header(h): h for h in headers}
    for field, syns in ALL_SYNONYMS.items():
        for h_norm, h_orig in norm_to_orig.items():
            if h_orig in used_headers:
                continue
            if h_norm in syns or any(h_norm == norm_header(s) for s in syns):
                mapping[field] = h_orig
                used_headers.add(h_orig)
                break
    unrecognized = [h for h in headers if h not in used_headers]
    return mapping, unrecognized


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(v):
    v = (v or "").strip().lower()
    if not v:
        return "", True
    return v, bool(EMAIL_RE.match(v))


def normalize_url(v):
    v = (v or "").strip()
    if not v:
        return ""
    if not re.match(r"^https?://", v, re.I):
        v = "https://" + v
    return v


def extract_domain(url):
    m = re.search(r"https?://(?:www\.)?([^/]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


def normalize_phone(v):
    v = (v or "").strip()
    return re.sub(r"(?!^\+)[^\d]", "", v) if v else ""


def build_records(rows, mapping):
    """Applique le mappage, normalise, renvoie (companies, warnings_par_ligne)."""
    companies = []
    warnings = []
    for idx, row in enumerate(rows, start=2):  # ligne 1 = en-têtes
        comp = {}
        for field, header in mapping.items():
            if not header:
                continue
            val = (row.get(header) or "").strip()
            if not val:
                continue
            comp[field] = val
        line_warn = []
        name = comp.get("name", "").strip()
        if not name:
            warnings.append({"line": idx, "reason": "Nom d'entreprise manquant", "row": row})
            continue
        # normalisations
        if comp.get("generic_email"):
            email, ok = normalize_email(comp["generic_email"])
            comp["generic_email"] = email
            if not ok:
                line_warn.append("Email entreprise invalide")
        if comp.get("website"):
            comp["website"] = normalize_url(comp["website"])
        if comp.get("phone"):
            comp["phone"] = normalize_phone(comp["phone"])
        if comp.get("tags"):
            comp["tags"] = [t.strip() for t in re.split(r"[;,|]", comp["tags"]) if t.strip()]
        # contact
        contact = {}
        for k in list(comp.keys()):
            if k.startswith("contact_"):
                contact[k.replace("contact_", "")] = comp.pop(k)
        if contact.get("email"):
            cem, ok = normalize_email(contact["email"])
            contact["email"] = cem
            if not ok:
                line_warn.append("Email contact invalide")
        if contact.get("full_name") and not contact.get("first_name"):
            parts = contact["full_name"].split(" ", 1)
            contact["first_name"] = parts[0]
            contact["last_name"] = parts[1] if len(parts) > 1 else ""
        comp["_contact"] = contact if (contact.get("first_name") or contact.get("email") or contact.get("full_name")) else None
        comp["_line"] = idx
        comp["_warnings"] = line_warn
        companies.append(comp)
        if line_warn:
            warnings.append({"line": idx, "reason": "; ".join(line_warn), "row": row})
    return companies, warnings


def find_internal_duplicates(companies):
    """Doublons à l'intérieur du fichier (par nom normalisé ou domaine)."""
    seen = {}
    dups = []
    for c in companies:
        keys = [norm_header(c.get("name", ""))]
        if c.get("website"):
            keys.append(extract_domain(c["website"]))
        matched = None
        for k in keys:
            if k and k in seen:
                matched = seen[k]
                break
        if matched is not None:
            dups.append(c["_line"])
        else:
            for k in keys:
                if k:
                    seen[k] = c["_line"]
    return dups
