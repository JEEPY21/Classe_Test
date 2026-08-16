import { CheckCircle2, Circle } from "lucide-react";

const STEPS = [
  { n: 1, title: "CV source", sub: "Extraction & vérification" },
  { n: 2, title: "Offre d'emploi", sub: "Analyse & mots-clés" },
  { n: 3, title: "Génération", sub: "Reformulation contrôlée" },
  { n: 4, title: "Contrôle ATS", sub: "Lisibilité technique" },
  { n: 5, title: "Mise en page", sub: "Relecture & export" },
];

export default function Stepper({ current, maxReached, onNavigate }) {
  return (
    <nav aria-label="Étapes" className="lg:sticky lg:top-24">
      {/* Mobile: horizontal */}
      <ol className="flex lg:hidden gap-2 overflow-x-auto pb-2">
        {STEPS.map((s) => {
          const done = s.n < current;
          const active = s.n === current;
          return (
            <li key={s.n} className="shrink-0">
              <button
                disabled={s.n > maxReached}
                onClick={() => onNavigate(s.n)}
                data-testid={`stepper-mobile-${s.n}`}
                className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  active
                    ? "bg-primary text-primary-foreground border-primary"
                    : done
                    ? "bg-white border-brand text-brand"
                    : "bg-white border-border text-muted-foreground disabled:opacity-50"
                }`}
              >
                {s.n}. {s.title}
              </button>
            </li>
          );
        })}
      </ol>

      {/* Desktop: vertical */}
      <ol className="hidden lg:flex flex-col gap-1">
        {STEPS.map((s) => {
          const done = s.n < current;
          const active = s.n === current;
          const reachable = s.n <= maxReached;
          return (
            <li key={s.n}>
              <button
                disabled={!reachable}
                onClick={() => onNavigate(s.n)}
                data-testid={`stepper-${s.n}`}
                className={`w-full flex items-start gap-3 text-left px-4 py-3 rounded-xl border transition-colors ${
                  active
                    ? "border-primary bg-primary/[0.04]"
                    : "border-transparent hover:bg-secondary disabled:opacity-40 disabled:hover:bg-transparent"
                }`}
              >
                <span className="mt-0.5">
                  {done ? (
                    <CheckCircle2 className="w-5 h-5 text-brand" aria-hidden="true" />
                  ) : (
                    <Circle
                      className={`w-5 h-5 ${active ? "text-primary" : "text-muted-foreground"}`}
                      aria-hidden="true"
                    />
                  )}
                </span>
                <span>
                  <span className={`block text-sm font-semibold ${active ? "text-primary" : "text-foreground"}`}>
                    {s.title}
                  </span>
                  <span className="block text-xs text-muted-foreground">{s.sub}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
