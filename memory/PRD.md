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

- **Données démo simplifiées + analyse prudente** (2026) : badge « Démo » sur fiche, toggle inclure/exclure la démo des stats du tableau de bord (demo_count + bandeau + toggle-demo-btn), bouton suppression. Score « non calculé » (score=None) avant analyse. Analyse IA en 3 blocs (A/B/C), vocabulaire prudent, service « potentiel à explorer » conditionnel, « Analyse insuffisante » (score None), traçabilité score. Vérifié iterations 6-7.
- **Discovery Agent V1** (2026) : agent de recherche d'entreprises RÉELLES via API Recherche d'Entreprises (Sirene INSEE, HTTP sortant confirmé). Workflow 4 étapes : interpret (mapping secteur→NAF pointé, région IDF→8 départements, corrigeable) → run réel/simulation → vérification (identité SIREN, activité NAF exact, statut actif) → scoring FIGÉ (3 tables : confiance identité, correspondance mission, complétude, /100 chacune, détail ligne par ligne). Filtre géographique STRICT côté client (l'API departement n'est qu'un tri). Site/tél/email « non disponible » (jamais inventés). Validation humaine 100% → création CRM avec dédup SIREN. RGPD : exclusion des SIREN en opposition, champ opposition_rgpd, source+date de collecte stockées. Mode simulation marqué. Cible adjacente (NAF voisins). Vérifié testing_agent iteration_8 (8/8 UI) + fix geo vérifié.

## Correction scoring Discovery — 2 règles (2026-07-27)
- **Critère Taille (correspondance mission)** : `interpret_mission` extrait une vraie fourchette de la mission (« 1 à 20 / de X à Y / entre X et Y / moins de N / plus de N salariés »). `_build_candidate(size_range)` compare la tranche d'effectif Sirene à la fourchette : 15/15 si chevauchement, 0/15 + note « Tranche Sirene X–Y hors fourchette » sinon. Sans fourchette → critère `neutral` renommé « Tranche d'effectif renseignée », exclu du dénominateur (fin du 15/15 trompeur).
- **Critère Cohérence entre sources (confiance)** : suppression du bonus automatique 5/5. État `neutral`, note « Non vérifiable — une seule source active (Sirene) », exclu du dénominateur → confiance affichée /95.
- Nouvelle structure : chaque critère = `{label, pts, max, status(ok/ko/neutral), note}` ; `_score()` renvoie `total` + `max_total` (exclut neutres). `Discovery.jsx` affiche `total/max_total`, couleurs en %, notes par critère, fourchette dans la carte d'interprétation (interp-size-range).
- Testé : iteration_9.json — backend 8/8, frontend 2/2, aucun bug.

## Purge RGPD 90j + tests variés Discovery (2026-07-27)
- **Purge RGPD (P1 fait)** : `purge_stale_discovery()` supprime les fiches Discovery non validées après 90 jours. Mission > 90j sans aucun candidat validé → supprimée ; mission avec candidats validés → les fiches non validées sont retirées, statut « Purgé (RGPD 90j) ». Tâche `asyncio` quotidienne lancée au startup + endpoint manuel `POST /api/discovery/purge` (admin). Testé e2e (curl) : 1 supprimée, 1 nettoyée, fiche récente préservée. Note RGPD affichée dans l'historique frontend.
- **Tests variés (P1 fait)** : interprétation validée sur avocats/communication/logiciels/conseil/architectes/RH ; tailles (1-20, 10-49, moins de 50, plus de 200, entre X et Y) ; indisponibilité Sirene → 0 candidat, `source_unavailable=True`, aucune donnée inventée. Run réel Sirene validé (3 cabinets Paris réels, filtre taille effectif).
- **Couverture régionale élargie** : ajout `MAJOR_CITIES` (Lyon, Marseille, Bordeaux, Lille, Toulouse, Nantes, Nice, etc.) + détection « département XX » / « (XX) ». Auparavant seule l'Île-de-France était géo-filtrée.

## Ordre Experts-Comptables + clarif Google Places (2026-07-27)
- **Ordre (option d retenue)** : non intégré. Affichage « Confirmation Ordre des Experts-Comptables : Non disponible » ajouté (a) sur chaque fiche entreprise via carte « Vérifications externes » (CompanyDetail.jsx, data-testid external-verifications-card / verif-ordre) et (b) dans la traçabilité des candidats Discovery (backend verification.ordre_experts_comptables + Discovery.jsx). Motif documenté : robots.txt du CNOEC interdit /recherche*, contenu sous droit d'auteur, RGPD.
- **Google Places (recherche, en attente décision)** : modèle par SKU depuis mars 2025 — Essentials 10 000/mois, Pro 5 000/mois, Enterprise 1 000/mois (gratuits). `websiteUri` + `nationalPhoneNumber` = SKU Enterprise → **~1 000 fiches complètes (site+téléphone) gratuites/mois**. Compte de facturation + carte obligatoire même en gratuit ; quota dur recommandé (~900) pour garantir 0 €. Rien intégré.

## Intégration Google Places (New) — enrichissement source secondaire (2026-07-27)
- **Objectif** : enrichir les fiches Discovery avec site web + téléphone public, activant réellement les critères site/téléphone et la cohérence multi-sources (Sirene ↔ Google).
- **Backend** : `places_service.lookup_company_place()` (Text Search New + repli Place Details, field mask minimal `websiteUri,nationalPhoneNumber` = SKU Enterprise, langue fr / région FR). `discovery_service.apply_places_enrichment()` recalcule confidence/completeness et la cohérence (ok/ko/neutral selon nom+CP). Endpoint `POST /api/discovery/enrich` {mission_id, siren}.
- **Maîtrise du coût** : quota dur applicatif mensuel `GOOGLE_PLACES_MONTHLY_CAP=900` (collection `api_usage`), **cache** Mongo (`places_cache`) par nom+adresse normalisés (ré-enrichissement gratuit), endpoint `GET /api/places/usage`. Clé en env `GOOGLE_MAPS_API_KEY` (jamais côté frontend).
- **Frontend** (Discovery.jsx) : bouton « Enrichir (Google Places) » / « Ré-enrichir », badge Enrichi, affichage site/téléphone, toast avec quota restant, cohérence + source secondaire dans la traçabilité.
- **Honnêteté** : email reste 0 (Places ne fournit pas d'email) ; aucune donnée inventée ; si aucune correspondance Google → cohérence neutre « non vérifiable ».
- **Testé** : run réel Sirene + enrich réel (site/tél récupérés, quota 1/900), chemin cache (0 conso, cohérence ok), UI e2e par capture. Contradiction correctement détectée quand noms/CP divergent.
- ⚠️ Recommandé côté Google Cloud : poser aussi un **quota dur par méthode** (le budget d'alerte 3 € n'arrête pas l'usage). Le cap applicatif garantit déjà ≤ 900/mois.

## Extraction email public depuis le site officiel (2026-07-27)
- **Enchaîné automatiquement** à l'enrichissement Google Places (option a) : une fois le site officiel confirmé, `email_scraper.extract_public_email()` teste quelques pages contact probables (/contact, /nous-contacter, /mentions-legales… + accueil) et extrait un email réellement affiché (liens mailto + texte).
- **Zéro invention** : jamais de `contact@domaine` déduit ; si rien → « Email non trouvé sur le site officiel ». **robots.txt respecté** (urllib.robotparser) → si accès interdit : « Extraction impossible — accès automatisé restreint par le site (robots.txt) ». Priorité aux boîtes génériques (contact@, info@, accueil@…), filtrage des faux positifs (assets, placeholders).
- **Traçabilité** : URL exacte de la page + date de collecte + mode réel, stockées dans `email_source` de la fiche.
- **Score** : critère Email (complétude 15) = points si trouvé avec preuve, 0 sinon ; critère confiance « téléphone OU email public » = 5 si tél OU email. Jamais de bonus par défaut.
- **Coût : 0 €** (simple fetch HTTP, aucun service tiers). Résultat mis en cache dans `places_cache.email_info`.
- **Testé** : email trouvé (SADEC → accueil.paris@sadec-akelys.fr, complétude 100/100), non trouvé, robots bloqué (Google/Facebook), site absent — tous honnêtes. UI e2e par capture.

## Analyse IA ancrée sur le contenu réel du site officiel (2026-07-28)
- **Avant le scoring**, l'endpoint `/api/companies/{id}/analyze` récupère automatiquement le texte de la page d'accueil + page contact du site officiel (`email_scraper.fetch_site_text`, accueil + /contact + variantes, robots.txt respecté, ≤3 pages / 6000 caractères, coût 0).
- Ce texte est passé à `ai_service.analyze_company(company, site_context)` et `score_company(..., site_context)` comme **source réelle vérifiée** : les faits `data_available` sont désormais sourcés « (source : site officiel) » vs « (source : dossier) ». Fiabilité passe de « faible » à « modérée » et `external_search_done=True` quand le site est lu.
- **Fallback** : si le site est inaccessible / bloqué par robots.txt, l'analyse continue normalement avec les seules données du dossier (fiabilité faible, `used=False`, note honnête).
- **Traçabilité** stockée dans `company.analysis_site_context` {used, pages_used, chars, robots_blocked, note, collected_at} et affichée dans la carte « Vérifications externes » (fiche entreprise).
- **Testé** (curl e2e) : site réel (SADEC → 2 pages lues, faits sourcés du site, score 61, fiabilité modérée) ; site invalide (fallback dossier, score 41, fiabilité faible) ; fetch unitaire + capture UI.

## Prochaines actions
Démarrer le schéma « information vérifiable »
