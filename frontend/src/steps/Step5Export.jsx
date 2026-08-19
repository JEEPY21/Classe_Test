import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowLeft, FileText, FileType2, Download, Eye, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

export default function Step5Export({ session, templateId, setTemplateId, onBack }) {
  const [templates, setTemplates] = useState([]);
  const [preview, setPreview] = useState(null);
  const [reviewed, setReviewed] = useState(false);
  const [downloading, setDownloading] = useState("");
  const hasCover = (preview?.cover_letter?.paragraphs || []).length > 0;

  useEffect(() => { api.templates().then((r) => setTemplates(r.data)).catch(() => {}); }, []);
  useEffect(() => {
    if (session) api.preview({ generation_id: session.id }).then((r) => setPreview(r.data)).catch((e) => toast.error(formatApiError(e.response?.data?.detail)));
  }, [session]);

  const download = async (docType, format) => {
    const key = `${docType}-${format}`;
    setDownloading(key);
    try {
      const { data } = await api.download({ generation_id: session.id, template_id: templateId, format, doc_type: docType });
      const name = (preview?.final?.identity?.full_name || "cv").replace(/\s+/g, "_");
      const prefix = docType === "cover_letter" ? "Lettre" : "CV";
      saveBlob(data, `${prefix}_${name}.${format}`);
      toast.success(`${docType === "cover_letter" ? "Lettre" : "CV"} ${format.toUpperCase()} téléchargé`);
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setDownloading("");
    }
  };

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 5</span>
        <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">Mise en page & export</h1>
        <p className="text-muted-foreground mt-2">Choisissez un template ATS-friendly, relisez le avant/après, puis exportez en PDF ou DOCX.</p>
      </div>

      {/* Templates */}
      <div className="border border-border rounded-2xl bg-white p-5">
        <h3 className="font-heading font-semibold text-lg mb-4">Template</h3>
        <div className="grid sm:grid-cols-3 gap-4">
          {templates.map((t) => (
            <button key={t.id} onClick={() => setTemplateId(t.id)} data-testid={`template-${t.id}`}
              className={`text-left border rounded-xl p-4 transition-colors ${templateId === t.id ? "border-primary ring-2 ring-primary/20" : "border-border hover:border-primary/40"}`}>
              <div className="flex items-center justify-between">
                <span className="font-heading font-semibold">{t.name}</span>
                {templateId === t.id && <CheckCircle2 className="w-4 h-4 text-brand" />}
              </div>
              <div className="mt-3 rounded-md border border-border bg-secondary/40 h-24 p-2 space-y-1">
                <div className="h-2 w-2/3 rounded" style={{ background: t.accent }} />
                <div className="h-1.5 w-full bg-slate-200 rounded" />
                <div className="h-1.5 w-5/6 bg-slate-200 rounded" />
                <div className="h-1.5 w-1/2 bg-slate-200 rounded" />
              </div>
              <p className="text-xs text-muted-foreground mt-2">{t.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Before / After review (mandatory) */}
      <div className="border border-border rounded-2xl bg-white p-5" data-testid="review-card">
        <div className="flex items-center gap-2 mb-4"><Eye className="w-5 h-5 text-brand" aria-hidden="true" /><h3 className="font-heading font-semibold text-lg">Relecture avant / après</h3></div>
        {!preview ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-brand" /></div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            <ReviewColumn title="CV d'origine" data={preview.original} tone="muted" />
            <ReviewColumn title="CV optimisé (final)" data={preview.final} tone="brand" cover={preview.cover_letter} />
          </div>
        )}
        <label className="flex items-center gap-3 mt-5 border border-border rounded-xl px-4 py-3 cursor-pointer bg-secondary/30" data-testid="review-confirm">
          <Checkbox checked={reviewed} onCheckedChange={(v) => setReviewed(!!v)} />
          <span className="text-sm">J'ai relu le avant/après et je valide le contenu final avant export.</span>
        </label>
      </div>

      {/* Export */}
      <div className="border border-border rounded-2xl bg-white p-5">
        <h3 className="font-heading font-semibold text-lg mb-1">Export final</h3>
        <p className="text-sm text-muted-foreground mb-4">PDF (texte natif) et DOCX, tous deux compatibles ATS. Le CV et la lettre se téléchargent séparément.</p>

        <div className="grid sm:grid-cols-2 gap-4">
          <div className="border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3"><FileText className="w-4 h-4 text-brand" aria-hidden="true" /><span className="font-semibold">CV</span></div>
            <div className="flex flex-wrap gap-2">
              <Button className="bg-primary" disabled={!reviewed || downloading} onClick={() => download("cv", "pdf")} data-testid="export-cv-pdf-btn">
                {downloading === "cv-pdf" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" aria-hidden="true" />} CV PDF
              </Button>
              <Button variant="outline" disabled={!reviewed || downloading} onClick={() => download("cv", "docx")} data-testid="export-cv-docx-btn">
                {downloading === "cv-docx" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" aria-hidden="true" />} CV DOCX
              </Button>
            </div>
          </div>

          <div className="border border-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3"><FileType2 className="w-4 h-4 text-brand" aria-hidden="true" /><span className="font-semibold">Lettre de motivation</span></div>
            {hasCover ? (
              <div className="flex flex-wrap gap-2">
                <Button className="bg-primary" disabled={!reviewed || downloading} onClick={() => download("cover_letter", "pdf")} data-testid="export-letter-pdf-btn">
                  {downloading === "cover_letter-pdf" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" aria-hidden="true" />} Lettre PDF
                </Button>
                <Button variant="outline" disabled={!reviewed || downloading} onClick={() => download("cover_letter", "docx")} data-testid="export-letter-docx-btn">
                  {downloading === "cover_letter-docx" ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Download className="w-4 h-4 mr-2" aria-hidden="true" />} Lettre DOCX
                </Button>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Aucune lettre générée pour cette candidature.</p>
            )}
          </div>
        </div>
        {!reviewed && <p className="text-xs text-amber-600 mt-3">Validez la relecture ci-dessus pour activer les téléchargements.</p>}
      </div>

      <div className="flex justify-start">
        <Button variant="outline" onClick={onBack}><ArrowLeft className="w-4 h-4 mr-2" /> Retour au contrôle ATS</Button>
      </div>
    </div>
  );
}

function ReviewColumn({ title, data, tone, cover }) {
  return (
    <div className={`rounded-xl border p-4 ${tone === "brand" ? "border-primary/30 bg-primary/[0.02]" : "border-border bg-secondary/30"}`}>
      <div className="text-xs font-semibold uppercase tracking-[0.15em] mb-3" style={{ color: tone === "brand" ? "#2563EB" : "#64748B" }}>{title}</div>
      <div className="space-y-3 text-sm">
        {(data?.experiences || []).map((e, i) => (
          <div key={i}>
            <p className="font-semibold">{e.role}{e.company ? ` — ${e.company}` : ""}</p>
            <ul className="list-disc pl-4 text-slate-600 mt-1 space-y-0.5">
              {(e.bullets || []).map((b, bi) => <li key={bi}>{b}</li>)}
            </ul>
          </div>
        ))}
        {data?.skills?.length > 0 && (
          <div>
            <p className="font-semibold mb-1">Compétences</p>
            <div className="flex flex-wrap gap-1.5">{data.skills.map((s, i) => <Badge key={i} variant="outline" className="bg-white">{s}</Badge>)}</div>
          </div>
        )}
        {cover?.paragraphs?.length > 0 && (
          <div>
            <p className="font-semibold mb-1">Lettre de motivation</p>
            <div className="text-slate-600 space-y-1">{cover.paragraphs.map((p, i) => <p key={i}>{p}</p>)}</div>
          </div>
        )}
      </div>
    </div>
  );
}
