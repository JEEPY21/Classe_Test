import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowRight, ArrowLeft, ScanSearch, CheckCircle2, XCircle, AlertTriangle, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function Step4ATS({ session, templateId, onNext, onBack }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const run = async () => {
    if (!session) return;
    setLoading(true);
    try {
      const { data } = await api.atsCheck({ generation_id: session.id, template_id: templateId });
      setResult(data);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { run(); /* eslint-disable-next-line */ }, []);

  const report = result?.report;
  const critical = report?.critical_issues || [];

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 4</span>
        <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">Contrôle qualité ATS</h1>
        <p className="text-muted-foreground mt-2">On vérifie que votre CV mis en page est correctement lu, champ par champ — pas une simple case à cocher.</p>
      </div>

      {result && (
        <div className={`rounded-xl border px-4 py-3 text-sm ${result.affinda_available ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-blue-200 bg-blue-50 text-blue-800"}`} data-testid="ats-source-banner">
          {result.affinda_available
            ? "Analyse effectuée par l'API professionnelle Affinda."
            : `Analyse de lisibilité interne (extraction native du PDF généré). ${result.affinda_message || "Affinda indisponible."}`}
        </div>
      )}

      {loading || !result ? (
        <div className="border border-border rounded-2xl bg-white p-12 text-center">
          <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto mb-3" />
          <p className="font-medium">Rendu du CV et audit ATS en cours…</p>
        </div>
      ) : (
        <>
          <div className="border border-border rounded-2xl bg-white p-6 flex items-center gap-6" data-testid="ats-score">
            <div className="text-center">
              <div className="font-heading text-5xl font-bold" style={{ color: report.score >= 75 ? "#10B981" : report.score >= 50 ? "#F59E0B" : "#EF4444" }}>{report.score}%</div>
              <p className="text-xs text-muted-foreground mt-1">Lisibilité ATS</p>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1"><ScanSearch className="w-5 h-5 text-brand" aria-hidden="true" /><span className="font-semibold">{report.read_fields ?? "—"} / {report.total_fields ?? "—"} champs correctement lus</span></div>
              {report.has_text_layer === false && <p className="text-sm text-destructive mt-1">Aucune couche de texte détectée — le PDF risque d'être illisible pour un ATS.</p>}
            </div>
          </div>

          {critical.length > 0 ? (
            <div className="border border-red-200 bg-red-50 rounded-2xl p-5" data-testid="ats-critical">
              <div className="flex items-center gap-2 font-semibold text-red-800 mb-2"><AlertTriangle className="w-5 h-5" /> Champs critiques mal lus</div>
              <p className="text-sm text-red-700 mb-2">Ces éléments essentiels n'ont pas été extraits correctement. Corrigez la mise en forme (choisissez un autre template à l'étape suivante) ou vérifiez le contenu avant export :</p>
              <div className="flex flex-wrap gap-2">{critical.map((c, i) => <Badge key={i} className="bg-red-600">{c}</Badge>)}</div>
            </div>
          ) : (
            <div className="border border-emerald-200 bg-emerald-50 rounded-2xl p-4 text-emerald-800 text-sm flex items-center gap-2" data-testid="ats-ok">
              <CheckCircle2 className="w-5 h-5" /> Tous les champs critiques (nom, contact, postes, dates) sont correctement lus.
            </div>
          )}

          <div className="border border-border rounded-2xl bg-white p-5" data-testid="ats-fields">
            <h3 className="font-heading font-semibold text-lg mb-3">Détail par champ</h3>
            <div className="grid sm:grid-cols-2 gap-2">
              {(report.fields || []).map((f, i) => (
                <div key={i} className="flex items-start gap-2 border border-border rounded-lg px-3 py-2">
                  {f.status === "read" ? <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" /> : <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />}
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{f.label}</p>
                    <p className="text-xs text-muted-foreground">{f.status === "read" ? "Lu correctement" : "Non détecté"}{f.critical ? " · critique" : ""}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex justify-between sticky bottom-4 bg-white/80 backdrop-blur-xl border border-border rounded-xl p-3">
            <Button variant="outline" onClick={onBack}><ArrowLeft className="w-4 h-4 mr-2" /> Retour</Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={run}><RefreshCw className="w-4 h-4 mr-2" /> Relancer</Button>
              <Button className="bg-primary" onClick={onNext} data-testid="ats-next-btn">Mise en page & export <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" /></Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
