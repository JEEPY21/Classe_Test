# PRD — Matchipy

## Problème / Vision
Application web (FR) générant des CV et lettres de motivation optimisés par IA à partir
d'un CV existant + une offre d'emploi. Usage initial personnel, architecture propre et
multi-utilisateurs-ready pour commercialisation ultérieure.

## Règles non-négociables (implémentées)
1. Zéro hallucination — le LLM ne s'appuie que sur le CV structuré validé.
2. Traçabilité — chaque mot-clé porte sa source (offre / cv / confirmation_utilisateur).
3. Validation humaine avant export — écran relecture avant/après obligatoire.
4. Séparation contenu (JSON LLM) / mise en forme (templates HTML/CSS fixes).

## Architecture
- Backend: FastAPI modulaire (db.py, models.py, auth.py, llm_service.py, extraction.py,
  ats_service.py, export_service.py, routers.py, server.py). MongoDB (motor). Toutes les
  entités portent user_id (multi-user ready).
- Auth: JWT (bcrypt + PyJWT), cookies httpOnly, brute-force lockout, seed admin.
- LLM: Claude claude-sonnet-4-6 via emergentintegrations (EMERGENT_LLM_KEY).
- Frontend: React + Tailwind + Shadcn, design "Swiss & High-Contrast", workflow 5 blocs
  avec stepper vertical, AuthContext + ProtectedRoute.

## Personas
- Chercheur d'emploi (utilisateur unique aujourd'hui), futurs comptes multiples.

## Implémenté (2026-08-16) — Blocs 1-5 validés e2e (tests 100%)
- BLOC 1: upload PDF/DOCX -> extraction (pdfplumber/python-docx) -> structuration Claude ->
  formulaire JSON éditable ; PUT update ; DELETE RGPD.
- BLOC 2: analyse d'offre (poste, hard/soft skills, mots-clés, détection langue fr/en/es/de).
- BLOC 3: score par sous-critères + explication ; écran confirmation compétences manquantes
  (checklist, jamais auto) ; diffs avant/après ligne par ligne (accept/reject) ; lettre de
  motivation ; traçabilité des mots-clés par source.
- BLOC 4: contrôle ATS — Affinda (câblé) + repli lisibilité interne (ré-extraction du PDF,
  champ par champ). Rapport détaillé lisible.
- BLOC 5: 3 templates ATS-friendly (classic/modern/compact), relecture avant/après
  obligatoire, export PDF (texte natif, xhtml2pdf) + DOCX (python-docx).

## État des intégrations
- Génération CV : **Claude Sonnet 4.6** (`claude-sonnet-4-6`) — score, reformulations, skills_section.
- Génération lettre : **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) — style humain (sans tiret long, sans puces, sans clichés). Appels CV/lettre lancés en parallèle (asyncio.gather).
- Extraction CV : nettoyage du texte avant LLM (espaces multiples, sauts de ligne, en-têtes/pieds de page répétés).
- Contrôle ATS (Bloc 4) : **aucun appel LLM** — Affinda (clé actuelle 401) + repli lisibilité interne déterministe.
- Génération asynchrone + polling (plus de 502), refresh token auto (TTL 8h).

## Backlog priorisé
- P1: BLOC 3bis — suivi manuel des candidatures (dashboard statuts, CV/lettre attachés).
- P1: éditeur de lettre de motivation modifiable + export lettre (PDF/DOCX).
- P2: régénération ciblée intégrant les compétences confirmées dans les puces.
- P2: reset password (endpoints prévus dans le playbook), persistance workflow après refresh.
- P2: multi-CV, versions, historique des exports.

## Prochaines tâches
1. Fournir une clé Affinda valide (Settings -> API tokens) pour BLOC 4 pro.
2. Décider de l'activation du BLOC 3bis (suivi de candidatures).
