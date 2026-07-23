# PRD — PROSPECTIA

## Problème / Vision
Application web full-stack de prospection commerciale B2B assistée par IA, en français, pour Jean-Philippe Koffi (chef de projet marketing digital). Fonctionne comme une machine commerciale semi-automatisée : trouver/importer des entreprises → analyser → qualifier → générer un email → validation humaine → envoyer (simulation) → relancer → analyser les réponses → opportunités → client.

## Architecture technique
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + Recharts + sonner. Sidebar fixe (desktop) + nav mobile. Fonts Manrope/IBM Plex Sans. Thème clair, bleu nuit.
- Backend: FastAPI + Motor (MongoDB async). Toutes routes préfixées /api. Auth JWT Bearer (localStorage).
- IA: OpenAI GPT-5.5 via emergentintegrations (EMERGENT_LLM_KEY), sorties JSON (ai_service.py).
- Email: MODE SIMULATION (aucun envoi réel).

## Personas / rôles
- Admin (seul rôle actif) : Jean-Philippe Koffi. Structure évolutive prévue (commercial, analyste, validateur, lecture seule).

## Collections MongoDB
users, companies, contacts, campaigns, templates, emails, followups, replies, opportunities, services, exclusions, activity_logs, errors, settings.

## Implémenté (2026-07 — MVP Phase 1)
- Authentification JWT (login/logout/me, seed admin idempotent, mots de passe bcrypt).
- Tableau de bord : 16+ KPIs, entonnoir de conversion, répartition par statut/secteur, bloc "Actions prioritaires aujourd'hui".
- Entreprises : CRUD, recherche, filtres (statut/secteur), tri, sélection multiple, changement de statut en masse, détection de doublons multi-champs, import/export CSV.
- Contacts : CRUD lié aux entreprises, recherche.
- Analyse digitale IA + scoring /100 avec détail, explication, recommandation ; modification manuelle du score.
- Génération d'emails IA (3 tons) + file de validation (valider/envoyer/programmer/refuser). Aucun 1er email envoyé sans validation.
- Envoi simulation → crée automatiquement 3 relances (J+3, J+7, J+14).
- Moteur de relances : génération IA, envoi simulation, arrêt auto si réponse/refus/client.
- Réponses : classification IA (15 catégories) → stop relances, création opportunité, ajout auto exclusion si "Ne plus contacter".
- Opportunités : pipeline Kanban.
- Campagnes, Modèles de messages (préchargés), Services (17 préchargés), Liste d'exclusion (vérifiée avant envoi).
- Journal d'activité complet (auto vs manuel), Centre d'erreurs.
- Paramètres : Profil / Prospection / IA / Email / Conformité.
- Données de démo (10 entreprises, contacts, 3 campagnes, emails, réponses, opportunités) créables/supprimables en 1 clic.

## Backlog (Phase 2)
- P1: Envoi réel Gmail/SMTP/Brevo (remplacer simulation), réception & rattachement automatique des réponses.
- P1: Rendez-vous (section + assistant de préparation IA, Google Calendar/Calendly).
- P2: Sources de prospects (Google Maps, annuaires, webhooks, Make/n8n), enrichissement, vérification d'email.
- P2: Statistiques avancées (perf par campagne/modèle/objet, délais moyens), niveaux d'automatisation configurables poussés.
- P2: Multi-utilisateur + rôles, récupération de mot de passe, brute-force protection.

## Identifiants
Admin: jp.koffi@prospectia.app / Prospectia2026! (voir /app/memory/test_credentials.md)

## Prochaines tâches
1. Phase 2 : intégration email réelle + réception réponses.
2. Section Rendez-vous + assistant IA.
