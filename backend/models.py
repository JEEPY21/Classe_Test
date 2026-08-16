"""Pydantic models for Matchipy. Multi-user ready: every domain document carries user_id."""
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ---------- Auth ----------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class LoginInput(BaseModel):
    email: EmailStr
    password: str


# ---------- Structured CV ----------
class Identity(BaseModel):
    full_name: str = ""
    title: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: List[str] = []


class Experience(BaseModel):
    id: str = Field(default_factory=new_id)
    company: str = ""
    role: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    bullets: List[str] = []


class Education(BaseModel):
    id: str = Field(default_factory=new_id)
    institution: str = ""
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""


class Language(BaseModel):
    language: str = ""
    level: str = ""


class StructuredCV(BaseModel):
    identity: Identity = Field(default_factory=Identity)
    summary: str = ""
    experiences: List[Experience] = []
    education: List[Education] = []
    skills: List[str] = []
    languages: List[Language] = []


class CVUpdateInput(BaseModel):
    structured: StructuredCV


# ---------- Job Offer ----------
class JobAnalysis(BaseModel):
    job_title: str = ""
    company: str = ""
    hard_skills: List[str] = []
    soft_skills: List[str] = []
    keywords: List[str] = []
    language: Literal["fr", "en", "es", "de"] = "fr"


class JobOfferInput(BaseModel):
    raw_text: str = Field(min_length=20)


# ---------- Generation ----------
class GenerateInput(BaseModel):
    cv_id: str
    job_id: str
    target_language: Optional[Literal["fr", "en", "es", "de"]] = None


class ConfirmSkillsInput(BaseModel):
    confirmed_skills: List[str] = []


class RewriteDecision(BaseModel):
    experience_id: str
    accepted_bullets: List[int] = []  # indices of accepted proposed bullets


class DecisionsInput(BaseModel):
    rewrites: List[RewriteDecision] = []
    cover_letter_accepted: Optional[bool] = None
