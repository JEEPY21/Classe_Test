import { useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CalendarDays, MapPin, Building2, CheckCircle2, Loader2, FileText, FileType2, Sparkles, RefreshCw } from "lucide-react";
import { toast } from "sonner";

function saveBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; document.body.appendChild(a); a.click();
  a.remove(); window.URL.revokeObjectURL(url);
}

export default function DailyOffers() {
  const [offers, setOffers] = useState(null);
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState({});     // offerId -> bool (validating)
  const [downloading, setDownloading] = useState("");
  const [expanded, setExpanded] = useState({});

  const load = () => api.dailyOffers().then((r) => { setOffers(r.data.offers); setStatus(r.data.status); }).catch(() => setOffers([]));
  useEffect(() => { load(); }, []);

  const pollOffer = (offerId, sid) => {
    const iv = setInterval(async () => {
      try {
        const { data } = await api.getSession(sid);
        if (data.status === "ready" || data.status === "error") {
          clearInterval(iv);
          setBusy((b) => ({ ...b, [offerId]: false }));
          setOffers((prev) => prev.map((o) => o.id === offerId ? { ...o, generation: { session_id: sid, status: data.status } } : o));
          if (data.status === "error") toast.error("La génération a échoué pour cette offre");
          else toast.success("CV et lettre générés");
        }
      } catch (_) {}
    }, 2500);
  };

  const validate = async (offer) => {
    setBusy((b) => ({ ...b, [offer.id]: true }));
    try {
      const { data } = await api.validateOffer(offer.id);
      setOffers((prev) => prev.map((o) => o.id === offer.id ? { ...o, generation: { session_id: data.session_id, status: "pending" } } : o));
      pollOffer(offer.id, data.session_id);
    } catch (err) {
      setBusy((b) => ({ ...b, [offer.id]: false }));
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  const download = async (offer, docType, fmt) => {
    const sid = offer.generation?.session_id;
    setDownloading(`${offer.id}-${docType}-${fmt}`);
    try {
      const { data } = await api.download({ generation_id: sid, template_id: "classic", format: fmt, doc_type: docType });
      const name = (offer.entreprise || offer.intitule || "offre").replace(/\s+/g, "_");
      saveBlob(data, `${docType === "cover_letter" ? "Lettre" : "CV"}_${name}.${fmt}`);
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail)); }
    finally { setDownloading(""); }
  };

  const refresh = async () => {
    setOffers(null);
    try { await api.refreshOffers(); } catch (_) {}
    load();
  };

  return (
    <section className="mb-10" data-testid="daily-offers-section">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-brand" aria-hidden="true" />
          <h2 className="font-heading text-2xl font-bold tracking-tight">Offres du jour</h2>
          <Badge variant="secondary">CDI · Marketing · France</Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={refresh} data-testid="refresh-offers-btn"><RefreshCw className="w-4 h-4 mr-2" /> Actualiser</Button>
      </div>

      {offers === null ? (
        <div className="flex justify-center py-12"><Loader2 className="w-6 h-6 animate-spin text-brand" /></div>
      ) : offers.length === 0 ? (
        <div className="border border-dashed border-border rounded-2xl p-8 text-center bg-white">
          <p className="font-medium">Aucune offre disponible pour le moment</p>
          <p className="text-sm text-muted-foreground mt-1">
            {status?.error
              ? "Connexion à France Travail impossible (identifiants API refusés). Vérifiez l'abonnement à « Offres d'emploi v2 »."
              : "Les offres sont récupérées automatiquement chaque matin à 7h."}
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {offers.map((o) => {
            const gen = o.generation;
            const isReady = gen?.status === "ready";
            const isPending = busy[o.id] || gen?.status === "pending";
            return (
              <div key={o.id} className="border border-border rounded-2xl bg-white p-5 flex flex-col" data-testid={`offer-card-${o.id}`}>
                <h3 className="font-heading font-semibold text-lg">{o.intitule}</h3>
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground mt-2">
                  <span className="flex items-center gap-1"><Building2 className="w-4 h-4" /> {o.entreprise || "—"}</span>
                  <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {o.lieu || "—"}</span>
                  <span className="flex items-center gap-1"><CalendarDays className="w-4 h-4" /> {(o.date_publication || "").slice(0, 10)}</span>
                </div>
                <p className={`text-sm text-slate-600 mt-3 whitespace-pre-line ${expanded[o.id] ? "" : "line-clamp-4"}`}>{o.description}</p>
                {o.description?.length > 220 && (
                  <button className="text-xs text-brand mt-1 self-start hover:underline" onClick={() => setExpanded((e) => ({ ...e, [o.id]: !e[o.id] }))}>
                    {expanded[o.id] ? "Réduire" : "Voir le descriptif complet"}
                  </button>
                )}
                <div className="mt-4 pt-4 border-t border-border">
                  {isReady ? (
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="flex items-center gap-1 text-sm text-emerald-700 font-medium"><CheckCircle2 className="w-4 h-4" /> Prêt</span>
                      <Button variant="outline" size="sm" disabled={downloading} onClick={() => download(o, "cv", "pdf")} data-testid={`offer-cv-pdf-${o.id}`}>
                        {downloading === `${o.id}-cv-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4 mr-1" />} CV PDF
                      </Button>
                      <Button variant="outline" size="sm" disabled={downloading} onClick={() => download(o, "cv", "docx")} data-testid={`offer-cv-docx-${o.id}`}>
                        <FileText className="w-4 h-4 mr-1" /> CV DOCX
                      </Button>
                      <Button variant="outline" size="sm" disabled={downloading} onClick={() => download(o, "cover_letter", "pdf")} data-testid={`offer-letter-pdf-${o.id}`}>
                        {downloading === `${o.id}-cover_letter-pdf` ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileType2 className="w-4 h-4 mr-1" />} Lettre PDF
                      </Button>
                      <Button variant="outline" size="sm" disabled={downloading} onClick={() => download(o, "cover_letter", "docx")} data-testid={`offer-letter-docx-${o.id}`}>
                        <FileType2 className="w-4 h-4 mr-1" /> Lettre DOCX
                      </Button>
                    </div>
                  ) : (
                    <Button className="bg-primary" size="sm" disabled={isPending} onClick={() => validate(o)} data-testid={`validate-offer-${o.id}`}>
                      {isPending ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Génération…</> : <><CheckCircle2 className="w-4 h-4 mr-2" /> Valider</>}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
