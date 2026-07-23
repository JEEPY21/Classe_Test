import React, { useState, useRef } from "react";
import client, { apiError } from "@/lib/api";
import { Btn, Select } from "@/components/kit";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Upload, FileText, CheckCircle2, AlertTriangle, Loader2, ArrowRight, Download, X } from "lucide-react";

export default function ImportDialog({ open, onOpenChange, onDone }) {
  const [step, setStep] = useState("select"); // select | preview | report
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);
  const [mapping, setMapping] = useState({});
  const [strategy, setStrategy] = useState("ignore");
  const [report, setReport] = useState(null);
  const fileRef = useRef();

  const reset = () => { setStep("select"); setPreview(null); setMapping({}); setReport(null); setStrategy("ignore"); };
  const close = () => { reset(); onOpenChange(false); };

  const onFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await client.post("/import/preview", fd);
      setPreview(data);
      setMapping(data.mapping || {});
      setStep("preview");
    } catch (err) { toast.error(apiError(err)); }
    finally { setLoading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  const confirm = async () => {
    if (!mapping.name) return toast.error("Le champ « Nom entreprise » doit être mappé à une colonne.");
    setLoading(true);
    try {
      const { data } = await client.post("/import/confirm", { import_id: preview.import_id, mapping, duplicate_strategy: strategy });
      setReport(data);
      setStep("report");
      onDone && onDone();
    } catch (err) { toast.error(apiError(err)); }
    finally { setLoading(false); }
  };

  const downloadRejected = () => {
    const rows = report.rejected_rows || [];
    const lines = ["ligne;motif"].concat(rows.map((r) => `${r.line};"${r.reason}"`));
    const url = URL.createObjectURL(new Blob([lines.join("\n")], { type: "text/csv" }));
    const a = document.createElement("a"); a.href = url; a.download = "lignes_rejetees.csv"; a.click();
  };

  const fields = preview?.available_fields || [];
  const labels = preview?.field_labels || {};

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) reset(); onOpenChange(v); }}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader><DialogTitle>Importer des entreprises</DialogTitle></DialogHeader>

        {step === "select" && (
          <div className="py-8">
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls,.txt" hidden onChange={onFile} data-testid="import-file-input" />
            <button onClick={() => fileRef.current.click()} disabled={loading}
              className="w-full border-2 border-dashed border-slate-300 rounded-xl py-12 flex flex-col items-center gap-3 hover:border-blue-400 hover:bg-blue-50/40 transition-colors" data-testid="import-dropzone">
              {loading ? <Loader2 className="w-8 h-8 text-blue-500 animate-spin" /> : <Upload className="w-8 h-8 text-slate-400" />}
              <span className="text-sm font-medium text-slate-700">Sélectionner un fichier CSV ou Excel</span>
              <span className="text-xs text-slate-400">CSV (virgule / point-virgule / tabulation), UTF-8, accents et Excel .xlsx pris en charge</span>
            </button>
          </div>
        )}

        {step === "preview" && preview && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[["Format", preview.meta.ext?.toUpperCase()], ["Encodage", preview.meta.encoding],
                ["Séparateur", preview.meta.separator], ["Lignes", preview.meta.n_rows],
                ["Colonnes", preview.meta.n_cols], ["Lignes valides", preview.valid_rows],
                ["Doublons fichier", preview.internal_duplicates], ["Doublons base", preview.db_duplicates]].map(([k, v]) => (
                <div key={k} className="bg-slate-50 rounded-lg px-3 py-2 border border-slate-100">
                  <div className="text-[10px] uppercase text-slate-400">{k}</div>
                  <div className="text-sm font-semibold text-slate-800">{v}</div>
                </div>
              ))}
            </div>

            {!mapping.name && (
              <div className="flex items-center gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                <AlertTriangle className="w-4 h-4" /> Le champ obligatoire « Nom entreprise » n'est associé à aucune colonne. Mappez-le ci-dessous.
              </div>
            )}

            <div>
              <div className="text-sm font-medium text-slate-700 mb-2">Correspondance des colonnes</div>
              <div className="max-h-56 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100">
                {fields.map((f) => (
                  <div key={f} className="flex items-center gap-3 px-3 py-2">
                    <span className="text-xs w-40 flex-shrink-0 text-slate-600">{labels[f]}</span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-300" />
                    <Select className="flex-1 text-xs" value={mapping[f] || ""} data-testid={`map-${f}`}
                      onChange={(e) => setMapping({ ...mapping, [f]: e.target.value })}>
                      <option value="">— Ignorer —</option>
                      {preview.headers.map((h) => <option key={h} value={h}>{h}</option>)}
                    </Select>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="text-sm font-medium text-slate-700 mb-2">Aperçu (5 premières lignes)</div>
              <div className="overflow-x-auto border border-slate-200 rounded-lg">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50"><tr>{preview.headers.map((h) => <th key={h} className="px-2 py-1.5 text-left font-medium text-slate-500 whitespace-nowrap">{h}</th>)}</tr></thead>
                  <tbody className="divide-y divide-slate-100">
                    {preview.sample.map((row, i) => (
                      <tr key={i}>{preview.headers.map((h) => <td key={h} className="px-2 py-1.5 text-slate-600 whitespace-nowrap max-w-[160px] truncate">{row[h]}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {preview.warning_count > 0 && (
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                {preview.warning_count} ligne(s) avec avertissements (nom manquant / email invalide) seront rejetées ou signalées.
              </div>
            )}

            <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-slate-100">
              <span className="text-sm text-slate-600">Doublons existants :</span>
              <Select value={strategy} onChange={(e) => setStrategy(e.target.value)} data-testid="dup-strategy">
                <option value="ignore">Ignorer la ligne</option>
                <option value="update">Compléter les champs manquants</option>
                <option value="create_anyway">Créer quand même</option>
              </Select>
              <div className="flex-1" />
              <Btn variant="secondary" onClick={close}>Annuler</Btn>
              <Btn variant="blue" onClick={confirm} disabled={loading || !mapping.name} data-testid="confirm-import-btn">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />} Confirmer l'import
              </Btn>
            </div>
          </div>
        )}

        {step === "report" && report && (
          <div className="space-y-5 py-2" data-testid="import-report">
            <div className="flex items-center gap-3 text-emerald-700">
              <CheckCircle2 className="w-8 h-8" />
              <div><div className="font-heading font-semibold text-lg">Import terminé</div>
                <div className="text-xs text-slate-500">Identifiant : {report.import_id?.slice(0, 8)}</div></div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[["Entreprises créées", report.companies_created, "text-emerald-600"],
                ["Entreprises mises à jour", report.companies_updated, "text-blue-600"],
                ["Contacts créés", report.contacts_created, "text-emerald-600"],
                ["Doublons ignorés", report.duplicates_ignored, "text-slate-500"],
                ["Lignes rejetées", report.rejected, "text-red-600"],
                ["Lignes totales", report.total_lines, "text-slate-700"]].map(([k, v, c]) => (
                <div key={k} className="bg-slate-50 rounded-lg px-3 py-3 border border-slate-100">
                  <div className={`text-2xl font-heading font-bold ${c}`}>{v}</div>
                  <div className="text-xs text-slate-400 mt-0.5">{k}</div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2">
              {report.rejected > 0 && <Btn variant="secondary" onClick={downloadRejected} data-testid="download-rejected-btn"><Download className="w-4 h-4" /> Télécharger les lignes rejetées</Btn>}
              <div className="flex-1" />
              <Btn variant="blue" onClick={close} data-testid="close-report-btn">Terminer</Btn>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
