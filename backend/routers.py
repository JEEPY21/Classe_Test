"""Domain routes: CV (bloc 1), Job (bloc 2), Generation (bloc 3),
ATS (bloc 4), Export (bloc 5). All scoped to the authenticated user (multi-user ready)."""
import io
import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from db import db
from auth import get_current_user
from models import (CVUpdateInput, JobOfferInput, GenerateInput,
                    ConfirmSkillsInput, DecisionsInput, StructuredCV, new_id, now_iso,
                    ApplicationCreate, ApplicationUpdate)
import llm_service
import export_service
import ats_service
from extraction import extract_text

router = APIRouter()


# ---------------- helpers ----------------
async def _get_cv(cv_id: str, user: dict) -> dict:
    doc = await db.cvs.find_one({"id": cv_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="CV introuvable")
    return doc


async def _get_job(job_id: str, user: dict) -> dict:
    doc = await db.jobs.find_one({"id": job_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return doc


async def _get_session(sid: str, user: dict) -> dict:
    doc = await db.sessions.find_one({"id": sid, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return doc


def _strip(doc: dict) -> dict:
    doc.pop("_id", None)
    return doc


# ---------------- BLOC 1: CV ----------------
cv_router = APIRouter(prefix="/cv", tags=["cv"])


@cv_router.post("/upload")
async def upload_cv(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Fichier vide")
    try:
        raw_text = extract_text(file.filename, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if len(raw_text) < 30:
        raise HTTPException(status_code=422,
                            detail="Impossible d'extraire du texte (CV scanné en image ?). Fournissez un PDF/DOCX au texte natif.")
    try:
        structured = await llm_service.structure_cv(raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Échec de la structuration IA : {str(e)[:150]}")
    # ensure ids on nested lists via pydantic
    structured = StructuredCV(**structured).model_dump()
    doc = {"id": new_id(), "user_id": user["id"], "filename": file.filename,
           "raw_text": raw_text, "structured": structured,
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.cvs.insert_one(doc)
    return _strip(doc)


@cv_router.get("")
async def list_cvs(user: dict = Depends(get_current_user)):
    docs = await db.cvs.find({"user_id": user["id"]}, {"_id": 0, "raw_text": 0}).sort("created_at", -1).to_list(100)
    return docs


@cv_router.get("/{cv_id}")
async def get_cv(cv_id: str, user: dict = Depends(get_current_user)):
    return _strip(await _get_cv(cv_id, user))


@cv_router.put("/{cv_id}")
async def update_cv(cv_id: str, body: CVUpdateInput, user: dict = Depends(get_current_user)):
    await _get_cv(cv_id, user)
    await db.cvs.update_one({"id": cv_id, "user_id": user["id"]},
                            {"$set": {"structured": body.structured.model_dump(), "updated_at": now_iso()}})
    return _strip(await _get_cv(cv_id, user))


@cv_router.delete("/{cv_id}")
async def delete_cv(cv_id: str, user: dict = Depends(get_current_user)):
    """RGPD — suppression du CV source et des données associées à la demande de l'utilisateur."""
    await _get_cv(cv_id, user)
    await db.cvs.delete_one({"id": cv_id, "user_id": user["id"]})
    await db.sessions.delete_many({"cv_id": cv_id, "user_id": user["id"]})
    return {"deleted": True}


# ---------------- BLOC 2: Job offer ----------------
job_router = APIRouter(prefix="/job", tags=["job"])


@job_router.post("/analyze")
async def analyze_job(body: JobOfferInput, user: dict = Depends(get_current_user)):
    try:
        analysis = await llm_service.analyze_job(body.raw_text)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Échec de l'analyse IA : {str(e)[:150]}")
    doc = {"id": new_id(), "user_id": user["id"], "raw_text": body.raw_text,
           "analysis": analysis, "created_at": now_iso()}
    await db.jobs.insert_one(doc)
    return _strip(doc)


@job_router.get("/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    return _strip(await _get_job(job_id, user))


# ---------------- BLOC 3: Controlled generation ----------------
gen_router = APIRouter(prefix="/generate", tags=["generate"])


async def _run_generation(sid: str, cv_structured: dict, job_analysis: dict, target: str,
                          confirmed_skills: list = None):
    confirmed_skills = confirmed_skills or []
    try:
        # Two distinct LLM calls, run concurrently: Sonnet for the CV, Haiku for the letter.
        cv_result, letter = await asyncio.wait_for(asyncio.gather(
            llm_service.generate_cv(cv_structured, job_analysis, target, confirmed_skills),
            llm_service.generate_cover_letter(cv_structured, job_analysis, target, confirmed_skills),
        ), timeout=180)
        await db.sessions.update_one({"id": sid}, {"$set": {
            "score": cv_result.get("score", {}),
            "experience_rewrites": cv_result.get("experience_rewrites", []),
            "skills_section": cv_result.get("skills_section", []),
            "cover_letter": {"paragraphs": letter.get("paragraphs", [])},
            "status": "ready",
            "error": None,
            "updated_at": now_iso(),
        }})
    except asyncio.TimeoutError:
        await db.sessions.update_one({"id": sid}, {"$set": {
            "status": "error",
            "error": "La génération a dépassé le délai maximal (3 min). Réessayez.",
            "updated_at": now_iso()}})
    except Exception as e:
        await db.sessions.update_one({"id": sid}, {"$set": {
            "status": "error", "error": str(e)[:300], "updated_at": now_iso()}})


@gen_router.post("")
async def generate(body: GenerateInput, user: dict = Depends(get_current_user)):
    cv = await _get_cv(body.cv_id, user)
    job = await _get_job(body.job_id, user)
    target = body.target_language or job["analysis"].get("language", "fr")
    doc = {"id": new_id(), "user_id": user["id"], "cv_id": body.cv_id, "job_id": body.job_id,
           "target_language": target,
           "score": {}, "experience_rewrites": [], "skills_section": [], "cover_letter": {"paragraphs": []},
           "confirmed_skills": [],
           "decisions": {"rewrites": [], "cover_letter_accepted": True},
           "status": "pending", "error": None,
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.sessions.insert_one(doc)
    # Launch the long LLM work in the background so the HTTP request returns immediately
    # (avoids the edge/proxy timeout -> 502 on long generations).
    asyncio.create_task(_run_generation(doc["id"], cv["structured"], job["analysis"], target))
    return _strip(doc)


@gen_router.get("/{sid}")
async def get_session(sid: str, user: dict = Depends(get_current_user)):
    return _strip(await _get_session(sid, user))


@gen_router.put("/{sid}/confirm-skills")
async def confirm_skills(sid: str, body: ConfirmSkillsInput, user: dict = Depends(get_current_user)):
    """Only skills explicitly confirmed by the user are stored (tagged as user confirmation for
    traceability), then the CV is REGENERATED so each confirmed skill is either woven into the
    matching experience bullet or placed once in the curated skills section."""
    session = await _get_session(sid, user)
    cv = await _get_cv(session["cv_id"], user)
    job = await _get_job(session["job_id"], user)
    confirmed_meta = [{"skill": s, "source": "confirmation_utilisateur"} for s in body.confirmed_skills]
    await db.sessions.update_one({"id": sid, "user_id": user["id"]},
                                 {"$set": {"confirmed_skills_meta": confirmed_meta,
                                           "confirmed_skills": body.confirmed_skills,
                                           "status": "pending", "error": None,
                                           "updated_at": now_iso()}})
    asyncio.create_task(_run_generation(sid, cv["structured"], job["analysis"],
                                        session.get("target_language", "fr"), body.confirmed_skills))
    return _strip(await _get_session(sid, user))


@gen_router.put("/{sid}/decisions")
async def save_decisions(sid: str, body: DecisionsInput, user: dict = Depends(get_current_user)):
    await _get_session(sid, user)
    session = await _get_session(sid, user)
    decisions = session.get("decisions", {"rewrites": [], "cover_letter_accepted": True})
    decisions["rewrites"] = [d.model_dump() for d in body.rewrites]
    if body.cover_letter_accepted is not None:
        decisions["cover_letter_accepted"] = body.cover_letter_accepted
    await db.sessions.update_one({"id": sid, "user_id": user["id"]},
                                 {"$set": {"decisions": decisions, "updated_at": now_iso()}})
    return _strip(await _get_session(sid, user))


# ---------------- BLOC 4: ATS quality control ----------------
ats_router = APIRouter(prefix="/ats", tags=["ats"])


@ats_router.post("/check")
async def ats_check(payload: dict, user: dict = Depends(get_current_user)):
    sid = payload.get("generation_id")
    template_id = payload.get("template_id", "classic")
    session = await _get_session(sid, user)
    cv = await _get_cv(session["cv_id"], user)
    final_cv = export_service.build_final_cv(cv["structured"], session)
    html = export_service.render_html(final_cv, template_id, session.get("target_language", "fr"))
    pdf = export_service.html_to_pdf(html)
    report = ats_service.run_ats_check(pdf, "matchipy_cv.pdf", final_cv)
    return report


# ---------------- BLOC 5: Templates & export ----------------
export_router = APIRouter(prefix="/export", tags=["export"])


@export_router.get("/templates")
async def templates():
    return export_service.TEMPLATES


@export_router.post("/preview")
async def preview(payload: dict, user: dict = Depends(get_current_user)):
    """Return the assembled final CV JSON + original for the before/after review screen."""
    sid = payload.get("generation_id")
    session = await _get_session(sid, user)
    cv = await _get_cv(session["cv_id"], user)
    final_cv = export_service.build_final_cv(cv["structured"], session)
    return {"original": cv["structured"], "final": final_cv,
            "cover_letter": session.get("cover_letter", {}),
            "target_language": session.get("target_language", "fr")}


@export_router.post("/download")
async def download(payload: dict, user: dict = Depends(get_current_user)):
    sid = payload.get("generation_id")
    template_id = payload.get("template_id", "classic")
    fmt = payload.get("format", "pdf")
    doc_type = payload.get("doc_type", "cv")
    session = await _get_session(sid, user)
    cv = await _get_cv(session["cv_id"], user)
    final_cv = export_service.build_final_cv(cv["structured"], session)
    lang = session.get("target_language", "fr")
    name = (final_cv.get("identity", {}).get("full_name") or "cv").replace(" ", "_")
    docx_media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    if doc_type == "cover_letter":
        paragraphs = (session.get("cover_letter") or {}).get("paragraphs", [])
        if not paragraphs:
            raise HTTPException(status_code=400, detail="Aucune lettre de motivation à exporter.")
        identity = final_cv.get("identity", {})
        if fmt == "docx":
            content = export_service.build_cover_letter_docx(identity, paragraphs, lang)
            media, filename = docx_media, f"Lettre_{name}.docx"
        else:
            html = export_service.render_cover_letter_html(identity, paragraphs, lang)
            content, media, filename = export_service.html_to_pdf(html), "application/pdf", f"Lettre_{name}.pdf"
    else:
        if fmt == "docx":
            content = export_service.build_docx(final_cv, lang)
            media, filename = docx_media, f"CV_{name}.docx"
        else:
            html = export_service.render_html(final_cv, template_id, lang)
            content, media, filename = export_service.html_to_pdf(html), "application/pdf", f"CV_{name}.pdf"

    return StreamingResponse(io.BytesIO(content), media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# ---------------- BLOC 3bis: Application tracking ----------------
app_router = APIRouter(prefix="/applications", tags=["applications"])


def _render_doc(final_cv, cover_paragraphs, template_id, lang, doc_type, fmt):
    docx_media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    name = (final_cv.get("identity", {}).get("full_name") or "cv").replace(" ", "_")
    if doc_type == "cover_letter":
        identity = final_cv.get("identity", {})
        if fmt == "docx":
            return export_service.build_cover_letter_docx(identity, cover_paragraphs, lang), docx_media, f"Lettre_{name}.docx"
        html = export_service.render_cover_letter_html(identity, cover_paragraphs, lang)
        return export_service.html_to_pdf(html), "application/pdf", f"Lettre_{name}.pdf"
    if fmt == "docx":
        return export_service.build_docx(final_cv, lang), docx_media, f"CV_{name}.docx"
    html = export_service.render_html(final_cv, template_id, lang)
    return export_service.html_to_pdf(html), "application/pdf", f"CV_{name}.pdf"


@app_router.post("")
async def create_application(body: ApplicationCreate, user: dict = Depends(get_current_user)):
    session = await _get_session(body.session_id, user)
    cv = await _get_cv(session["cv_id"], user)
    # Snapshot the reviewed CV + cover letter so the application stays intact even if the
    # session or source CV is later modified/deleted.
    final_cv = export_service.build_final_cv(cv["structured"], session)
    doc = {"id": new_id(), "user_id": user["id"], "session_id": body.session_id,
           "cv_id": session["cv_id"], "job_id": session.get("job_id"),
           "poste": body.poste, "entreprise": body.entreprise,
           "statut": body.statut,
           "date_candidature": body.date_candidature or now_iso()[:10],
           "notes": body.notes, "template_id": body.template_id,
           "target_language": session.get("target_language", "fr"),
           "snapshot": {"final_cv": final_cv,
                        "cover_letter": session.get("cover_letter", {"paragraphs": []})},
           "created_at": now_iso(), "updated_at": now_iso()}
    await db.applications.insert_one(doc)
    return _strip(doc)


@app_router.get("")
async def list_applications(statut: str = None, user: dict = Depends(get_current_user)):
    query = {"user_id": user["id"]}
    if statut:
        query["statut"] = statut
    docs = await db.applications.find(query, {"_id": 0, "snapshot": 0}).sort("created_at", -1).to_list(500)
    return docs


@app_router.put("/{app_id}")
async def update_application(app_id: str, body: ApplicationUpdate, user: dict = Depends(get_current_user)):
    existing = await db.applications.find_one({"id": app_id, "user_id": user["id"]})
    if not existing:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = now_iso()
    await db.applications.update_one({"id": app_id, "user_id": user["id"]}, {"$set": updates})
    doc = await db.applications.find_one({"id": app_id, "user_id": user["id"]}, {"_id": 0, "snapshot": 0})
    return doc


@app_router.delete("/{app_id}")
async def delete_application(app_id: str, user: dict = Depends(get_current_user)):
    res = await db.applications.delete_one({"id": app_id, "user_id": user["id"]})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    return {"deleted": True}


@app_router.post("/{app_id}/download")
async def download_application_doc(app_id: str, payload: dict, user: dict = Depends(get_current_user)):
    doc = await db.applications.find_one({"id": app_id, "user_id": user["id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    doc_type = payload.get("doc_type", "cv")
    fmt = payload.get("format", "pdf")
    snap = doc.get("snapshot", {})
    final_cv = snap.get("final_cv", {})
    cover = (snap.get("cover_letter") or {}).get("paragraphs", [])
    if doc_type == "cover_letter" and not cover:
        raise HTTPException(status_code=400, detail="Aucune lettre attachée à cette candidature.")
    content, media, filename = _render_doc(final_cv, cover, doc.get("template_id", "classic"),
                                           doc.get("target_language", "fr"), doc_type, fmt)
    return StreamingResponse(io.BytesIO(content), media_type=media,
                             headers={"Content-Disposition": f'attachment; filename="{filename}"'})


router.include_router(cv_router)
router.include_router(job_router)
router.include_router(gen_router)
router.include_router(ats_router)
router.include_router(export_router)
router.include_router(app_router)
