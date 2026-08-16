import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowRight, Wand2, Globe } from "lucide-react";
import { toast } from "sonner";

const LANGS = { fr: "Français", en: "Anglais", es: "Espagnol", de: "Allemand" };

export default function Step2Job({ job, setJob, onNext }) {
  const [text, setText] = useState(job?.raw_text || "");
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    if (text.trim().length < 20) { toast.error("Collez le texte complet de l'offre."); return; }
    setLoading(true);
    try {
      const { data } = await api.analyzeJob(text);
      setJob(data);
      toast.success("Offre analysée");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  const a = job?.analysis;

  return (
    <div className="animate-fade-up">
      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 2</span>
      <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">Offre d'emploi</h1>
      <p className="text-muted-foreground mt-2 mb-6">Collez l'offre visée. Matchipy en extrait les compétences, mots-clés et la langue de génération.</p>

      <div className="border border-border rounded-2xl bg-white p-5 sm:p-6">
        <Textarea rows={10} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Collez ici le texte complet de l'offre d'emploi…" data-testid="job-textarea" />
        <div className="flex justify-end mt-4">
          <Button className="bg-primary" onClick={analyze} disabled={loading} data-testid="analyze-job-btn">
            {loading ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Wand2 className="w-4 h-4 mr-2" aria-hidden="true" />}
            Analyser l'offre
          </Button>
        </div>
      </div>

      {a && (
        <div className="mt-6 space-y-4 animate-fade-up" data-testid="job-analysis">
          <div className="grid sm:grid-cols-2 gap-4">
            <Panel title="Poste détecté"><p className="font-heading text-xl font-semibold">{a.job_title || "—"}</p>{a.company && <p className="text-muted-foreground">{a.company}</p>}</Panel>
            <Panel title="Langue de génération">
              <div className="flex items-center gap-2"><Globe className="w-5 h-5 text-brand" aria-hidden="true" />
                <span className="font-heading text-xl font-semibold">{LANGS[a.language] || a.language}</span></div>
            </Panel>
          </div>
          <Chips title="Compétences techniques (hard skills)" items={a.hard_skills} testid="hard-skills" />
          <Chips title="Compétences comportementales (soft skills)" items={a.soft_skills} variant="outline" />
          <Chips title="Mots-clés récurrents" items={a.keywords} variant="outline" />

          <div className="flex justify-end sticky bottom-4">
            <Button className="bg-primary" onClick={onNext} data-testid="job-next-btn">
              Générer le CV optimisé <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

const Panel = ({ title, children }) => (
  <div className="border border-border rounded-2xl bg-white p-5">
    <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">{title}</span>
    <div className="mt-2">{children}</div>
  </div>
);
const Chips = ({ title, items, variant = "secondary", testid }) => (
  <div className="border border-border rounded-2xl bg-white p-5" data-testid={testid}>
    <span className="text-xs font-semibold uppercase tracking-[0.15em] text-muted-foreground">{title}</span>
    <div className="flex flex-wrap gap-2 mt-3">
      {(items || []).length ? items.map((x, i) => <Badge key={i} variant={variant}>{x}</Badge>) : <span className="text-sm text-muted-foreground">—</span>}
    </div>
  </div>
);
