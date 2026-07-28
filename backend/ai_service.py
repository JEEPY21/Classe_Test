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
    "Tu es un expert en acquisition digitale B2B, PRUDENT et RIGOUREUX. Tu réponds UNIQUEMENT en JSON valide, en français. "
    "RÈGLES ABSOLUES : "
    "1) Tu n'inventes JAMAIS un fait ni une absence de fait. "
    "2) Tu distingues strictement : donnée non renseignée dans le dossier, donnée non vérifiée, recherche sans résultat, absence confirmée. "
    "3) La seule source extérieure autorisée est le CONTENU DU SITE OFFICIEL lorsqu'il est fourni ci-dessous (source vérifiée) ; "
    "en son absence, tu ne peux te baser que sur les données du dossier. Aucune autre supposition extérieure. "
    "4) N'écris JAMAIS des formulations catégoriques comme « aucun site », « pas de LinkedIn », « aucun tunnel ». "
    "Écris plutôt « site non renseigné dans le dossier / non vérifié », « présence LinkedIn non confirmée », « tunnel public non vérifié ». "
    "5) Sépare toujours les FAITS (données présentes) des HYPOTHÈSES (interprétations conditionnelles). "
    "6) Une recommandation dépendant d'une donnée non vérifiée est un « service potentiel à explorer », pas un « service recommandé »."
)


async def analyze_company(company: dict, site_context: dict = None) -> dict:
    present = {k: v for k, v in {
        "Site internet": company.get("website"), "Email générique": company.get("generic_email"),
        "Téléphone": company.get("phone"), "LinkedIn": company.get("linkedin"),
        "Facebook": company.get("facebook"), "Instagram": company.get("instagram"),
        "Description": company.get("description"), "Adresse": company.get("address"),
    }.items() if v}
    site_text = (site_context or {}).get("text") or ""
    if site_text:
        pages = ", ".join((site_context or {}).get("pages_used") or [])
        site_block = (
            "\n\n=== CONTENU RÉEL DU SITE OFFICIEL (source vérifiée — extraite automatiquement) ===\n"
            f"Pages lues : {pages}\n"
            "Ce texte provient réellement du site officiel de l'entreprise. Tu peux t'en servir comme FAITS "
            "sur ce que l'entreprise dit d'elle-même (activité, services, cible, ton, coordonnées), en précisant "
            "que la source est le site officiel. Ne déduis rien au-delà de ce qui est écrit.\n"
            f"\"\"\"\n{site_text}\n\"\"\"\n"
        )
        reliability = "Fiabilité modérée — analyse appuyée sur le contenu réel du site officiel (source citée)."
    else:
        note = (site_context or {}).get("note")
        site_block = ("\n\nContenu du site officiel : " + (note or "non disponible") +
                      ". Aucune autre vérification extérieure n'a été effectuée.\n") if company.get("website") else \
                     "\n\nAucun site officiel renseigné : aucune vérification extérieure possible.\n"
        reliability = "Fiabilité faible — aucune vérification extérieure effectuée."

    prompt = f"""Analyse ce dossier prospect à partir des données du dossier ET, si présent, du contenu réel du site officiel ci-dessous.

Entreprise : {company.get('name')}
Secteur : {company.get('sector') or 'non renseigné'}
Ville : {company.get('city') or 'non renseignée'}
Données présentes dans le dossier : {present or 'très peu de données'}{site_block}
Détermine d'abord si les données sont SUFFISANTES pour un diagnostic fiable (au moins nom + secteur + une donnée de présence digitale OU du contenu réel du site). Sinon, mets "insufficient": true.

Réponds STRICTEMENT avec ce JSON :
{{
  "summary": "résumé prudent de l'activité basé sur le dossier et le site officiel s'il est disponible (2-3 phrases, sans rien inventer)",
  "data_available": ["fait réellement présent (dossier ou site officiel, précise la source) 1", "fait 2"],
  "missing_or_unverified": ["donnée absente ou non vérifiée à rechercher/confirmer 1", "élément 2"],
  "hypotheses": ["hypothèse commerciale prudente et conditionnelle 1", "hypothèse 2"],
  "questions_to_ask": ["question à poser au prospect pour lever une incertitude 1", "question 2"],
  "potential_service": "service potentiel à explorer (nom)",
  "service_condition": "condition sous laquelle ce service est pertinent",
  "entry_offer": "Audit gratuit du système d'acquisition digitale",
  "prospecting_angle": "angle de prospection prudent en une phrase, idéalement ancré sur ce que dit le site officiel",
  "confidence": "faible|moyen|élevé",
  "reliability_note": "{reliability}",
  "insufficient": false
}}"""
    return await _run(ANALYSIS_SYSTEM, prompt, f"analysis-{company.get('id','x')}")


SCORING_SYSTEM = (
    "Tu es un expert en qualification de prospects B2B. Tu produis un SCORE PROVISOIRE basé uniquement sur les données du dossier "
    "(aucune vérification extérieure). Tu es prudent et déterministe. Tu réponds UNIQUEMENT en JSON valide, en français."
)


async def score_company(company: dict, analysis: dict, site_context: dict = None) -> dict:
    site_text = (site_context or {}).get("text") or ""
    if site_text:
        pages = ", ".join((site_context or {}).get("pages_used") or [])
        source_block = (f"\nContenu réel du site officiel LU (source vérifiée, pages : {pages}) — extrait :\n"
                        f"\"\"\"\n{site_text[:2500]}\n\"\"\"\n")
        reliability_line = "Fiabilité modérée — score appuyé sur le contenu réel du site officiel (source citée)."
        ext_done = True
        header = "Une lecture du site officiel a été effectuée (source réelle citée) : la fiabilité est modérée."
    else:
        source_block = ""
        reliability_line = "Fiabilité faible — aucune vérification extérieure effectuée."
        ext_done = False
        header = "Aucune recherche extérieure n'a été effectuée : la fiabilité est donc faible."

    prompt = f"""Calcule un SCORE COMMERCIAL PROVISOIRE (sur 100) pour ce dossier, basé sur les données présentes et le contenu réel du site officiel s'il est fourni.
{header}

Grille (attribue les points uniquement si la donnée est réellement présente/déductible du dossier ou du site officiel) :
- problème digital potentiel visible dans le dossier/site : 20
- adéquation potentielle avec les services : 20
- entreprise active (indices présents) : 10
- décideur identifiable : 15
- email professionnel présent : 10
- capacité financière potentielle : 10
- besoin probablement urgent : 10
- possibilité de personnalisation : 5

Entreprise : {company.get('name')} | Secteur : {company.get('sector') or 'non renseigné'} | Site : {company.get('website') or 'non renseigné'} | Email : {company.get('generic_email') or 'non renseigné'}
Faits du dossier : {analysis.get('data_available')}
Éléments manquants/non vérifiés : {analysis.get('missing_or_unverified')}{source_block}
Réponds STRICTEMENT avec ce JSON :
{{
  "score": <entier 0-100>,
  "score_label": "Score provisoire basé sur les données du dossier{' et le site officiel' if site_text else ''}",
  "breakdown": {{
    "probleme_visible": <0-20>, "adequation_services": <0-20>, "entreprise_active": <0-10>,
    "decideur_identifiable": <0-15>, "email_pro": <0-10>, "capacite_financiere": <0-10>,
    "besoin_urgent": <0-10>, "personnalisation": <0-5>
  }},
  "data_used": ["donnée utilisée pour le calcul (précise si dossier ou site officiel) 1", "donnée 2"],
  "data_absent": ["donnée manquante qui limite le score 1", "donnée 2"],
  "rules_applied": "résumé des règles appliquées",
  "limits": "limites du calcul",
  "external_search_done": {str(ext_done).lower()},
  "explanation": "explication des points attribués",
  "recommendation": "Priorité élevée|Bon prospect|À examiner|Faible priorité",
  "reliability": "{reliability_line}",
  "confidence": "faible|moyen|élevé"
}}"""
    return await _run(SCORING_SYSTEM, prompt, f"score-{company.get('id','x')}")


EMAIL_SYSTEM = (
    "Tu es Jean-Philippe Koffi, chef de projet marketing digital. Tu rédiges des emails de prospection B2B professionnels, "
    "humains, courts et personnalisés, en français. PRUDENCE ABSOLUE : n'affirme jamais l'absence d'un outil non vérifié. "
    "Utilise des formulations comme « À première vue… », « Lors de ma consultation… », « Je n'ai pas identifié… », "
    "« Ce point mériterait d'être confirmé avec vous… ». Interdits : inventer, présenter une hypothèse comme un fait, "
    "citer un champ interne du CRM, affirmer catégoriquement l'absence d'un outil, ton agressif, style spam. "
    "Réponds UNIQUEMENT en JSON valide."
)


async def generate_email(company: dict, contact: dict, analysis: dict, tone: str = "consultatif") -> dict:
    observation = (analysis.get("hypotheses") or analysis.get("missing_or_unverified") or ["votre acquisition digitale pourrait être optimisée"])[0]
    service = analysis.get("potential_service") or "l'optimisation de votre acquisition digitale"
    prompt = f"""Rédige un email de premier contact (ton: {tone}), PRUDENT et personnalisé.

Contact: {contact.get('first_name')} {contact.get('last_name')} - {contact.get('role') or 'Dirigeant'}
Entreprise: {company.get('name')} ({company.get('sector') or 'secteur non renseigné'}, {company.get('city') or ''})
Observation prudente (à formuler sans affirmer de certitude): {observation}
Service potentiel à explorer: {service}
Offre d'entrée: Audit gratuit du système d'acquisition digitale

Structure: objet court ; salutation ; observation PRUDENTE (« À première vue… », « Je n'ai pas identifié… ») ;
conséquence possible au conditionnel ; courte présentation ; proposition d'audit gratuit ; question simple ; signature « Jean-Philippe Koffi ».
Ajoute une phrase de désinscription discrète. N'affirme JAMAIS catégoriquement l'absence d'un outil.

Réponds STRICTEMENT avec ce JSON:
{{
  "subject": "objet de l'email",
  "body": "corps complet avec sauts de ligne \\n",
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
