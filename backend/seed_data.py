"""Données de démonstration et catalogues par défaut pour PROSPECTIA."""
from datetime import datetime, timezone, timedelta
import uuid

now = lambda: datetime.now(timezone.utc).isoformat()

DEFAULT_SERVICES = [
    {"name": "Audit du système d'acquisition digitale", "problems_solved": "Manque de visibilité sur les freins à la conversion", "price_range": "Gratuit", "active": True},
    {"name": "Création de site internet", "problems_solved": "Absence de site ou site obsolète", "price_range": "2 000 - 6 000 €", "active": True},
    {"name": "Refonte de site", "problems_solved": "Site peu professionnel ou non responsive", "price_range": "1 500 - 5 000 €", "active": True},
    {"name": "Maintenance de site", "problems_solved": "Site non maintenu, lent ou vulnérable", "price_range": "80 - 300 €/mois", "active": True},
    {"name": "Landing page", "problems_solved": "Absence de page de conversion dédiée", "price_range": "800 - 2 500 €", "active": True},
    {"name": "Tunnel de conversion", "problems_solved": "Visiteurs qui ne deviennent pas des contacts", "price_range": "2 000 - 8 000 €", "active": True},
    {"name": "Optimisation du parcours client", "problems_solved": "Taux de conversion faible", "price_range": "1 500 - 4 000 €", "active": True},
    {"name": "CRM", "problems_solved": "Suivi des prospects désorganisé", "price_range": "1 000 - 5 000 €", "active": True},
    {"name": "Automatisation des relances", "problems_solved": "Relances manuelles oubliées", "price_range": "800 - 3 000 €", "active": True},
    {"name": "Marketing automation", "problems_solved": "Nurturing inexistant", "price_range": "1 500 - 6 000 €", "active": True},
    {"name": "SEO", "problems_solved": "Faible visibilité sur Google", "price_range": "600 - 2 000 €/mois", "active": True},
    {"name": "SEA (Google Ads)", "problems_solved": "Pas de trafic payant qualifié", "price_range": "500 - 2 000 €/mois", "active": True},
    {"name": "Meta Ads", "problems_solved": "Absence sur les réseaux sociaux payants", "price_range": "500 - 2 000 €/mois", "active": True},
    {"name": "Gestion des réseaux sociaux", "problems_solved": "Présence sociale incohérente", "price_range": "600 - 1 800 €/mois", "active": True},
    {"name": "Création de contenus", "problems_solved": "Manque de contenus de confiance", "price_range": "400 - 1 500 €/mois", "active": True},
    {"name": "Identité visuelle", "problems_solved": "Image de marque peu professionnelle", "price_range": "800 - 3 000 €", "active": True},
    {"name": "Conseil en transformation digitale", "problems_solved": "Absence de stratégie digitale", "price_range": "1 000 - 5 000 €", "active": True},
]

DEFAULT_TEMPLATES = [
    {"name": "Premier contact - Consultatif", "type": "premier_contact", "sector": "Conseil", "objective": "Obtenir un audit",
     "subject": "Une remarque concernant votre acquisition digitale",
     "content": "Bonjour {prenom},\n\nEn consultant {entreprise}, j'ai remarqué que {observation}.\n\nVotre expertise semble clairement présentée, mais {consequence}.\n\nJ'accompagne des entreprises de services dans l'amélioration de leur acquisition digitale.\n\nJe peux vous préparer gratuitement un diagnostic rapide mettant en évidence les deux ou trois améliorations prioritaires pour {entreprise}.\n\nEst-ce un sujet qui pourrait vous intéresser actuellement ?\n\nBien cordialement,\n{signature}",
     "tone": "consultatif", "active": True},
    {"name": "Relance 1", "type": "relance_1", "sector": "Tous", "objective": "Relancer avec valeur",
     "subject": "Suite à mon message",
     "content": "Bonjour {prenom},\n\nJe me permets de revenir vers vous concernant mon précédent message au sujet de {probleme}.\n\nJ'avais identifié quelques pistes qui pourraient améliorer votre acquisition.\n\nJe peux vous les transmettre sous la forme d'un diagnostic rapide et gratuit.\n\nEst-ce un sujet pertinent pour vous actuellement ?\n\nBien cordialement,\n{signature}",
     "tone": "consultatif", "active": True},
    {"name": "Relance 2", "type": "relance_2", "sector": "Tous", "objective": "Dernière relance de valeur",
     "subject": "Dernière prise de contact",
     "content": "Bonjour {prenom},\n\nJe reviens une dernière fois vers vous concernant {probleme}.\n\nMême sans projet immédiat, je peux vous envoyer les principales observations réalisées sur {entreprise}.\n\nSouhaitez-vous que je vous les transmette ?\n\nBien cordialement,\n{signature}",
     "tone": "chaleureux", "active": True},
    {"name": "Relance finale", "type": "relance_finale", "sector": "Tous", "objective": "Clôture polie",
     "subject": "Clôture de mon suivi",
     "content": "Bonjour {prenom},\n\nJe comprends que le sujet ne soit peut-être pas prioritaire actuellement.\n\nJe clôture donc mon suivi afin de ne pas multiplier les messages.\n\nVous pourrez naturellement revenir vers moi si vous souhaitez un regard extérieur sur votre acquisition digitale.\n\nBien cordialement,\n{signature}",
     "tone": "professionnel", "active": True},
]

DEFAULT_SETTINGS = {
    "profile": {"first_name": "Jean-Philippe", "last_name": "Koffi", "company": "Koffi Digital",
                "email": "jp.koffi@prospectia.app", "phone": "", "website": "",
                "signature": "Jean-Philippe Koffi\nChef de projet marketing digital", "language": "fr", "timezone": "Europe/Paris"},
    "prospection": {"daily_volume": 5, "send_days": ["lun", "mar", "mer", "jeu", "ven"],
                    "send_hours": "09:00-18:00", "followup_delays": [3, 7, 14], "max_followups": 3,
                    "validation_required": True, "min_score": 50, "geo_zones": ["Île-de-France", "France"]},
    "ai": {"provider": "openai", "model": "gpt-5.5", "language": "fr", "tone": "consultatif",
           "temperature": 0.7, "max_tokens": 1500, "daily_limit": 100, "custom_instructions": ""},
    "email": {"provider": "simulation", "sender_email": "jp.koffi@prospectia.app", "sender_name": "Jean-Philippe Koffi",
              "reply_to": "jp.koffi@prospectia.app", "daily_limit": 5, "mode": "simulation"},
    "compliance": {"retention_days": 365, "opt_out_text": "Si vous ne souhaitez pas être recontacté à ce sujet, indiquez-le-moi simplement en réponse à cet email.",
                   "auto_delete": False},
    "automation_level": 3,
}

DEMO_COMPANIES = [
    ("Cabinet Lambert Conseil", "Conseil", "Paris", "75008", "https://lambert-conseil.fr", "contact@lambert-conseil.fr", "6-10", "Qualifié", 78),
    ("Juridis Associés", "Cabinet juridique", "Neuilly-sur-Seine", "92200", "https://juridis-associes.fr", "info@juridis-associes.fr", "11-20", "Contacté", 85),
    ("ComptaPlus Expertise", "Cabinet comptable", "Boulogne-Billancourt", "92100", "", "contact@comptaplus.fr", "1-5", "À analyser", 0),
    ("RH Solutions IDF", "Ressources humaines", "Paris", "75009", "https://rh-solutions.fr", "hello@rh-solutions.fr", "6-10", "Intéressé", 82),
    ("Martin Consultants", "Consultant indépendant", "Versailles", "78000", "", "", "1-5", "Nouveau", 0),
    ("Agence Novéa", "Agence", "Paris", "75011", "https://agence-novea.fr", "contact@novea.fr", "11-20", "Relance 1", 71),
    ("Services Pro B2B", "Services aux entreprises", "Nanterre", "92000", "https://servicespro.fr", "info@servicespro.fr", "6-10", "Qualifié", 66),
    ("Cabinet Administratif Rivoli", "Cabinet administratif", "Paris", "75001", "", "rivoli@admin.fr", "1-5", "Non qualifié", 42),
    ("Delacroix & Partners", "Conseil", "Levallois-Perret", "92300", "https://delacroix-partners.com", "contact@delacroix.com", "11-20", "Client", 90),
    ("Innov Consulting", "Conseil", "Paris", "75017", "https://innov-consulting.fr", "hello@innov.fr", "6-10", "Rendez-vous", 88),
]

DEMO_CONTACTS = [
    ("Sophie", "Lambert", "Dirigeante", "dirigeant", "s.lambert@lambert-conseil.fr"),
    ("Marc", "Jurisse", "Associé fondateur", "fondateur", "m.jurisse@juridis-associes.fr"),
    ("Claire", "Petit", "Gérante", "dirigeant", "c.petit@comptaplus.fr"),
    ("Nadia", "Bensaïd", "Directrice", "directeur_general", "n.bensaid@rh-solutions.fr"),
    ("Julien", "Martin", "Consultant", "fondateur", "j.martin@martin-consultants.fr"),
    ("Émilie", "Novéa", "Directrice marketing", "directeur_marketing", "e.novea@agence-novea.fr"),
    ("Thomas", "Girard", "Directeur commercial", "directeur_commercial", "t.girard@servicespro.fr"),
    ("Paul", "Rivoli", "Gérant", "dirigeant", "p.rivoli@admin.fr"),
    ("Anne", "Delacroix", "Associée", "fondateur", "a.delacroix@delacroix.com"),
    ("Hugo", "Renard", "CEO", "president", "h.renard@innov.fr"),
]

DEMO_CAMPAIGNS = [
    ("Cabinets de conseil – Île-de-France", "Conseil", "Île-de-France", "Active", "Audit gratuit du système d'acquisition digitale"),
    ("Cabinets juridiques – Paris", "Cabinet juridique", "Paris", "En préparation", "Audit gratuit du système d'acquisition digitale"),
    ("Services B2B – TPE", "Services aux entreprises", "France", "Brouillon", "Audit gratuit du système d'acquisition digitale"),
]
