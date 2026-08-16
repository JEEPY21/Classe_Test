import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ShieldCheck, GitCompareArrows, ScanSearch, FileCheck2, Sparkles } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useEffect } from "react";

const RULES = [
  { icon: ShieldCheck, title: "Zéro hallucination", text: "Aucune expérience, compétence ou date n'est inventée. Tout reste fondé sur votre CV réel." },
  { icon: GitCompareArrows, title: "Traçabilité totale", text: "Chaque mot-clé ATS ajouté est tracé jusqu'à sa source : l'offre ou votre CV." },
  { icon: ScanSearch, title: "Contrôle ATS réel", text: "Le CV généré est audité pour vérifier qu'un vrai ATS le lit correctement." },
  { icon: FileCheck2, title: "Validation humaine", text: "Un écran de relecture avant/après précède toujours l'export final." },
];

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  useEffect(() => {
    if (user && user !== false) navigate("/dashboard");
  }, [user, navigate]);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="max-w-7xl mx-auto px-5 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-heading font-bold text-lg">M</span>
            </div>
            <span className="font-heading font-bold text-xl tracking-tight">Matchipy</span>
          </div>
          <div className="flex items-center gap-2">
            <Link to="/login"><Button variant="ghost" data-testid="landing-login-btn">Connexion</Button></Link>
            <Link to="/register"><Button className="bg-primary" data-testid="landing-register-btn">Commencer</Button></Link>
          </div>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-5 py-16 lg:py-24 grid lg:grid-cols-2 gap-12 items-center">
        <div className="animate-fade-up">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-brand mb-5">
            <Sparkles className="w-4 h-4" aria-hidden="true" /> CV & lettres optimisés par IA
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-heading font-bold tracking-tight text-primary leading-[1.05]">
            Un CV taillé pour l'offre.<br />Sans jamais mentir.
          </h1>
          <p className="mt-6 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed">
            Matchipy reformule votre CV et rédige votre lettre à partir de votre parcours réel et de
            l'offre visée — avec traçabilité des mots-clés, contrôle ATS et validation avant/après.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/register"><Button size="lg" className="bg-primary h-12 px-8" data-testid="landing-cta-btn">Créer mon compte</Button></Link>
            <Link to="/login"><Button size="lg" variant="outline" className="h-12 px-8">J'ai déjà un compte</Button></Link>
          </div>
        </div>
        <div className="relative animate-fade-up" style={{ animationDelay: "0.1s" }}>
          <div className="absolute -inset-3 grain rounded-3xl -z-10" aria-hidden="true" />
          <img
            src="https://images.unsplash.com/photo-1698047681432-006d2449c631?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxNzV8MHwxfHNlYXJjaHwyfHxwcm9mZXNzaW9uYWwlMjByZXN1bWUlMjBqb2IlMjBhcHBsaWNhdGlvbiUyMGRlc2t8ZW58MHx8fHwxNzg2ODc0NjU5fDA&ixlib=rb-4.1.0&q=85"
            alt="Relecture d'un CV sur un bureau"
            className="rounded-2xl border border-border w-full object-cover aspect-[4/3] shadow-sm"
          />
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-5 pb-24">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {RULES.map((r, i) => (
            <div key={i} className="border border-border rounded-2xl p-6 bg-white hover:-translate-y-px transition-transform">
              <r.icon className="w-6 h-6 text-brand mb-4" aria-hidden="true" />
              <h3 className="font-heading font-semibold text-lg mb-1.5">{r.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{r.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
