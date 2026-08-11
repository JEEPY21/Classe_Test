import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Select, Textarea } from "@/components/kit";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, MessageSquare, CheckCircle2, Send, Sparkles, Loader2, Mail } from "lucide-react";

const sentColor = { positif: "text-emerald-600", neutre: "text-slate-500", négatif: "text-red-600" };

export default function Replies() {
  const [rows, setRows] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ company_id: "", text: "" });
  const [active, setActive] = useState(null);
  const [response, setResponse] = useState("");
  const [sending, setSending] = useState(false);

  const load = () => client.get("/replies").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); client.get("/companies").then((r) => setCompanies(r.data)); }, []);

  const analyze = async () => {
    if (!form.company_id || !form.text) return toast.error("Entreprise et texte requis");
    try { await client.post("/replies", form); toast.success("Réponse analysée par l'IA"); setShow(false); setForm({ company_id: "", text: "" }); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  const openReply = (r) => {
    setActive(r);
    setResponse(r.response_text || r.analysis?.suggested_reply || "");
  };

  const sendResponse = async () => {
    if (!response.trim()) return toast.error("Le message ne peut pas être vide");
    setSending(true);
    try {
      const { data } = await client.post(`/replies/${active.id}/respond`, { message: response });
      toast.success(`Réponse envoyée à ${data.dest || "le prospect"} (simulation)`);
      setActive(null);
      load();
    } catch (e) { toast.error(apiError(e)); }
    finally { setSending(false); }
  };

  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Réponses" subtitle="Cliquez sur une réponse pour rédiger et envoyer votre réponse au prospect">
        <Btn variant="blue" onClick={() => setShow(true)} data-testid="add-reply-btn"><Plus className="w-4 h-4" /> Enregistrer une réponse</Btn>
      </PageHeader>
      {rows.length === 0 ? <Card><Empty text="Aucune réponse enregistrée." /></Card> :
        <div className="space-y-3">
          {rows.map((r) => (
            <Card key={r.id} onClick={() => openReply(r)} role="button" tabIndex={0}
              className="p-5 animate-fade-in cursor-pointer hover:border-blue-300 hover:shadow-md transition-all" data-testid={`reply-${r.id}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-heading font-semibold text-slate-800 flex items-center gap-2"><MessageSquare className="w-4 h-4 text-blue-600" /> {r.company_name}</span>
                <div className="flex items-center gap-2">
                  {r.handled && <span className="text-xs px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 font-medium flex items-center gap-1" data-testid={`reply-handled-${r.id}`}><CheckCircle2 className="w-3 h-3" /> Répondu</span>}
                  <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-700 font-medium">{r.category}</span>
                </div>
              </div>
              <p className="text-sm text-slate-600 italic border-l-2 border-slate-200 pl-3 mb-3 line-clamp-2">{r.text}</p>
              {r.analysis && (
                <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                  <span>Sentiment : <span className={sentColor[r.analysis.sentiment] || ""}>{r.analysis.sentiment}</span></span>
                  <span>Intérêt : {r.analysis.interest_level}</span>
                  <span>Action : {r.analysis.next_action}</span>
                  <span className="ml-auto text-blue-600 font-medium">Rédiger une réponse →</span>
                </div>
              )}
            </Card>
          ))}
        </div>}

      {/* Vue détail + rédaction de réponse */}
      <Dialog open={!!active} onOpenChange={(o) => !o && setActive(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          {active && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2"><MessageSquare className="w-5 h-5 text-blue-600" /> {active.company_name}
                  <span className="text-xs px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium">{active.category}</span>
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <div className="text-xs uppercase text-slate-400 mb-1">Réponse reçue du prospect</div>
                  <p className="text-sm text-slate-700 italic bg-slate-50 border border-slate-100 rounded-lg p-3 whitespace-pre-wrap" data-testid="reply-detail-text">{active.text}</p>
                </div>
                {active.analysis && (
                  <div className="grid grid-cols-2 gap-3 text-xs bg-blue-50/50 border border-blue-100 rounded-lg p-3">
                    <div><span className="text-slate-400">Sentiment</span><div className={`font-medium ${sentColor[active.analysis.sentiment] || ""}`}>{active.analysis.sentiment}</div></div>
                    <div><span className="text-slate-400">Niveau d'intérêt</span><div className="font-medium text-slate-700">{active.analysis.interest_level}</div></div>
                    <div className="col-span-2"><span className="text-slate-400">Action recommandée</span><div className="font-medium text-slate-700">{active.analysis.next_action}</div></div>
                  </div>
                )}
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs uppercase text-slate-400 flex items-center gap-1"><Mail className="w-3.5 h-3.5" /> Votre réponse à {active.recipient || "destinataire inconnu"}</label>
                    {active.analysis?.suggested_reply && (
                      <button onClick={() => setResponse(active.analysis.suggested_reply)} className="text-xs text-blue-600 flex items-center gap-1" data-testid="use-suggestion-btn"><Sparkles className="w-3 h-3" /> Proposition IA</button>
                    )}
                  </div>
                  <Textarea rows={8} value={response} onChange={(e) => setResponse(e.target.value)} placeholder="Rédigez votre réponse..." data-testid="response-input" />
                  <p className="text-[11px] text-amber-600 mt-1">Envoi en mode simulation — aucun email réel n'est transmis.</p>
                  {active.handled && active.responded_at && (
                    <p className="text-[11px] text-emerald-600 mt-1">Déjà répondu le {new Date(active.responded_at).toLocaleString("fr-FR")} → {active.responded_to}</p>
                  )}
                </div>
              </div>
              <DialogFooter>
                <Btn variant="secondary" onClick={() => setActive(null)}>Fermer</Btn>
                <Btn variant="blue" onClick={sendResponse} disabled={sending} data-testid="send-response-btn">
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Envoyer la réponse
                </Btn>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Enregistrer une réponse */}
      <Dialog open={show} onOpenChange={setShow}>
        <DialogContent>
          <DialogHeader><DialogTitle>Enregistrer une réponse</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <Select className="w-full" value={form.company_id} onChange={(e) => setForm({ ...form, company_id: e.target.value })} data-testid="reply-company-select">
              <option value="">Choisir une entreprise...</option>
              {companies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </Select>
            <Textarea rows={5} placeholder="Collez le texte de la réponse reçue..." value={form.text} onChange={(e) => setForm({ ...form, text: e.target.value })} data-testid="reply-text-input" />
          </div>
          <DialogFooter>
            <Btn variant="secondary" onClick={() => setShow(false)}>Annuler</Btn>
            <Btn variant="blue" onClick={analyze} data-testid="analyze-reply-btn">Analyser avec l'IA</Btn>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
