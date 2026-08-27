"""LLM service — Claude Sonnet 4.6 via Emergent universal key.
Enforces the non-negotiable rules: zero hallucination, keyword traceability,
content-only (JSON) generation. The LLM NEVER produces layout."""
import os
import json
import re
from emergentintegrations.llm.chat import LlmChat, UserMessage

MODEL_PROVIDER = "anthropic"
MODEL_NAME = "claude-sonnet-4-6"
MODEL_HAIKU = "claude-haiku-4-5-20251001"


def _key() -> str:
    return os.environ["EMERGENT_LLM_KEY"]


async def _ask(system: str, prompt: str, session_id: str, model: str = MODEL_NAME) -> str:
    chat = LlmChat(api_key=_key(), session_id=session_id, system_message=system).with_model(
        MODEL_PROVIDER, model)
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
async def generate_cv(cv: dict, job: dict, target_language: str, confirmed_skills: list) -> dict:
    """CV generation (Claude Sonnet). Produce ONLY the CV content (content-only JSON, no layout):
    - a transparent match score broken down by sub-criteria
    - line-by-line experience rewrite proposals (each keyword tagged with its source)
    - a curated skills_section (transverse skills only)
    The cover letter is generated separately by Claude Haiku."""
    lang_names = {"fr": "français", "en": "anglais", "es": "espagnol", "de": "allemand"}
    tl = lang_names.get(target_language, "français")
    system = (
        "Tu es un rédacteur de CV expert et rigoureux. RÈGLES NON NÉGOCIABLES:\n"
        "1. ZÉRO HALLUCINATION: n'invente jamais une expérience, une compétence, une date, "
        "un chiffre ou une réalisation absente du CV structuré fourni ou de la liste des "
        "compétences confirmées par l'utilisateur.\n"
        "2. TRAÇABILITÉ: chaque mot-clé/compétence que tu intègres doit provenir soit de l'offre, "
        "soit du CV, soit des compétences confirmées. Indique la source ('offre', 'cv', "
        "'confirmation_utilisateur').\n"
        "3. Reformule chaque puce d'expérience individuellement (verbes d'action, résultats chiffrés "
        "UNIQUEMENT si le chiffre existe déjà dans le CV source). Ne fusionne pas les puces.\n"
        "4. Le score doit être expliqué par sous-critère, jamais opaque.\n"
        "5. PLACEMENT DES COMPÉTENCES (règle stricte): pour CHAQUE compétence réelle du candidat "
        "(présente dans le CV ou confirmée manuellement), détermine si elle est rattachable à une "
        "expérience précise. SI OUI -> intègre-la NATURELLEMENT dans la puce de mission de cette "
        "expérience (reformulation), et NE la mets PAS dans skills_section. SI NON (logiciel "
        "transverse, langue, soft skill général, outil non lié à une mission précise) -> place-la "
        "dans skills_section. Une compétence n'apparaît qu'UNE SEULE FOIS au total : jamais à la fois "
        "dans une puce ET dans skills_section. skills_section est limitée à 12 éléments MAXIMUM, "
        "priorisés par pertinence vis-à-vis de l'offre.\n"
        f"6. Rédige tout le contenu généré en {tl}.\n"
        "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour."
    )
    schema = (
        '{'
        '"adapted_title":"","adapted_summary":"",'
        '"score":{"overall":0,"hard_skills":0,"soft_skills":0,"education":0,"keywords":0,'
        '"explanation":"","matched_hard_skills":[],"missing_hard_skills":[],'
        '"matched_soft_skills":[],"missing_soft_skills":[],"missing_keywords":[]},'
        '"experience_rewrites":[{"experience_id":"","role":"","company":"",'
        '"bullets":[{"original":"","proposed":"","keywords_used":[{"keyword":"","source":"offre"}]}]}],'
        '"skills_section":[{"skill":"","source":"cv"}]'
        '}'
    )
    prompt = (
        f"Voici le CV structuré du candidat (SEULE source de vérité factuelle):\n{json.dumps(cv, ensure_ascii=False)}\n\n"
        f"Voici l'analyse de l'offre d'emploi ciblée:\n{json.dumps(job, ensure_ascii=False)}\n\n"
        f"Compétences confirmées manuellement par l'utilisateur (à traiter comme réelles, source "
        f"'confirmation_utilisateur'):\n{json.dumps(confirmed_skills, ensure_ascii=False)}\n\n"
        "Produis:\n"
        "- adapted_title: le titre du poste à afficher EN HAUT du CV, adapté précisément au vocabulaire "
        "et à l'intitulé de l'offre ciblée (jamais générique), tout en restant fidèle au profil réel.\n"
        "- adapted_summary: une accroche / résumé de profil (2-3 phrases) alignée sur les attentes et le "
        "vocabulaire de l'offre, fondée uniquement sur le vécu réel du candidat (jamais générique, "
        "aucune invention).\n"
        "- score: chaque sous-score de 0 à 100 (hard_skills, soft_skills, education, keywords) + un "
        "overall pondéré, une explication claire, et les listes de compétences correspondantes/manquantes.\n"
        "- experience_rewrites: pour CHAQUE expérience du CV (garde le même experience_id), une "
        "reformulation puce par puce. 'original' = puce d'origine, 'proposed' = reformulation améliorée "
        "intégrant naturellement les compétences rattachables à cette expérience ET les mots-clés "
        "pertinents fondés sur le vécu réel. Pour chaque puce, liste keywords_used avec leur source.\n"
        "- skills_section: UNIQUEMENT les compétences réelles NON rattachables à une expérience précise "
        "(transverses/langues/soft skills généraux), dédupliquées, max 12, priorisées selon l'offre, "
        "chacune avec sa source. Ne JAMAIS y répéter une compétence déjà intégrée dans une puce.\n"
        f"SCHEMA: {schema}\n\nRenvoie uniquement le JSON."
    )
    data = _parse_json(await _ask(system, prompt, "generate-cv", model=MODEL_NAME))
    return _normalize_generation(data)


async def generate_cover_letter(cv: dict, job: dict, target_language: str, confirmed_skills: list) -> dict:
    """Cover letter generation (Claude Haiku). Grounded ONLY in the CV + offer. Human, natural style."""
    lang_names = {"fr": "français", "en": "anglais", "es": "espagnol", "de": "allemand"}
    tl = lang_names.get(target_language, "français")
    system = (
        "Tu es un candidat qui rédige sa propre lettre de motivation. RÈGLES NON NÉGOCIABLES:\n"
        "1. ZÉRO HALLUCINATION: fonde-toi uniquement sur le CV structuré + l'offre + les compétences "
        "confirmées. N'invente aucune expérience, compétence, date ou réalisation.\n"
        "2. STYLE: écris dans un style naturel et humain, comme une vraie personne. "
        "INTERDIT: les tirets longs (—), les listes à puces, les formules creuses et clichés "
        "(« je suis dynamique et motivé », « votre entreprise leader », etc.). "
        "Varie la longueur des phrases, sois direct, reflète la voix authentique du candidat.\n"
        f"3. Rédige la lettre en {tl}.\n"
        "Tu réponds UNIQUEMENT avec un objet JSON valide de la forme "
        '{"paragraphs":["...","..."]}, sans texte autour.'
    )
    prompt = (
        f"CV structuré du candidat (source de vérité):\n{json.dumps(cv, ensure_ascii=False)}\n\n"
        f"Analyse de l'offre ciblée:\n{json.dumps(job, ensure_ascii=False)}\n\n"
        f"Compétences confirmées par l'utilisateur:\n{json.dumps(confirmed_skills, ensure_ascii=False)}\n\n"
        "Rédige une lettre de motivation de 3 à 4 paragraphes, fondée uniquement sur ces éléments. "
        "Respecte strictement les règles de style (aucun tiret long, aucune puce, aucune formule creuse, "
        "phrases de longueurs variées, ton direct et humain). "
        'Renvoie uniquement le JSON: {"paragraphs":["paragraphe 1","paragraphe 2", ...]}.'
    )
    data = _parse_json(await _ask(system, prompt, "generate-letter", model=MODEL_HAIKU))
    paras = data.get("paragraphs") or []
    # safety net: strip any stray em dashes / bullet markers the model may have left
    clean = []
    for p in paras:
        if not isinstance(p, str):
            continue
        p = p.replace("—", ", ").replace("•", "").replace("- ", "").strip()
        if p:
            clean.append(p)
    return {"paragraphs": clean}


def _to_str_list(value) -> list:
    """Coerce a list that may contain strings or objects into a clean list of strings."""
    out = []
    for x in value or []:
        if isinstance(x, str):
            s = x.strip()
        elif isinstance(x, dict):
            s = str(x.get("skill") or x.get("keyword") or x.get("name") or "").strip()
        else:
            s = str(x).strip()
        if s:
            out.append(s)
    return out


def _normalize_generation(data: dict) -> dict:
    """Enforce the output schema so the UI always receives plain strings (Claude occasionally
    returns skill objects instead of strings)."""
    score = data.get("score") or {}
    for k in ("matched_hard_skills", "missing_hard_skills", "matched_soft_skills",
              "missing_soft_skills", "missing_keywords"):
        score[k] = _to_str_list(score.get(k))
    data["score"] = score
    woven = set()
    for r in data.get("experience_rewrites") or []:
        for b in r.get("bullets") or []:
            ku = []
            for k in b.get("keywords_used") or []:
                if isinstance(k, dict):
                    kw = str(k.get("keyword") or k.get("skill") or "").strip()
                    src = str(k.get("source") or "cv").strip()
                elif isinstance(k, str):
                    kw, src = k.strip(), "cv"
                else:
                    kw, src = str(k).strip(), "cv"
                if kw:
                    ku.append({"keyword": kw, "source": src})
                    woven.add(kw.lower())
            b["keywords_used"] = ku

    # skills_section: normalize to [{skill, source}], dedupe, drop skills already woven into
    # a bullet (a skill must appear only once), cap at 12.
    section = []
    seen = set()
    for item in data.get("skills_section") or []:
        if isinstance(item, dict):
            skill = str(item.get("skill") or item.get("keyword") or item.get("name") or "").strip()
            source = str(item.get("source") or "cv").strip()
        elif isinstance(item, str):
            skill, source = item.strip(), "cv"
        else:
            skill, source = str(item).strip(), "cv"
        low = skill.lower()
        if not skill or low in seen or low in woven:
            continue
        seen.add(low)
        section.append({"skill": skill, "source": source})
        if len(section) >= 12:
            break
    data["skills_section"] = section
    return data
