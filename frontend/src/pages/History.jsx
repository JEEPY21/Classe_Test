import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { History, Plus, Trash2, FileText, FileType2, Loader2 } from "lucide-react";
import { toast } from "sonner";

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

function scoreColor(v) {
  return v >= 75 ? "#10B981" : v >= 50 ? "#F59E0B" : "#EF4444";
}

export default function HistoryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState(null);
  const [downloading, setDownloading] = useState("");

  const load = () => api.listHistory().then((r) => setItems(r.data)).catch(() => setItems([]));
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    try { await api.deleteHistory(id); toast.success("Génération supprimée de l'historique"); load(); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  const dl = async (item, docType, fmt) => {
    setDownloading(`${item.id}-${docType}-${fmt}`);
    try {
      const { data } = await api.downloadHistoryDoc(item.id, { doc_type: docType, format: fmt });
      const name = (item.entreprise || item.poste || "document").replace(/\s+/g, "_");
      const prefix = docType === "cover_letter" ? "Lettre" : "CV";
      saveBlob(data, `${prefix}_${name}.${fmt}`);
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setDownloading(""); }
  };

  return (
    <div className="min-h-screen bg-secondary/40">
      <Navbar />
      <main className="max-w-7xl mx-auto px-5 py-10">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Sauvegarde automatique</span>
            <h1 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mt-1">Historique des générations</h1>
            <p className="text-muted-foreground mt-2">Chaque génération est enregistrée automatiquement. Retrouvez et téléchargez le CV et la lettre sans relancer l'IA.</p>
          </div>
          <Button className="bg-primary h-11 px-6" onClick={() => navigate("/workflow")} data-testid="history-new-btn">
            <Plus className="w-4 h-4 mr-2" aria-hidden="true" /> Nouvelle optimisation
          </Button>
        </div>

        {items === null ? (
          <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-brand" /></div>
        ) : items.length === 0 ? (
          <div className="grain border border-dashed border-border rounded-2xl p-12 text-center bg-white">
            <History className="w-10 h-10 text-muted-foreground mx-auto mb-4" aria-hidden="true" />
            <h3 className="font-heading text-xl font-semibold">Aucune génération enregistrée</h3>
            <p className="text-muted-foreground mt-2 max-w-md mx-auto">Lancez une optimisation : le résultat sera sauvegardé ici automatiquement.</p>
            <Button className="bg-primary mt-6" onClick={() => navigate("/workflow")}>Démarrer</Button>
          </div>
        ) : (
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.id} className="border border-border rounded-2xl bg-white p-5" data-testid={`history-row-${item.id}`}>
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-12 h-12 rounded-full border border-border flex items-center justify-center shrink-0"
                      style={{ color: scoreColor(item.score?.overall || 0) }}>
                      <span className="font-heading font-bold text-sm">{item.score?.overall ?? "—"}</span>
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-heading font-semibold text-lg truncate">{item.poste || "Poste non précisé"}</h3>
                      <p className="text-sm text-muted-foreground truncate">{item.entreprise || "—"} · {(item.created_at || "").slice(0, 10)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(item, "cv", "pdf")} data-testid={`hist-cv-pdf-${item.id}`}>
                      {downloading === `${item.id}-cv-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />} CV PDF
                    </Button>
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(item, "cv", "docx")} data-testid={`hist-cv-docx-${item.id}`}>
                      <FileText className="w-4 h-4 mr-1" /> CV DOCX
                    </Button>
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(item, "cover_letter", "pdf")} data-testid={`hist-letter-pdf-${item.id}`}>
                      {downloading === `${item.id}-cover_letter-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileType2 className="w-4 h-4 mr-1" />} Lettre PDF
                    </Button>
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(item, "cover_letter", "docx")} data-testid={`hist-letter-docx-${item.id}`}>
                      <FileType2 className="w-4 h-4 mr-1" /> Lettre DOCX
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive" data-testid={`hist-delete-${item.id}`}><Trash2 className="w-4 h-4" /></Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Supprimer de l'historique ?</AlertDialogTitle>
                          <AlertDialogDescription>Le CV et la lettre sauvegardés seront définitivement supprimés (RGPD).</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Annuler</AlertDialogCancel>
                          <AlertDialogAction className="bg-destructive" onClick={() => remove(item.id)} data-testid={`hist-confirm-delete-${item.id}`}>Supprimer</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
