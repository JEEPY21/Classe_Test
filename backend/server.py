from dotenv import load_dotenv
from pathlib import Path
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import logging
import io
import csv
import re
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Any

import bcrypt
import jwt
import pandas as pd
from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field

import ai_service
import seed_data
import import_service

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"

app = FastAPI(title="PROSPECTIA API")
api = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prospectia")

now_iso = lambda: datetime.now(timezone.utc).isoformat()
new_id = lambda: str(uuid.uuid4())


# ---------- Auth helpers ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def create_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email, "type": "access",
               "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(request: Request) -> dict:
    auth = request.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Non authentifié")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expirée")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token invalide")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(401, "Utilisateur introuvable")
    return user


async def log_activity(action: str, entity: str, entity_id: str = "", detail: str = "",
                       old_state: str = "", new_state: str = "", auto: bool = False, status: str = "ok"):
    await db.activity_logs.insert_one({
        "id": new_id(), "action": action, "entity": entity, "entity_id": entity_id,
        "detail": detail, "old_state": old_state, "new_state": new_state,
        "user": "Jean-Philippe Koffi", "auto": auto, "status": status, "created_at": now_iso()
    })

async def log_error(error_type: str, message: str, entity_id: str = "", corrective: str = ""):
    await db.errors.insert_one({
        "id": new_id(), "type": error_type, "message": message, "entity_id": entity_id,
        "corrective_action": corrective, "resolved": False, "created_at": now_iso()
    })


# ---------- Models ----------
class LoginIn(BaseModel):
    email: str
    password: str

class Company(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    legal_name: Optional[str] = ""
    sector: Optional[str] = ""
    sub_sector: Optional[str] = ""
    description: Optional[str] = ""
    address: Optional[str] = ""
    city: Optional[str] = ""
    postal_code: Optional[str] = ""
    region: Optional[str] = ""
    country: Optional[str] = "France"
    website: Optional[str] = ""
    google_maps: Optional[str] = ""
    linkedin: Optional[str] = ""
    facebook: Optional[str] = ""
    instagram: Optional[str] = ""
    other_socials: Optional[str] = ""
    size: Optional[str] = ""
    employees: Optional[str] = ""
    founded_year: Optional[str] = ""
    phone: Optional[str] = ""
    generic_email: Optional[str] = ""
    source: Optional[str] = "Ajout manuel"
    status: Optional[str] = "Nouveau"
    tags: List[str] = []
    notes: Optional[str] = ""
    score: Optional[int] = 0
    analysis: Optional[Any] = None
    score_detail: Optional[Any] = None
    is_demo: bool = False

class Contact(BaseModel):
    id: str = Field(default_factory=new_id)
    company_id: str
    first_name: str
    last_name: Optional[str] = ""
    role: Optional[str] = ""
    decision_level: Optional[str] = "autre"
    department: Optional[str] = ""
    email: Optional[str] = ""
    email_verified: Optional[str] = "non vérifié"
    phone: Optional[str] = ""
    linkedin: Optional[str] = ""
    source: Optional[str] = ""
    do_not_contact: bool = False
    notes: Optional[str] = ""
    next_action: Optional[str] = ""
    next_action_date: Optional[str] = ""
    is_demo: bool = False

class Campaign(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    description: Optional[str] = ""
    sector: Optional[str] = ""
    geo_zone: Optional[str] = ""
    size_criteria: Optional[str] = ""
    offer: Optional[str] = "Audit gratuit du système d'acquisition digitale"
    template_id: Optional[str] = ""
    max_prospects: Optional[int] = 100
    daily_volume: Optional[int] = 5
    start_date: Optional[str] = ""
    end_date: Optional[str] = ""
    followup_sequence: List[int] = [3, 7, 14]
    status: Optional[str] = "Brouillon"
    is_demo: bool = False

class Template(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str
    type: Optional[str] = "premier_contact"
    sector: Optional[str] = "Tous"
    objective: Optional[str] = ""
    subject: str
    content: str
    tone: Optional[str] = "consultatif"
    active: bool = True

class EmailDraft(BaseModel):
    id: str = Field(default_factory=new_id)
    company_id: str
    contact_id: Optional[str] = ""
    campaign_id: Optional[str] = ""
    subject: str
    body: str
    tone: Optional[str] = "consultatif"
    status: Optional[str] = "À valider"  # À valider, Validé, Programmé, Envoyé, Refusé
    problem: Optional[str] = ""
    service: Optional[str] = ""
    scheduled_date: Optional[str] = ""
    sent_at: Optional[str] = ""

class ReplyIn(BaseModel):
    company_id: str
    email_id: Optional[str] = ""
    text: str

class GenericIn(BaseModel):
    data: dict = {}


def clean(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ---------- Auth routes ----------
@api.post("/auth/login")
async def login(body: LoginIn):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email ou mot de passe incorrect")
    token = create_token(user["id"], user["email"])
    await log_activity("Connexion", "utilisateur", user["id"], detail=email)
    return {"token": token, "user": {"id": user["id"], "email": user["email"],
            "name": user.get("name"), "role": user.get("role", "admin")}}

@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@api.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"ok": True}


# ---------- Companies ----------
def detect_duplicate(existing: dict, c: dict) -> bool:
    for f in ["name", "website", "phone", "generic_email", "address"]:
        v = (c.get(f) or "").strip().lower()
        if v and (existing.get(f) or "").strip().lower() == v:
            return True
    return False

@api.get("/companies")
async def list_companies(user: dict = Depends(get_current_user), status: Optional[str] = None,
                         sector: Optional[str] = None, search: Optional[str] = None,
                         sort: Optional[str] = "created_at", order: Optional[str] = "desc"):
    q: dict = {}
    if status:
        q["status"] = status
    if sector:
        q["sector"] = sector
    if search:
        q["$or"] = [{"name": {"$regex": search, "$options": "i"}},
                    {"city": {"$regex": search, "$options": "i"}},
                    {"generic_email": {"$regex": search, "$options": "i"}}]
    direction = -1 if order == "desc" else 1
    docs = await db.companies.find(q, {"_id": 0}).sort(sort, direction).to_list(1000)
    return docs

@api.post("/companies")
async def create_company(company: Company, user: dict = Depends(get_current_user)):
    doc = company.model_dump()
    ors = [{f: doc[f]} for f in ["name", "website", "phone", "generic_email", "address"] if doc.get(f)]
    existing = await db.companies.find_one({"$or": ors}, {"_id": 0}) if ors else None
    if existing and detect_duplicate(existing, doc):
        raise HTTPException(409, "Doublon détecté : cette entreprise existe déjà (nom, site, téléphone, email ou adresse identique)")
    doc["created_at"] = now_iso()
    doc["updated_at"] = now_iso()
    await db.companies.insert_one(doc)
    await log_activity("Création d'entreprise", "entreprise", doc["id"], new_state=doc["name"])
    return clean(doc)

@api.get("/companies/{cid}")
async def get_company(cid: str, user: dict = Depends(get_current_user)):
    doc = await db.companies.find_one({"id": cid}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Entreprise introuvable")
    doc["contacts"] = await db.contacts.find({"company_id": cid}, {"_id": 0}).to_list(100)
    doc["emails"] = await db.emails.find({"company_id": cid}, {"_id": 0}).to_list(100)
    return doc

@api.put("/companies/{cid}")
async def update_company(cid: str, company: Company, user: dict = Depends(get_current_user)):
    old = await db.companies.find_one({"id": cid}, {"_id": 0})
    if not old:
        raise HTTPException(404, "Entreprise introuvable")
    doc = company.model_dump()
    doc["id"] = cid
    doc["updated_at"] = now_iso()
    doc["created_at"] = old.get("created_at", now_iso())
    doc["analysis"] = doc.get("analysis") or old.get("analysis")
    doc["score_detail"] = doc.get("score_detail") or old.get("score_detail")
    doc["score"] = doc.get("score") or old.get("score", 0)
    await db.companies.replace_one({"id": cid}, doc)
    if old.get("status") != doc.get("status"):
        await log_activity("Changement de statut", "entreprise", cid, old_state=old.get("status"), new_state=doc.get("status"))
    else:
        await log_activity("Modification", "entreprise", cid, new_state=doc["name"])
    return clean(doc)

@api.delete("/companies/{cid}")
async def delete_company(cid: str, user: dict = Depends(get_current_user)):
    await db.companies.delete_one({"id": cid})
    await db.contacts.delete_many({"company_id": cid})
    await log_activity("Suppression", "entreprise", cid)
    return {"ok": True}

@api.post("/companies/bulk-status")
async def bulk_status(body: GenericIn, user: dict = Depends(get_current_user)):
    ids = body.data.get("ids", [])
    status = body.data.get("status")
    await db.companies.update_many({"id": {"$in": ids}}, {"$set": {"status": status, "updated_at": now_iso()}})
    await log_activity("Changement de statut en masse", "entreprise", detail=f"{len(ids)} entreprises → {status}", auto=False)
    return {"updated": len(ids)}

@api.post("/import/preview")
async def import_preview(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Étape 1 : détecte format/encodage/séparateur, propose un mappage, renvoie un aperçu."""
    content = await file.read()
    if not content:
        await log_error("Champ obligatoire manquant", "Fichier d'import vide")
        raise HTTPException(400, "Le fichier est vide.")
    try:
        rows, headers, meta = import_service.parse_file(content, file.filename)
    except ValueError as e:
        await log_error("Source inaccessible", f"Import illisible : {e}")
        raise HTTPException(400, str(e))
    if not rows:
        raise HTTPException(400, "Aucune ligne de données valide détectée.")
    mapping, unrecognized = import_service.auto_map(headers)
    if "name" not in mapping:
        # on renvoie quand même l'aperçu pour permettre un mappage manuel
        pass
    records, warnings = import_service.build_records(rows, mapping)
    internal_dups = import_service.find_internal_duplicates(records)
    # doublons avec la base
    existing_names = set()
    all_comp = await db.companies.find({}, {"_id": 0, "name": 1, "website": 1}).to_list(5000)
    for c in all_comp:
        existing_names.add(import_service.norm_header(c.get("name", "")))
    db_dups = sum(1 for r in records if import_service.norm_header(r.get("name", "")) in existing_names)
    contacts_detected = sum(1 for r in records if r.get("_contact"))

    import_id = new_id()
    await db.import_sessions.insert_one({
        "id": import_id, "rows": rows, "headers": headers, "meta": meta,
        "mapping": mapping, "created_at": now_iso(), "user": user.get("name")})
    return {
        "import_id": import_id, "meta": meta, "headers": headers,
        "mapping": mapping, "field_labels": import_service.FIELD_LABELS,
        "available_fields": list(import_service.FIELD_LABELS.keys()),
        "unrecognized": unrecognized, "sample": rows[:5],
        "valid_rows": len(records), "internal_duplicates": len(internal_dups),
        "db_duplicates": db_dups, "contacts_detected": contacts_detected,
        "warnings": warnings[:50], "warning_count": len(warnings),
        "name_mapped": "name" in mapping,
    }


class ConfirmImportIn(BaseModel):
    import_id: str
    mapping: dict
    duplicate_strategy: str = "ignore"  # ignore | update | create_anyway


@api.post("/import/confirm")
async def import_confirm(body: ConfirmImportIn, user: dict = Depends(get_current_user)):
    """Étape 2 : crée réellement les entreprises et contacts selon le mappage validé."""
    session = await db.import_sessions.find_one({"id": body.import_id}, {"_id": 0})
    if not session:
        raise HTTPException(404, "Session d'import expirée. Recommencez.")
    mapping = {k: v for k, v in (body.mapping or {}).items() if v}
    if "name" not in mapping:
        raise HTTPException(400, "Le champ obligatoire « Nom entreprise » n'est mappé à aucune colonne.")
    records, warnings = import_service.build_records(session["rows"], mapping)
    internal_dups = set(import_service.find_internal_duplicates(records))

    report = {"total_lines": session["meta"].get("n_rows", 0), "companies_created": 0,
              "companies_updated": 0, "contacts_created": 0, "duplicates_ignored": 0,
              "rejected": len(warnings), "warnings": len(warnings)}
    rejected_rows = list(warnings)

    # index des entreprises existantes par nom normalisé (cohérent avec l'aperçu)
    all_comp = await db.companies.find({}, {"_id": 0}).to_list(5000)
    existing_by_norm = {import_service.norm_header(c.get("name", "")): c for c in all_comp}

    for r in records:
        if r["_line"] in internal_dups:
            report["duplicates_ignored"] += 1
            continue
        contact = r.pop("_contact", None)
        r.pop("_line", None); r.pop("_warnings", None)
        name_norm = import_service.norm_header(r.get("name", ""))
        existing = existing_by_norm.get(name_norm)
        if existing:
            if body.duplicate_strategy == "ignore":
                report["duplicates_ignored"] += 1
                continue
            elif body.duplicate_strategy == "update":
                upd = {k: v for k, v in r.items() if v and not existing.get(k)}  # fusion des champs manquants
                if upd:
                    upd["updated_at"] = now_iso()
                    await db.companies.update_one({"id": existing["id"]}, {"$set": upd})
                report["companies_updated"] += 1
                target_id = existing["id"]
            else:  # create_anyway
                target_id = await _create_company(r)
                existing_by_norm[name_norm] = {"id": target_id, "name": r.get("name", "")}
                report["companies_created"] += 1
        else:
            target_id = await _create_company(r)
            existing_by_norm[name_norm] = {"id": target_id, "name": r.get("name", "")}
            report["companies_created"] += 1
        if contact and target_id:
            cdoc = {"id": new_id(), "company_id": target_id,
                    "first_name": contact.get("first_name", ""), "last_name": contact.get("last_name", ""),
                    "role": contact.get("role", ""), "email": contact.get("email", ""),
                    "phone": contact.get("phone", ""), "linkedin": contact.get("linkedin", ""),
                    "decision_level": contact.get("decision_level", "autre"),
                    "department": contact.get("department", ""), "source": "Import",
                    "email_verified": "non vérifié", "do_not_contact": False,
                    "import_id": body.import_id, "created_at": now_iso()}
            await db.contacts.insert_one(cdoc)
            report["contacts_created"] += 1

    await db.imports.insert_one({"id": body.import_id, "meta": session["meta"], "report": report,
                                 "rejected_rows": rejected_rows, "user": user.get("name"),
                                 "strategy": body.duplicate_strategy, "created_at": now_iso()})
    await db.import_sessions.delete_one({"id": body.import_id})
    await log_activity("Import terminé", "entreprise",
                       detail=f"{report['companies_created']} créées, {report['companies_updated']} MAJ, "
                              f"{report['contacts_created']} contacts, {report['duplicates_ignored']} doublons ignorés, "
                              f"{report['rejected']} rejetées")
    report["import_id"] = body.import_id
    report["rejected_rows"] = rejected_rows
    return report


async def _create_company(r: dict) -> str:
    r["id"] = new_id()
    r["source"] = r.get("source") or "Import CSV"
    r["status"] = "Importé"
    r["created_at"] = now_iso()
    r["updated_at"] = now_iso()
    doc = Company(**{k: v for k, v in r.items() if k in Company.model_fields}).model_dump()
    doc["status"] = "Importé"
    doc["source"] = r["source"]
    await db.companies.insert_one(doc)
    return doc["id"]


@api.get("/imports")
async def list_imports(user: dict = Depends(get_current_user)):
    return await db.imports.find({}, {"_id": 0, "rejected_rows": 0}).sort("created_at", -1).to_list(100)

@api.get("/companies-export/csv")
async def export_csv(user: dict = Depends(get_current_user)):
    docs = await db.companies.find({}, {"_id": 0}).to_list(5000)
    output = io.StringIO()
    fields = ["name", "sector", "city", "postal_code", "website", "generic_email", "phone", "status", "score"]
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for d in docs:
        writer.writerow(d)
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=prospectia_entreprises.csv"})


# ---------- AI analysis & scoring ----------
@api.post("/companies/{cid}/analyze")
async def analyze(cid: str, user: dict = Depends(get_current_user)):
    company = await db.companies.find_one({"id": cid}, {"_id": 0})
    if not company:
        raise HTTPException(404, "Entreprise introuvable")
    await db.companies.update_one({"id": cid}, {"$set": {"status": "En analyse"}})
    await log_activity("Analyse lancée", "entreprise", cid, new_state=company["name"])
    try:
        analysis = await ai_service.analyze_company(company)
        score_res = await ai_service.score_company(company, analysis)
    except Exception as e:
        await log_error("Format IA invalide", str(e), cid, "Relancer l'analyse")
        await db.companies.update_one({"id": cid}, {"$set": {"status": "À analyser"}})
        raise HTTPException(502, f"Erreur IA: {e}")
    score = int(score_res.get("score", 0))
    await db.companies.update_one({"id": cid}, {"$set": {
        "analysis": analysis, "score_detail": score_res, "score": score,
        "status": "Qualifié" if score >= 50 else "Non qualifié", "updated_at": now_iso()}})
    await log_activity("Analyse terminée", "entreprise", cid, new_state=f"Score {score}")
    doc = await db.companies.find_one({"id": cid}, {"_id": 0})
    return doc

@api.put("/companies/{cid}/score")
async def update_score(cid: str, body: GenericIn, user: dict = Depends(get_current_user)):
    score = int(body.data.get("score", 0))
    await db.companies.update_one({"id": cid}, {"$set": {"score": score, "updated_at": now_iso()}})
    await log_activity("Score modifié manuellement", "entreprise", cid, new_state=str(score))
    return {"ok": True, "score": score}


# ---------- Contacts ----------
@api.get("/contacts")
async def list_contacts(user: dict = Depends(get_current_user), search: Optional[str] = None):
    q: dict = {}
    if search:
        q["$or"] = [{"first_name": {"$regex": search, "$options": "i"}},
                    {"last_name": {"$regex": search, "$options": "i"}},
                    {"email": {"$regex": search, "$options": "i"}}]
    docs = await db.contacts.find(q, {"_id": 0}).sort("first_name", 1).to_list(1000)
    company_ids = list({d["company_id"] for d in docs})
    companies = await db.companies.find({"id": {"$in": company_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(1000)
    cmap = {c["id"]: c["name"] for c in companies}
    for d in docs:
        d["company_name"] = cmap.get(d["company_id"], "")
    return docs

@api.post("/contacts")
async def create_contact(contact: Contact, user: dict = Depends(get_current_user)):
    doc = contact.model_dump()
    doc["created_at"] = now_iso()
    await db.contacts.insert_one(doc)
    await log_activity("Création de contact", "contact", doc["id"], new_state=f"{doc['first_name']} {doc['last_name']}")
    return clean(doc)

@api.put("/contacts/{cid}")
async def update_contact(cid: str, contact: Contact, user: dict = Depends(get_current_user)):
    doc = contact.model_dump()
    doc["id"] = cid
    await db.contacts.replace_one({"id": cid}, doc)
    await log_activity("Modification", "contact", cid)
    return clean(doc)

@api.delete("/contacts/{cid}")
async def delete_contact(cid: str, user: dict = Depends(get_current_user)):
    await db.contacts.delete_one({"id": cid})
    await log_activity("Suppression", "contact", cid)
    return {"ok": True}


# ---------- Email generation ----------
@api.post("/emails/generate")
async def generate_email_ep(body: GenericIn, user: dict = Depends(get_current_user)):
    cid = body.data.get("company_id")
    contact_id = body.data.get("contact_id", "")
    tone = body.data.get("tone", "consultatif")
    variants = body.data.get("variants", False)
    company = await db.companies.find_one({"id": cid}, {"_id": 0})
    if not company:
        raise HTTPException(404, "Entreprise introuvable")
    contact = await db.contacts.find_one({"id": contact_id}, {"_id": 0}) if contact_id else \
        await db.contacts.find_one({"company_id": cid}, {"_id": 0})
    if not contact:
        contact = {"first_name": "Madame, Monsieur", "last_name": "", "role": "Dirigeant"}
    analysis = company.get("analysis") or {}
    if not analysis:
        raise HTTPException(400, "Analyse insuffisante — lancez d'abord l'analyse IA")
    try:
        if variants:
            result = await ai_service.generate_variants(company, contact, analysis)
        else:
            result = await ai_service.generate_email(company, contact, analysis, tone)
    except Exception as e:
        await log_error("Format IA invalide", str(e), cid, "Régénérer l'email")
        raise HTTPException(502, f"Erreur IA: {e}")
    await log_activity("Message généré", "email", cid, new_state=company["name"])
    return {"result": result, "problem": (analysis.get("problems") or [""])[0],
            "service": analysis.get("recommended_service", "")}

@api.post("/emails")
async def save_email(email: EmailDraft, user: dict = Depends(get_current_user)):
    doc = email.model_dump()
    doc["created_at"] = now_iso()
    await db.emails.insert_one(doc)
    await log_activity("Message généré", "email", doc["id"], new_state=doc["subject"])
    return clean(doc)

@api.get("/emails")
async def list_emails(user: dict = Depends(get_current_user), status: Optional[str] = None):
    q = {"status": status} if status else {}
    docs = await db.emails.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)
    cids = list({d["company_id"] for d in docs})
    companies = await db.companies.find({"id": {"$in": cids}}, {"_id": 0}).to_list(1000)
    cmap = {c["id"]: c for c in companies}
    for d in docs:
        comp = cmap.get(d["company_id"], {})
        d["company_name"] = comp.get("name", "")
        d["company_score"] = comp.get("score", 0)
    return docs

@api.put("/emails/{eid}")
async def update_email(eid: str, email: EmailDraft, user: dict = Depends(get_current_user)):
    doc = email.model_dump()
    doc["id"] = eid
    await db.emails.replace_one({"id": eid}, doc)
    await log_activity("Message modifié", "email", eid)
    return clean(doc)

@api.post("/emails/{eid}/validate")
async def validate_email(eid: str, body: GenericIn, user: dict = Depends(get_current_user)):
    """Valide et envoie (mode simulation) ou programme un email."""
    action = body.data.get("action", "send")  # send, schedule, refuse, hold, irrelevant
    email = await db.emails.find_one({"id": eid}, {"_id": 0})
    if not email:
        raise HTTPException(404, "Email introuvable")
    company = await db.companies.find_one({"id": email["company_id"]}, {"_id": 0})

    if action in ("refuse", "irrelevant"):
        await db.emails.update_one({"id": eid}, {"$set": {"status": "Refusé"}})
        await log_activity("Message refusé", "email", eid)
        return {"ok": True, "status": "Refusé"}
    if action == "hold":
        await db.emails.update_one({"id": eid}, {"$set": {"status": "À valider"}})
        return {"ok": True, "status": "À valider"}

    # pre-send verifications
    contact = await db.contacts.find_one({"company_id": email["company_id"]}, {"_id": 0})
    dest = (contact or {}).get("email") or (company or {}).get("generic_email")
    if not dest:
        await log_error("Email invalide", "Aucune adresse destinataire", eid, "Ajouter un email au contact")
        raise HTTPException(400, "Aucune adresse email destinataire")
    excluded = await db.exclusions.find_one({"email": dest})
    if excluded or (contact and contact.get("do_not_contact")):
        await log_error("Prospect exclu", f"{dest} figure sur la liste d'exclusion", eid)
        raise HTTPException(400, "Destinataire sur liste d'exclusion")

    if action == "schedule":
        sched = body.data.get("scheduled_date", now_iso())
        await db.emails.update_one({"id": eid}, {"$set": {"status": "Programmé", "scheduled_date": sched}})
        await log_activity("Message validé", "email", eid, new_state="Programmé")
        return {"ok": True, "status": "Programmé"}

    # send (simulation)
    await db.emails.update_one({"id": eid}, {"$set": {"status": "Envoyé", "sent_at": now_iso()}})
    await db.companies.update_one({"id": email["company_id"]}, {"$set": {"status": "Contacté", "updated_at": now_iso()}})
    # schedule follow-ups
    settings = await db.settings.find_one({"id": "global"}, {"_id": 0})
    delays = settings.get("prospection", {}).get("followup_delays", [3, 7, 14]) if settings else [3, 7, 14]
    for i, d in enumerate(delays, start=1):
        due = (datetime.now(timezone.utc) + timedelta(days=d)).isoformat()
        await db.followups.insert_one({
            "id": new_id(), "company_id": email["company_id"], "email_id": eid,
            "level": i, "due_date": due, "status": "Programmée", "subject": "", "body": "",
            "created_at": now_iso()})
    await log_activity("Email envoyé", "email", eid, new_state=f"→ {dest} (simulation)", auto=False)
    await log_activity("Relance programmée", "email", eid, detail=f"J+{','.join(map(str, delays))}", auto=True)
    return {"ok": True, "status": "Envoyé", "simulation": True}


# ---------- Follow-ups ----------
@api.get("/followups")
async def list_followups(user: dict = Depends(get_current_user)):
    docs = await db.followups.find({}, {"_id": 0}).sort("due_date", 1).to_list(1000)
    cids = list({d["company_id"] for d in docs})
    companies = await db.companies.find({"id": {"$in": cids}}, {"_id": 0}).to_list(1000)
    cmap = {c["id"]: c for c in companies}
    for d in docs:
        c = cmap.get(d["company_id"], {})
        d["company_name"] = c.get("name", "")
        d["company_status"] = c.get("status", "")
    return docs

@api.post("/followups/{fid}/send")
async def send_followup(fid: str, user: dict = Depends(get_current_user)):
    fu = await db.followups.find_one({"id": fid}, {"_id": 0})
    if not fu:
        raise HTTPException(404, "Relance introuvable")
    company = await db.companies.find_one({"id": fu["company_id"]}, {"_id": 0})
    # verifications
    if company and company.get("status") in ["A répondu", "Intéressé", "Client", "Refus", "Ne plus contacter"]:
        await db.followups.update_one({"id": fid}, {"$set": {"status": "Annulée"}})
        await log_error("Relance bloquée", f"Prospect en statut {company.get('status')}", fid, "Relance annulée automatiquement")
        raise HTTPException(400, f"Relance annulée : prospect en statut {company.get('status')}")
    await db.followups.update_one({"id": fid}, {"$set": {"status": "Envoyée", "sent_at": now_iso()}})
    status_map = {1: "Relance 1", 2: "Relance 2", 3: "Relance finale"}
    await db.companies.update_one({"id": fu["company_id"]}, {"$set": {"status": status_map.get(fu["level"], "Relance 1")}})
    await log_activity("Relance envoyée", "relance", fid, new_state=f"Niveau {fu['level']} (simulation)", auto=False)
    return {"ok": True}

@api.post("/followups/{fid}/generate")
async def gen_followup(fid: str, user: dict = Depends(get_current_user)):
    fu = await db.followups.find_one({"id": fid}, {"_id": 0})
    if not fu:
        raise HTTPException(404, "Relance introuvable")
    company = await db.companies.find_one({"id": fu["company_id"]}, {"_id": 0})
    contact = await db.contacts.find_one({"company_id": fu["company_id"]}, {"_id": 0}) or {"first_name": "Madame, Monsieur"}
    try:
        res = await ai_service.generate_followup(company, contact, fu["level"])
    except Exception as e:
        await log_error("Format IA invalide", str(e), fid)
        raise HTTPException(502, f"Erreur IA: {e}")
    await db.followups.update_one({"id": fid}, {"$set": {"subject": res.get("subject"), "body": res.get("body")}})
    return res


# ---------- Replies ----------
@api.get("/replies")
async def list_replies(user: dict = Depends(get_current_user)):
    docs = await db.replies.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    cids = list({d["company_id"] for d in docs})
    companies = await db.companies.find({"id": {"$in": cids}}, {"_id": 0}).to_list(1000)
    cmap = {c["id"]: c.get("name", "") for c in companies}
    for d in docs:
        d["company_name"] = cmap.get(d["company_id"], "")
    return docs

@api.post("/replies")
async def create_reply(body: ReplyIn, user: dict = Depends(get_current_user)):
    company = await db.companies.find_one({"id": body.company_id}, {"_id": 0})
    if not company:
        raise HTTPException(404, "Entreprise introuvable")
    try:
        analysis = await ai_service.classify_reply(body.text, company)
    except Exception as e:
        await log_error("Format IA invalide", str(e), body.company_id)
        raise HTTPException(502, f"Erreur IA: {e}")
    doc = {"id": new_id(), "company_id": body.company_id, "email_id": body.email_id,
           "text": body.text, "analysis": analysis, "category": analysis.get("category"),
           "handled": False, "created_at": now_iso()}
    await db.replies.insert_one(doc)
    await log_activity("Réponse reçue", "réponse", doc["id"], new_state=analysis.get("category"))
    await log_activity("Réponse classée", "réponse", doc["id"], new_state=analysis.get("category"), auto=True)

    cat = analysis.get("category")
    # stop follow-ups on any reply
    await db.followups.update_many({"company_id": body.company_id, "status": "Programmée"}, {"$set": {"status": "Annulée"}})
    contact = await db.contacts.find_one({"company_id": body.company_id}, {"_id": 0})
    dest = (contact or {}).get("email") or company.get("generic_email")
    if cat == "Ne plus contacter":
        await db.exclusions.insert_one({"id": new_id(), "email": dest, "domain": "", "company": company["name"],
                                        "reason": "Demande explicite du prospect", "source": "Réponse email", "created_at": now_iso()})
        await db.companies.update_one({"id": body.company_id}, {"$set": {"status": "Ne plus contacter"}})
        await log_activity("Contact exclu", "exclusion", body.company_id, new_state=dest, auto=True)
    elif cat == "Refus":
        await db.companies.update_one({"id": body.company_id}, {"$set": {"status": "Refus"}})
    elif cat in ("Intéressé", "Souhaite un rendez-vous", "Demande d'informations"):
        await db.companies.update_one({"id": body.company_id}, {"$set": {"status": "Intéressé"}})
        opp = {"id": new_id(), "company_id": body.company_id, "company_name": company["name"],
               "contact": f"{(contact or {}).get('first_name','')} {(contact or {}).get('last_name','')}".strip(),
               "need": analysis.get("intent", ""), "service": company.get("analysis", {}).get("recommended_service", ""),
               "estimated_value": 0, "probability": 40, "stage": "Intérêt détecté",
               "next_action": analysis.get("next_action", ""), "created_at": now_iso()}
        await db.opportunities.insert_one(opp)
        await log_activity("Opportunité créée", "opportunité", opp["id"], new_state=company["name"], auto=True)
    else:
        await db.companies.update_one({"id": body.company_id}, {"$set": {"status": "A répondu"}})
    return clean(doc)


# ---------- Opportunities ----------
@api.get("/opportunities")
async def list_opps(user: dict = Depends(get_current_user)):
    return await db.opportunities.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.put("/opportunities/{oid}")
async def update_opp(oid: str, body: GenericIn, user: dict = Depends(get_current_user)):
    await db.opportunities.update_one({"id": oid}, {"$set": body.data})
    await log_activity("Modification", "opportunité", oid, new_state=body.data.get("stage", ""))
    return {"ok": True}


# ---------- Campaigns ----------
@api.get("/campaigns")
async def list_campaigns(user: dict = Depends(get_current_user)):
    docs = await db.campaigns.find({}, {"_id": 0}).sort("name", 1).to_list(1000)
    for d in docs:
        d["prospect_count"] = await db.companies.count_documents({"sector": d.get("sector")})
        d["sent_count"] = await db.emails.count_documents({"campaign_id": d["id"], "status": "Envoyé"})
    return docs

@api.post("/campaigns")
async def create_campaign(c: Campaign, user: dict = Depends(get_current_user)):
    doc = c.model_dump()
    doc["created_at"] = now_iso()
    await db.campaigns.insert_one(doc)
    await log_activity("Création", "campagne", doc["id"], new_state=doc["name"])
    return clean(doc)

@api.put("/campaigns/{cid}")
async def update_campaign(cid: str, c: Campaign, user: dict = Depends(get_current_user)):
    doc = c.model_dump()
    doc["id"] = cid
    await db.campaigns.replace_one({"id": cid}, doc)
    await log_activity("Modification", "campagne", cid, new_state=doc.get("status"))
    return clean(doc)

@api.delete("/campaigns/{cid}")
async def delete_campaign(cid: str, user: dict = Depends(get_current_user)):
    await db.campaigns.delete_one({"id": cid})
    return {"ok": True}


# ---------- Templates ----------
@api.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    return await db.templates.find({}, {"_id": 0}).sort("type", 1).to_list(1000)

@api.post("/templates")
async def create_template(t: Template, user: dict = Depends(get_current_user)):
    doc = t.model_dump()
    doc["created_at"] = now_iso()
    await db.templates.insert_one(doc)
    return clean(doc)

@api.put("/templates/{tid}")
async def update_template(tid: str, t: Template, user: dict = Depends(get_current_user)):
    doc = t.model_dump()
    doc["id"] = tid
    await db.templates.replace_one({"id": tid}, doc)
    return clean(doc)

@api.delete("/templates/{tid}")
async def delete_template(tid: str, user: dict = Depends(get_current_user)):
    await db.templates.delete_one({"id": tid})
    return {"ok": True}


# ---------- Services ----------
@api.get("/services")
async def list_services(user: dict = Depends(get_current_user)):
    return await db.services.find({}, {"_id": 0}).to_list(1000)


# ---------- Exclusions ----------
@api.get("/exclusions")
async def list_exclusions(user: dict = Depends(get_current_user)):
    return await db.exclusions.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)

@api.post("/exclusions")
async def create_exclusion(body: GenericIn, user: dict = Depends(get_current_user)):
    doc = {"id": new_id(), **body.data, "source": body.data.get("source", "Ajout manuel"), "created_at": now_iso()}
    await db.exclusions.insert_one(doc)
    await log_activity("Contact exclu", "exclusion", doc["id"], new_state=doc.get("email", ""))
    return clean(doc)

@api.delete("/exclusions/{xid}")
async def delete_exclusion(xid: str, user: dict = Depends(get_current_user)):
    await db.exclusions.delete_one({"id": xid})
    return {"ok": True}


# ---------- Activity log & errors ----------
@api.get("/activity")
async def list_activity(user: dict = Depends(get_current_user), limit: int = 200):
    return await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)

@api.get("/errors")
async def list_errors(user: dict = Depends(get_current_user)):
    return await db.errors.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)

@api.post("/errors/{err_id}/resolve")
async def resolve_error(err_id: str, user: dict = Depends(get_current_user)):
    await db.errors.update_one({"id": err_id}, {"$set": {"resolved": True}})
    return {"ok": True}


# ---------- Settings ----------
@api.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    s = await db.settings.find_one({"id": "global"}, {"_id": 0})
    if not s:
        s = {"id": "global", **seed_data.DEFAULT_SETTINGS}
        await db.settings.insert_one(s)
        s.pop("_id", None)
    return s

@api.put("/settings")
async def update_settings(body: GenericIn, user: dict = Depends(get_current_user)):
    await db.settings.update_one({"id": "global"}, {"$set": body.data}, upsert=True)
    await log_activity("Modification", "paramètres")
    s = await db.settings.find_one({"id": "global"}, {"_id": 0})
    return s


# ---------- Dashboard ----------
@api.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)):
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    companies = await db.companies.find({}, {"_id": 0}).to_list(5000)
    total = len(companies)
    by_status: dict = {}
    by_sector: dict = {}
    for c in companies:
        by_status[c.get("status", "?")] = by_status.get(c.get("status", "?"), 0) + 1
        by_sector[c.get("sector", "?")] = by_sector.get(c.get("sector", "?"), 0) + 1

    def count_status(*ss):
        return sum(by_status.get(s, 0) for s in ss)

    emails_sent = await db.emails.count_documents({"status": "Envoyé"})
    to_validate = await db.emails.count_documents({"status": "À valider"})
    followups_scheduled = await db.followups.count_documents({"status": "Programmée"})
    replies_total = await db.replies.count_documents({})
    positive_replies = await db.replies.count_documents({"category": {"$in": ["Intéressé", "Souhaite un rendez-vous", "Demande d'informations"]}})
    opportunities = await db.opportunities.count_documents({})
    clients = count_status("Client")
    new_week = await db.companies.count_documents({"created_at": {"$gte": week_ago}})

    response_rate = round((replies_total / emails_sent * 100), 1) if emails_sent else 0
    positive_rate = round((positive_replies / replies_total * 100), 1) if replies_total else 0
    rdv_rate = round((count_status("Rendez-vous") / emails_sent * 100), 1) if emails_sent else 0
    conv_rate = round((clients / total * 100), 1) if total else 0

    # priority actions
    priority = {
        "messages_a_valider": to_validate,
        "prospects_a_relancer": followups_scheduled,
        "reponses_positives_non_traitees": await db.replies.count_documents({"handled": False, "category": {"$in": ["Intéressé", "Souhaite un rendez-vous"]}}),
        "prospects_sans_action": count_status("Nouveau", "À analyser"),
        "erreurs_automatisation": await db.errors.count_documents({"resolved": False}),
    }

    funnel = [
        {"stage": "Prospects", "value": total},
        {"stage": "Qualifiés", "value": count_status("Qualifié", "Prêt pour message", "À valider")},
        {"stage": "Contactés", "value": count_status("Contacté", "Relance 1", "Relance 2", "Relance finale", "A répondu", "Intéressé", "Rendez-vous", "Client")},
        {"stage": "Réponses", "value": replies_total},
        {"stage": "Intéressés", "value": count_status("Intéressé", "Rendez-vous", "Proposition envoyée", "Client")},
        {"stage": "Clients", "value": clients},
    ]

    return {
        "kpis": {
            "total_prospects": total, "new_week": new_week,
            "to_analyze": count_status("À analyser", "En analyse", "Nouveau"),
            "qualified": count_status("Qualifié"), "to_validate": to_validate,
            "emails_sent": emails_sent, "followups_scheduled": followups_scheduled,
            "replies": replies_total, "positive_replies": positive_replies,
            "appointments": count_status("Rendez-vous"), "proposals": count_status("Proposition envoyée"),
            "clients": clients, "potential_revenue": opportunities * 3000, "signed_revenue": clients * 4500,
            "response_rate": response_rate, "positive_rate": positive_rate,
            "rdv_rate": rdv_rate, "conversion_rate": conv_rate,
        },
        "by_status": [{"name": k, "value": v} for k, v in by_status.items()],
        "by_sector": [{"name": k, "value": v} for k, v in by_sector.items()],
        "funnel": funnel,
        "priority": priority,
    }


# ---------- Demo data ----------
@api.post("/demo/seed")
async def seed_demo(user: dict = Depends(get_current_user)):
    await clear_demo_internal()
    company_ids = []
    for i, (name, sector, city, cp, web, email, size, status, score) in enumerate(seed_data.DEMO_COMPANIES):
        cid = new_id()
        company_ids.append(cid)
        await db.companies.insert_one({
            "id": cid, "name": name, "sector": sector, "city": city, "postal_code": cp, "region": "Île-de-France",
            "country": "France", "website": web, "generic_email": email, "size": size, "status": status,
            "score": score, "source": "Données de démonstration", "tags": ["démo"], "is_demo": True,
            "legal_name": "", "description": f"{sector} basé à {city}.", "phone": "01 23 45 67 89",
            "analysis": {"summary": f"{name} est un acteur du secteur {sector}.",
                         "problems": ["Site peu optimisé pour la conversion", "Absence de prise de rendez-vous en ligne"],
                         "consequences": ["Perte de contacts qualifiés"],
                         "recommended_service": "Tunnel de conversion", "confidence": "moyen",
                         "prospecting_angle": "Améliorer la conversion des visiteurs"} if score else None,
            "created_at": now_iso(), "updated_at": now_iso()})
        fn, ln, role, level, cemail = seed_data.DEMO_CONTACTS[i]
        await db.contacts.insert_one({"id": new_id(), "company_id": cid, "first_name": fn, "last_name": ln,
                                      "role": role, "decision_level": level, "email": cemail, "email_verified": "vérifié",
                                      "is_demo": True, "do_not_contact": False, "created_at": now_iso()})
    for name, sector, geo, status, offer in seed_data.DEMO_CAMPAIGNS:
        await db.campaigns.insert_one({"id": new_id(), "name": name, "sector": sector, "geo_zone": geo,
                                       "status": status, "offer": offer, "daily_volume": 5, "max_prospects": 100,
                                       "followup_sequence": [3, 7, 14], "is_demo": True, "created_at": now_iso()})
    # emails
    for cid in company_ids[:5]:
        c = await db.companies.find_one({"id": cid}, {"_id": 0})
        await db.emails.insert_one({"id": new_id(), "company_id": cid, "subject": "Une remarque concernant votre acquisition digitale",
                                    "body": f"Bonjour,\n\nEn consultant {c['name']}, j'ai remarqué quelques pistes d'amélioration...\n\nBien cordialement,\nJean-Philippe Koffi",
                                    "status": "À valider" if c["status"] in ("Qualifié",) else "Envoyé", "tone": "consultatif",
                                    "is_demo": True, "created_at": now_iso()})
    # replies
    reply_samples = [("Bonjour, oui cela m'intéresse, pouvons-nous en discuter ?", 3),
                     ("Merci mais nous sommes déjà accompagnés.", 8),
                     ("Pouvez-vous m'envoyer plus d'informations ?", 6)]
    for text, idx in reply_samples:
        c = await db.companies.find_one({"id": company_ids[idx]}, {"_id": 0})
        cat = "Intéressé" if "intéresse" in text else ("Déjà accompagné" if "accompagnés" in text else "Demande d'informations")
        await db.replies.insert_one({"id": new_id(), "company_id": company_ids[idx], "text": text, "category": cat,
                                     "analysis": {"category": cat, "sentiment": "positif" if cat != "Déjà accompagné" else "neutre",
                                                  "interest_level": "élevé" if cat == "Intéressé" else "faible",
                                                  "summary": text, "next_action": "Recontacter"}, "handled": False,
                                     "is_demo": True, "created_at": now_iso()})
    # opportunities
    for idx in [3, 9]:
        c = await db.companies.find_one({"id": company_ids[idx]}, {"_id": 0})
        await db.opportunities.insert_one({"id": new_id(), "company_id": company_ids[idx], "company_name": c["name"],
                                           "contact": "", "need": "Refonte du tunnel de conversion", "service": "Tunnel de conversion",
                                           "estimated_value": 4500, "probability": 60, "stage": "Rendez-vous planifié",
                                           "next_action": "Préparer le rendez-vous", "is_demo": True, "created_at": now_iso()})
    await log_activity("Données de démonstration créées", "système", detail="10 entreprises, 10 contacts, 3 campagnes")
    return {"ok": True, "message": "Données de démonstration créées"}

async def clear_demo_internal():
    for col in ["companies", "contacts", "campaigns", "emails", "replies", "opportunities", "followups"]:
        await db[col].delete_many({"is_demo": True})

@api.delete("/demo/clear")
async def clear_demo(user: dict = Depends(get_current_user)):
    await clear_demo_internal()
    await log_activity("Données de démonstration supprimées", "système")
    return {"ok": True}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True,
                   allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    # indexes
    await db.users.create_index("email", unique=True)
    await db.companies.create_index("name")
    # seed admin
    email = os.environ["ADMIN_EMAIL"].lower()
    existing = await db.users.find_one({"email": email})
    pw = os.environ["ADMIN_PASSWORD"]
    if not existing:
        await db.users.insert_one({"id": new_id(), "email": email, "password_hash": hash_password(pw),
                                   "name": os.environ.get("ADMIN_NAME", "Admin"), "role": "admin", "created_at": now_iso()})
        logger.info("Admin créé")
    elif not verify_password(pw, existing["password_hash"]):
        await db.users.update_one({"email": email}, {"$set": {"password_hash": hash_password(pw)}})
    # seed services & templates & settings
    if await db.services.count_documents({}) == 0:
        for s in seed_data.DEFAULT_SERVICES:
            await db.services.insert_one({"id": new_id(), **s})
    if await db.templates.count_documents({}) == 0:
        for t in seed_data.DEFAULT_TEMPLATES:
            await db.templates.insert_one({"id": new_id(), **t})
    if not await db.settings.find_one({"id": "global"}):
        await db.settings.insert_one({"id": "global", **seed_data.DEFAULT_SETTINGS})


@app.on_event("shutdown")
async def shutdown():
    client.close()
