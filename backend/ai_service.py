"""Service IA pour PROSPECTIA - analyse, scoring, génération d'emails, classification des réponses."""
import os
import json
import re
from emergentintegrations.llm.chat import LlmChat, UserMessage

LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
MODEL = ("openai", "gpt-5.5")


def _extract_json(text: str):
    """Extrait proprement un objet JSON d'une réponse LLM."""
    if not text:
        raise ValueError("Réponse IA vide")
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    return json.loads(text)


async def _run(system: str, prompt: str, session: str) -> dict:
    if not LLM_KEY:
        raise RuntimeError("Clé IA absente (EMERGENT_LLM_KEY)")
    chat = LlmChat(api_key=LLM_KEY, session_id=session, system_message=system).with_model(*MODEL)
    resp = await chat.send_message(UserMessage(text=prompt))
    text = resp if isinstance(resp, str) else str(resp)
    try:
        return _extract_json(text)
    except Exception as e:
        raise ValueError(f"Format IA invalide: {e}")


ANALYSIS_SYSTEM = (
    "Tu es un expert en acquisition digitale B2B qui analyse la présence numérique d'entreprises. "
    "Tu réponds UNIQUEMENT en JSON valide, en français. "
    "RÈGLE ABSOLUE : n'invente jamais un problème. Base-toi uniquement sur les données fournies. "
    "Si une information n'est pas disponible, indique 'Information non vérifiée'."
)


async def analyze_company(company: dict) -> dict:
    prompt = f"""Analyse la présence digitale de cette entreprise à partir des données publiques fournies.

Données de l'entreprise :
- Nom: {company.get('name')}
- Secteur: {company.get('sector')}
- Description: {company.get('description') or 'Non fournie'}
- Site internet: {company.get('website') or 'Aucun'}
- Ville: {company.get('city')}
- LinkedIn: {company.get('linkedin') or 'Aucun'}
- Facebook: {company.get('facebook') or 'Aucun'}
- Instagram: {company.get('instagram') or 'Aucun'}
- Taille estimée: {company.get('size') or 'Inconnue'}

Réponds STRICTEMENT avec ce JSON:
{{
  "summary": "résumé de l'activité (2-3 phrases)",
  "target_clientele": "description de la clientèle probable",
  "problems": ["problème visible 1", "problème visible 2"],
  "consequences": ["conséquence commerciale possible 1"],
  "priority_improvements": ["amélioration prioritaire 1", "amélioration 2"],
  "recommended_service": "nom du service le plus pertinent",
  "secondary_service": "service secondaire éventuel ou null",
  "free_audit_idea": "idée d'audit gratuit personnalisé",
  "prospecting_angle": "angle de prospection en une phrase",
  "confidence": "faible|moyen|élevé",
  "sources_used": ["données fournies utilisées"]
}}"""
    return await _run(ANALYSIS_SYSTEM, prompt, f"analysis-{company.get('id','x')}")


SCORING_SYSTEM = (
    "Tu es un expert en qualification de prospects B2B. Tu attribues un score sur 100 selon une grille stricte. "
    "Tu réponds UNIQUEMENT en JSON valide, en français."
)


async def score_company(company: dict, analysis: dict) -> dict:
    prompt = f"""Évalue ce prospect selon la grille de scoring (total 100 points).

Grille:
- problème digital clairement visible: 20
- problème directement lié aux services proposés: 20
- entreprise active: 10
- décideur identifiable: 15
- email professionnel disponible: 10
- capacité financière potentielle: 10
- besoin probablement urgent: 10
- possibilité de personnalisation forte: 5

Entreprise: {company.get('name')} | Secteur: {company.get('sector')} | Site: {company.get('website') or 'aucun'} | Email: {company.get('generic_email') or 'aucun'}
Analyse: problèmes={analysis.get('problems')}, service={analysis.get('recommended_service')}, confiance={analysis.get('confidence')}

Réponds STRICTEMENT avec ce JSON:
{{
  "score": <entier 0-100>,
  "breakdown": {{
    "probleme_visible": <0-20>,
    "probleme_lie_services": <0-20>,
    "entreprise_active": <0-10>,
    "decideur_identifiable": <0-15>,
    "email_pro": <0-10>,
    "capacite_financiere": <0-10>,
    "besoin_urgent": <0-10>,
    "personnalisation": <0-5>
  }},
  "explanation": "explication des points attribués",
  "missing_elements": ["élément manquant 1"],
  "recommendation": "Priorité élevée|Bon prospect|À examiner|Faible priorité",
  "confidence": "faible|moyen|élevé"
}}"""
    return await _run(SCORING_SYSTEM, prompt, f"score-{company.get('id','x')}")


EMAIL_SYSTEM = (
    "Tu es Jean-Philippe Koffi, chef de projet marketing digital spécialisé en acquisition client. "
    "Tu rédiges des emails de prospection B2B professionnels, humains, courts et personnalisés, en français. "
    "Interdits: jargon inutile, exagération, fausse promesse, information inventée, ton agressif, style spam. "
    "Toute observation personnalisée doit provenir des données fournies. Réponds UNIQUEMENT en JSON valide."
)


async def generate_email(company: dict, contact: dict, analysis: dict, tone: str = "consultatif") -> dict:
    problem = (analysis.get("problems") or ["présence digitale à optimiser"])[0]
    consequence = (analysis.get("consequences") or ["difficulté à convertir les visiteurs en demandes"])[0]
    service = analysis.get("recommended_service") or "optimisation de l'acquisition digitale"
    prompt = f"""Rédige un email de premier contact (ton: {tone}).

Contact: {contact.get('first_name')} {contact.get('last_name')} - {contact.get('role') or 'Dirigeant'}
Entreprise: {company.get('name')} ({company.get('sector')}, {company.get('city')})
Observation vérifiée: {problem}
Conséquence possible: {consequence}
Service recommandé: {service}
Offre: Audit gratuit du système d'acquisition digitale

Structure: objet court, salutation, observation personnalisée, conséquence, courte présentation, proposition d'audit gratuit, question simple, signature "Jean-Philippe Koffi".
Ajoute une phrase de désinscription discrète.

Réponds STRICTEMENT avec ce JSON:
{{
  "subject": "objet de l'email",
  "body": "corps complet de l'email avec sauts de ligne \\n",
  "tone": "{tone}"
}}"""
    return await _run(EMAIL_SYSTEM, prompt, f"email-{company.get('id','x')}")


async def generate_variants(company: dict, contact: dict, analysis: dict) -> list:
    tones = ["directe", "consultative", "chaleureuse et professionnelle"]
    variants = []
    for t in tones:
        try:
            variants.append(await generate_email(company, contact, analysis, t))
        except Exception:
            continue
    return variants


async def generate_followup(company: dict, contact: dict, level: int, previous_subject: str = "") -> dict:
    labels = {1: "Relance 1 (J+3), courte et bienveillante",
              2: "Relance 2 (J+7), dernière relance de valeur",
              3: "Relance finale (J+14), clôture polie du suivi"}
    prompt = f"""Rédige une {labels.get(level, 'relance')} pour {contact.get('first_name')} de {company.get('name')}.
Sujet initial: {previous_subject}. Reste très court, professionnel, sans insistance.
Réponds STRICTEMENT avec ce JSON: {{"subject": "...", "body": "... \\n ...", "level": {level}}}"""
    return await _run(EMAIL_SYSTEM, prompt, f"followup-{company.get('id','x')}-{level}")


REPLY_SYSTEM = (
    "Tu es un assistant commercial qui analyse les réponses reçues à des emails de prospection B2B. "
    "Tu réponds UNIQUEMENT en JSON valide, en français."
)


async def classify_reply(reply_text: str, company: dict) -> dict:
    prompt = f"""Analyse cette réponse reçue de {company.get('name')}:

\"\"\"{reply_text}\"\"\"

Catégories possibles: Intéressé, Demande d'informations, Souhaite un rendez-vous, À rappeler plus tard, Pas maintenant, Déjà accompagné, Refus, Ne plus contacter, Mauvais interlocuteur, Transfert vers une autre personne, Absence du bureau, Adresse invalide, Réponse automatique, Réponse ambiguë, Autre.

Réponds STRICTEMENT avec ce JSON:
{{
  "category": "une des catégories",
  "summary": "résumé de la réponse",
  "sentiment": "positif|neutre|négatif",
  "intent": "intention détectée",
  "interest_level": "élevé|moyen|faible|nul",
  "next_action": "prochaine action recommandée",
  "recall_date": "YYYY-MM-DD ou null",
  "suggested_reply": "proposition de réponse",
  "needs_human_validation": true
}}"""
    return await _run(REPLY_SYSTEM, prompt, f"reply-{company.get('id','x')}")
