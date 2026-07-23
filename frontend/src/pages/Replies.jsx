import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Select, Textarea } from "@/components/kit";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, MessageSquare } from "lucide-react";

export default function Replies() {
  const [rows, setRows] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ company_id: "", text: "" });
  const load = () => client.get("/replies").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); client.get("/companies").then((r) => setCompanies(r.data)); }, []);
  const analyze = async () => {
    if (!form.company_id || !form.text) return toast.error("Entreprise et texte requis");
    try { await client.post("/replies", form); toast.success("Réponse analysée par l'IA"); setShow(false); setForm({ company_id: "", text: "" }); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
  if (!rows) return <Loading />;
  const sentColor = { positif: "text-emerald-600", neutre: "text-slate-500", négatif: "text-red-600" };
  return (
    <div>
      <PageHeader title="Réponses" subtitle="Analyse et classification automatique des réponses reçues">
        <Btn variant="blue" onClick={() => setShow(true)} data-testid="add-reply-btn"><Plus className="w-4 h-4" /> Enregistrer une réponse</Btn>
      </PageHeader>
      {rows.length === 0 ? <Card><Empty text="Aucune réponse enregistrée." /></Card> :
        <div className="space-y-3">
          {rows.map((r) => (
            <Card key={r.id} className="p-5 animate-fade-in" data-testid={`reply-${r.id}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-heading font-semibold text-slate-800 flex items-center gap-2"><MessageSquare className="w-4 h-4 text-blue-600" /> {r.company_name}</span>
                <span className="text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-700 font-medium">{r.category}</span>
              </div>
              <p className="text-sm text-slate-600 italic border-l-2 border-slate-200 pl-3 mb-3">{r.text}</p>
              {r.analysis && (
                <div className="flex flex-wrap gap-4 text-xs text-slate-500">
                  <span>Sentiment : <span className={sentColor[r.analysis.sentiment] || ""}>{r.analysis.sentiment}</span></span>
                  <span>Intérêt : {r.analysis.interest_level}</span>
                  <span>Action : {r.analysis.next_action}</span>
                </div>
              )}
            </Card>
          ))}
        </div>}
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
