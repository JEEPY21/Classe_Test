import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "@/components/Navbar";
import DailyOffers from "@/components/DailyOffers";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Plus, FileText, Trash2, ArrowRight, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Dashboard() {
  const navigate = useNavigate();
  const [cvs, setCvs] = useState(null);

  const load = () => api.listCVs().then((r) => setCvs(r.data)).catch(() => setCvs([]));
  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    try {
      await api.deleteCV(id);
      toast.success("CV supprimé (RGPD)");
      load();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  return (
    <div className="min-h-screen bg-secondary/40">
      <Navbar />
      <main className="max-w-7xl mx-auto px-5 py-10">
        <div className="flex items-end justify-between flex-wrap gap-4 mb-8">
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">Espace personnel</span>
            <h1 className="font-heading text-3xl sm:text-4xl font-bold tracking-tight mt-1">Tableau de bord</h1>
            <p className="text-muted-foreground mt-2">Lancez une optimisation ou reprenez un CV existant.</p>
          </div>
          <Button className="bg-primary h-11 px-6" onClick={() => navigate("/workflow")} data-testid="new-workflow-btn">
            <Plus className="w-4 h-4 mr-2" aria-hidden="true" /> Nouvelle optimisation
          </Button>
        </div>

        <DailyOffers />

        {cvs === null ? (
          <div className="flex justify-center py-24"><Loader2 className="w-6 h-6 animate-spin text-brand" /></div>
        ) : cvs.length === 0 ? (
          <div className="grain border border-dashed border-border rounded-2xl p-12 text-center bg-white">
            <FileText className="w-10 h-10 text-muted-foreground mx-auto mb-4" aria-hidden="true" />
            <h3 className="font-heading text-xl font-semibold">Aucun CV pour le moment</h3>
            <p className="text-muted-foreground mt-2 max-w-md mx-auto">
              Importez votre CV existant (PDF ou DOCX) pour démarrer votre première optimisation.
            </p>
            <Button className="bg-primary mt-6" onClick={() => navigate("/workflow")} data-testid="empty-start-btn">
              Démarrer <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" />
            </Button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {cvs.map((cv) => (
              <div key={cv.id} className="border border-border rounded-2xl p-5 bg-white flex flex-col" data-testid={`cv-card-${cv.id}`}>
                <div className="flex items-start justify-between">
                  <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                    <FileText className="w-5 h-5 text-primary" aria-hidden="true" />
                  </div>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-destructive" data-testid={`delete-cv-${cv.id}`}>
                        <Trash2 className="w-4 h-4" aria-hidden="true" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Supprimer ce CV ?</AlertDialogTitle>
                        <AlertDialogDescription>
                          Conformément au RGPD, le CV source et les optimisations associées seront définitivement supprimés.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Annuler</AlertDialogCancel>
                        <AlertDialogAction className="bg-destructive" onClick={() => remove(cv.id)} data-testid={`confirm-delete-${cv.id}`}>
                          Supprimer
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
                <h3 className="font-heading font-semibold text-lg mt-4 truncate">
                  {cv.structured?.identity?.full_name || cv.filename}
                </h3>
                <p className="text-sm text-muted-foreground truncate">{cv.structured?.identity?.title || cv.filename}</p>
                <div className="flex flex-wrap gap-1.5 mt-3">
                  <Badge variant="secondary">{cv.structured?.experiences?.length || 0} exp.</Badge>
                  <Badge variant="secondary">{cv.structured?.skills?.length || 0} compétences</Badge>
                </div>
                <Button
                  variant="outline"
                  className="mt-4 w-full"
                  onClick={() => navigate(`/workflow?cv=${cv.id}`)}
                  data-testid={`use-cv-${cv.id}`}
                >
                  Optimiser pour une offre <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" />
                </Button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
