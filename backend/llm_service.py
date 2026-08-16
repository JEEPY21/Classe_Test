"""LLM service — Claude Sonnet 4.6 via Emergent universal key.
Enforces the non-negotiable rules: zero hallucination, keyword traceability,
content-only (JSON) generation. The LLM NEVER produces layout."""
import os
import json
import re
from emergentintegrations.llm.chat import LlmChat, UserMessage

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"


def _key() -> str:
    return os.environ["EMERGENT_LLM_KEY"]


async def _ask(system: str, prompt: str, session_id: str) -> str:
    chat = LlmChat(api_key=_key(), session_id=session_id, system_message=system).with_model(
        MODEL_PROVIDER, MODEL_NAME)
    return await chat.send_message(UserMessage(text=prompt))


def _parse_json(text: str) -> dict:
    text = text.strip()
    # strip markdown fences
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # grab outermost json object
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    return json.loads(text)


# ---------------- BLOC 1: structure a raw CV ----------------
async def structure_cv(raw_text: str) -> dict:
    system = (
        "Tu es un extracteur de données de CV. Règle ABSOLUE: tu n'inventes RIEN. "
        "Tu recopies uniquement ce qui est présent dans le texte source. Si une information "
        "est absente, laisse une chaîne vide ou une liste vide. N'ajoute jamais de compétence, "
        "de date, d'entreprise ou de réalisation qui n'apparaît pas explicitement. "
        "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour."
    )
    schema = (
        '{"identity":{"full_name":"","title":"","email":"","phone":"","location":"","links":[]},'
        '"summary":"",'
        '"experiences":[{"company":"","role":"","location":"","start_date":"","end_date":"","current":false,"bullets":[]}],'
        '"education":[{"institution":"","degree":"","field":"","start_date":"","end_date":""}],'
        '"skills":[],"languages":[{"language":"","level":""}]}'
    )
    prompt = (
        f"Extrais et structure ce CV dans le schéma JSON suivant (recopie fidèle, zéro invention):\n"
        f"SCHEMA: {schema}\n\nCV SOURCE:\n\"\"\"\n{raw_text}\n\"\"\"\n\n"
        "Renvoie uniquement le JSON rempli."
    )
    data = _parse_json(await _ask(system, prompt, "structure-cv"))
    return data


# ---------------- BLOC 2: analyze a job offer ----------------
async def analyze_job(raw_text: str) -> dict:
    system = (
        "Tu es un analyste d'offres d'emploi. Tu extrais fidèlement les informations de l'offre. "
        "Tu détectes la langue de l'offre parmi: fr, en, es, de. "
        "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour."
    )
    schema = ('{"job_title":"","company":"","hard_skills":[],"soft_skills":[],'
              '"keywords":[],"language":"fr"}')
    prompt = (
        f"Analyse cette offre d'emploi. Extrais l'intitulé du poste, l'entreprise si mentionnée, "
        f"les compétences techniques (hard_skills), les compétences comportementales (soft_skills), "
        f"les mots-clés récurrents importants (keywords), et la langue (fr/en/es/de).\n"
        f"SCHEMA: {schema}\n\nOFFRE:\n\"\"\"\n{raw_text}\n\"\"\"\n\nRenvoie uniquement le JSON."
    )
    data = _parse_json(await _ask(system, prompt, "analyze-job"))
    if data.get("language") not in ("fr", "en", "es", "de"):
        data["language"] = "fr"
    return data


# ---------------- BLOC 3: controlled generation ----------------
async def generate_match(cv: dict, job: dict, target_language: str, confirmed_skills: list) -> dict:
    """Cross the structured CV with job keywords. Produce:
    - a transparent match score broken down by sub-criteria
    - line-by-line experience rewrite proposals (each keyword tagged with its source)
    - a cover letter grounded ONLY in the CV + offer
    Everything is content only (JSON). No layout."""
    lang_names = {"fr": "français", "en": "anglais", "es": "espagnol", "de": "allemand"}
    tl = lang_names.get(target_language, "français")
    system = (
        "Tu es un rédacteur de CV expert et rigoureux. RÈGLES NON NÉGOCIABLES:\n"
        "1. ZÉRO HALLUCINATION: n'invente jamais une expérience, une compétence, une date, "
        "un chiffre ou une réalisation absente du CV structuré fourni.\n"
        "2. TRAÇABILITÉ: chaque mot-clé que tu intègres à une reformulation doit provenir soit "
        "de l'offre, soit du CV, soit de la liste des compétences confirmées par l'utilisateur. "
        "Indique la source de chaque mot-clé utilisé ('offre', 'cv', 'confirmation_utilisateur').\n"
        "3. Reformule chaque puce d'expérience individuellement (verbes d'action, résultats chiffrés "
        "UNIQUEMENT si le chiffre existe déjà dans le CV source). Ne fusionne pas les puces.\n"
        "4. Le score doit être expliqué par sous-critère, jamais opaque.\n"
        f"5. Rédige tout le contenu généré en {tl}.\n"
        "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour."
    )
    schema = (
        '{'
        '"score":{"overall":0,"hard_skills":0,"soft_skills":0,"education":0,"keywords":0,'
        '"explanation":"","matched_hard_skills":[],"missing_hard_skills":[],'
        '"matched_soft_skills":[],"missing_soft_skills":[],"missing_keywords":[]},'
        '"experience_rewrites":[{"experience_id":"","role":"","company":"",'
        '"bullets":[{"original":"","proposed":"","keywords_used":[{"keyword":"","source":"offre"}]}]}],'
        '"cover_letter":{"paragraphs":[]}'
        '}'
    )
    prompt = (
        f"Voici le CV structuré du candidat (SEULE source de vérité factuelle):\n{json.dumps(cv, ensure_ascii=False)}\n\n"
        f"Voici l'analyse de l'offre d'emploi ciblée:\n{json.dumps(job, ensure_ascii=False)}\n\n"
        f"Compétences confirmées manuellement par l'utilisateur (à traiter comme réelles, source "
        f"'confirmation_utilisateur'):\n{json.dumps(confirmed_skills, ensure_ascii=False)}\n\n"
        "Produis:\n"
        "- score: chaque sous-score de 0 à 100 (hard_skills, soft_skills, education, keywords) + un "
        "overall pondéré, une explication claire, et les listes de compétences correspondantes/manquantes.\n"
        "- experience_rewrites: pour CHAQUE expérience du CV (garde le même experience_id), une "
        "reformulation puce par puce. 'original' = puce d'origine, 'proposed' = reformulation améliorée "
        "intégrant naturellement les mots-clés pertinents ET fondés sur le vécu réel. Pour chaque puce, "
        "liste keywords_used avec leur source.\n"
        "- cover_letter: 3 à 4 paragraphes fondés uniquement sur le CV + l'offre, sans rien inventer.\n"
        f"SCHEMA: {schema}\n\nRenvoie uniquement le JSON."
    )
    data = _parse_json(await _ask(system, prompt, "generate-match"))
    return data
