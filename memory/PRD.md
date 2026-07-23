# PROSPECTIA — PRD & Suivi

## Problème / Vision
Copilote commercial IA (prospection B2B) pour Jean-Philippe Koffi. Full-stack React + FastAPI + MongoDB, en français. Doit devenir un CRM **explicable, traçable, vérifiable** — pas un simple CRM avec des textes IA.

## Architecture
- Backend FastAPI (`/app/backend/server.py`), IA (`ai_service.py`, GPT-5.5 via Emergent LLM key), import (`import_service.py`), seed (`seed_data.py`).
- Auth JWT Bearer (localStorage). Admin: jp.koffi@prospectia.app / Prospectia2026!
- Frontend React, sidebar fixe, 15 sections, mode simulation email.

## Implémenté (à jour)
- **Phase 1 MVP (fait)** : Auth, Dashboard (KPIs + entonnoir + graphiques + actions prioritaires), Entreprises (CRUD, filtres, recherche, tri, sélection multiple, statut en masse, export CSV), Contacts, Analyse IA + Scoring /100 avec détail, Génération d'email (3 tons) + file de validation + envoi simulation + relances auto (J+3/7/14), Réponses (classification IA + arrêt relances + création opportunité + exclusion auto), Opportunités (Kanban), Services (17 préchargés), Modèles, Exclusions, Journal d'activité, Centre d'erreurs, Paramètres (5 onglets), données de démo.
- **Correctif login** (trim email/mdp) — vérifié testing_agent iteration_2.
- **BUG BLOQUANT import CORRIGÉ** (2026) : nouveau flux 2 étapes aperçu→confirmation. Détection encodage (utf-8-sig/utf-8/cp1252/latin-1) + séparateur (virgule/point-virgule/tab/pipe via csv.Sniffer), mappage par synonymes éditable, normalisation (email/url/tel), doublons internes + base, stratégies (ignorer/compléter/créer), rapport + téléchargement lignes rejetées, support .xlsx. Vérifié testing_agent iteration_3 (9/9 backend, 100% UI).
- **Correctif logo** : brand PROSPECTIA non-sélectionnable (Layout.jsx). Vérifié iteration_3.
- **Résilience login** : messages distincts (401 vs service indisponible) + retry auto 1x sur erreur transitoire (reload backend). Vérifié iterations 4-5.
- **Données démo simplifiées + analyse prudente** (2026) : badge « Démo » sur fiche, démo exclue des statistiques (dashboard demo_count + bandeau), bouton suppression. Score « non calculé » (score=None) avant analyse (plus de 0/100 trompeur). Analyse IA restructurée en 3 blocs (A Données disponibles / B Manquantes ou non vérifiées / C Hypothèses), vocabulaire prudent (non renseigné/non vérifié/non confirmé), service = « potentiel à explorer » conditionnel, « Analyse insuffisante » si dossier trop pauvre (score reste None), traçabilité score (données utilisées/absentes, règles, limites, recherche extérieure=non effectuée). Vérifié testing_agent iteration_6 (6/6 backend, 5/5 UI).

## Backlog prioritaire (demande de restructuration « copilote explicable »)
Ordre imposé par l'utilisateur (section 31) — à traiter par étapes, test après chaque :
- P0 : Schéma « information vérifiable » (source, preuve, statut vérification, confiance par donnée, historique) — modèle `collected_data`.
- P0 : Indice de complétude + score de confiance global (distinct du score commercial).
- P0 : Score commercial explicable (critères/poids/points/source/confiance), « score en attente » si non vérifié, modif manuelle + raison.
- P0 : Explication de tout changement de score (ancien→nouveau, cause, impact) + stabilité (JSON déterministe, T° faible).
- P1 : Séparer Problème / Offre d'entrée / Service final (3 champs). Emails prudents (formulations « je n'ai pas identifié… »). Panneau « Pourquoi cet email ».
- P1 : Nuance tunnel de vente & réseaux sociaux (statuts « non détecté publiquement » vs « absent confirmé »). Questions d'audit auto. Confirmation prospect.
- P1 : Chronologie métier + historique complet par fiche. Validation humaine par donnée.
- P2 : Test complet Agence Novéa, agent de collecte externe (scraping autorisé pages publiques), enrichissement.
- Reporté Phase 2 : Kanban avancé, rendez-vous, stats avancées, intégrations (Gmail/SMTP/Brevo, Make/n8n), multi-utilisateur.

## Prochaines actions
Démarrer le schéma « information vérifiable » (sources/preuves/confiance/historique) — fondation de l'explicabilité, avant scoring explicable et emails prudents.
