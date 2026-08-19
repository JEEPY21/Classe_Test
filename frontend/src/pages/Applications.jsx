import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { BriefcaseBusiness, Plus, Trash2, Pencil, FileText, FileType2, Loader2, Filter } from "lucide-react";
import { toast } from "sonner";

const STATUSES = ["envoyée", "relance", "entretien", "refusée", "acceptée"];
const STATUS_STYLE = {
  "envoyée": "bg-blue-50 text-blue-700 border-blue-200",
  "relance": "bg-amber-50 text-amber-700 border-amber-200",
  "entretien": "bg-violet-50 text-violet-700 border-violet-200",
  "refusée": "bg-red-50 text-red-700 border-red-200",
  "acceptée": "bg-emerald-50 text-emerald-700 border-emerald-200",
};

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

export default function Applications() {
  const navigate = useNavigate();
  const [apps, setApps] = useState(null);
  const [filter, setFilter] = useState("all");
  const [editing, setEditing] = useState(null);
  const [downloading, setDownloading] = useState("");

  const load = (statut) => {
    api.listApplications(statut && statut !== "all" ? statut : undefined)
      .then((r) => setApps(r.data)).catch(() => setApps([]));
  };
  useEffect(() => { load(filter); }, [filter]);

  const remove = async (id) => {
    try { await api.deleteApplication(id); toast.success("Candidature supprimée"); load(filter); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  const saveEdit = async () => {
    try {
      await api.updateApplication(editing.id, {
        poste: editing.poste, entreprise: editing.entreprise, statut: editing.statut,
        date_candidature: editing.date_candidature, notes: editing.notes,
      });
      toast.success("Candidature mise à jour");
      setEditing(null); load(filter);
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  const changeStatus = async (id, statut) => {
    try { await api.updateApplication(id, { statut }); load(filter); }
    catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
  };

  const dl = async (app, docType, fmt) => {
    setDownloading(`${app.id}-${docType}-${fmt}`);
    try {
      const { data } = await api.downloadApplicationDoc(app.id, { doc_type: docType, format: fmt });
      const name = (app.entreprise || app.poste || "candidature").replace(/\s+/g, "_");
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
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Suivi manuel</span>
            <h1 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mt-1">Mes candidatures</h1>
            <p className="text-muted-foreground mt-2">Centralisez vos candidatures, leur statut et les documents envoyés.</p>
          </div>
          <Button className="bg-primary h-11 px-6" onClick={() => navigate("/workflow")} data-testid="new-optimisation-btn">
            <Plus className="w-4 h-4 mr-2" aria-hidden="true" /> Nouvelle optimisation
          </Button>
        </div>

        <div className="flex items-center gap-3 mb-5">
          <Filter className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-56 bg-white" data-testid="status-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous les statuts</SelectItem>
              {STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        {apps === null ? (
          <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-brand" /></div>
        ) : apps.length === 0 ? (
          <div className="grain border border-dashed border-border rounded-2xl p-12 text-center bg-white">
            <BriefcaseBusiness className="w-10 h-10 text-muted-foreground mx-auto mb-4" aria-hidden="true" />
            <h3 className="font-heading text-xl font-semibold">Aucune candidature suivie</h3>
            <p className="text-muted-foreground mt-2 max-w-md mx-auto">Générez un CV pour une offre, puis enregistrez la candidature depuis l'étape d'export.</p>
            <Button className="bg-primary mt-6" onClick={() => navigate("/workflow")}>Démarrer une optimisation</Button>
          </div>
        ) : (
          <div className="space-y-3">
            {apps.map((app) => (
              <div key={app.id} className="border border-border rounded-2xl bg-white p-5" data-testid={`app-row-${app.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h3 className="font-heading font-semibold text-lg truncate">{app.poste || "Poste non précisé"}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_STYLE[app.statut] || ""}`} data-testid={`app-status-${app.id}`}>{app.statut}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">{app.entreprise || "—"} · {app.date_candidature}</p>
                    {app.notes && <p className="text-sm text-slate-600 mt-2">{app.notes}</p>}
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Select value={app.statut} onValueChange={(v) => changeStatus(app.id, v)}>
                      <SelectTrigger className="w-36 h-9" data-testid={`quick-status-${app.id}`}><SelectValue /></SelectTrigger>
                      <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                    </Select>
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(app, "cv", "pdf")} data-testid={`dl-cv-${app.id}`}>
                      {downloading === `${app.id}-cv-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />} CV
                    </Button>
                    <Button variant="outline" size="sm" disabled={downloading} onClick={() => dl(app, "cover_letter", "pdf")} data-testid={`dl-letter-${app.id}`}>
                      {downloading === `${app.id}-cover_letter-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileType2 className="w-4 h-4 mr-1" />} Lettre
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => setEditing({ ...app })} data-testid={`edit-${app.id}`}><Pencil className="w-4 h-4" /></Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive" data-testid={`delete-app-${app.id}`}><Trash2 className="w-4 h-4" /></Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Supprimer cette candidature ?</AlertDialogTitle>
                          <AlertDialogDescription>Cette action est définitive. Les documents attachés seront supprimés.</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Annuler</AlertDialogCancel>
                          <AlertDialogAction className="bg-destructive" onClick={() => remove(app.id)} data-testid={`confirm-delete-app-${app.id}`}>Supprimer</AlertDialogAction>
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

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Modifier la candidature</DialogTitle></DialogHeader>
          {editing && (
            <div className="space-y-3">
              <div><Label>Poste</Label><Input className="mt-1" value={editing.poste || ""} onChange={(e) => setEditing({ ...editing, poste: e.target.value })} data-testid="edit-poste-input" /></div>
              <div><Label>Entreprise</Label><Input className="mt-1" value={editing.entreprise || ""} onChange={(e) => setEditing({ ...editing, entreprise: e.target.value })} /></div>
              <div className="grid grid-cols-2 gap-3">
                <div><Label>Date</Label><Input type="date" className="mt-1" value={editing.date_candidature || ""} onChange={(e) => setEditing({ ...editing, date_candidature: e.target.value })} /></div>
                <div>
                  <Label>Statut</Label>
                  <Select value={editing.statut} onValueChange={(v) => setEditing({ ...editing, statut: v })}>
                    <SelectTrigger className="mt-1" data-testid="edit-statut-select"><SelectValue /></SelectTrigger>
                    <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>
              <div><Label>Notes</Label><Textarea rows={3} className="mt-1" value={editing.notes || ""} onChange={(e) => setEditing({ ...editing, notes: e.target.value })} /></div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>Annuler</Button>
            <Button className="bg-primary" onClick={saveEdit} data-testid="save-edit-btn">Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
