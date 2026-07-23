import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Input, Textarea, ScoreBadge } from "@/components/kit";
import { toast } from "sonner";
import { Check, X, Clock, Send, Edit3, Loader2 } from "lucide-react";

export default function Validation() {
  const [rows, setRows] = useState(null);
  const [editing, setEditing] = useState({});
  const [busy, setBusy] = useState("");

  const load = () => client.get("/emails", { params: { status: "À valider" } }).then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);

  const act = async (id, action, extra = {}) => {
    setBusy(id + action);
    try {
      const e = editing[id];
      if (e) await client.put(`/emails/${id}`, e);
      await client.post(`/emails/${id}/validate`, { data: { action, ...extra } });
      toast.success(action === "send" ? "Email envoyé (simulation) — relances programmées" : action === "schedule" ? "Email programmé" : "Traité");
      load();
    } catch (err) { toast.error(apiError(err)); } finally { setBusy(""); }
  };

  if (!rows) return <Loading />;

  return (
    <div className="max-w-4xl">
      <PageHeader title="File de validation" subtitle="Aucun premier email n'est envoyé sans votre validation" />
      {rows.length === 0 ? <Card><Empty text="Aucun message en attente de validation." /></Card> :
        <div className="space-y-4">
          {rows.map((m) => {
            const e = editing[m.id] || m;
            return (
              <Card key={m.id} className="p-6 animate-fade-in" data-testid={`validation-card-${m.id}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <span className="font-heading font-semibold text-slate-800">{m.company_name}</span>
                    <ScoreBadge score={m.company_score} />
                  </div>
                  {m.service && <span className="text-xs px-2 py-1 rounded-md bg-blue-50 text-blue-700">{m.service}</span>}
                </div>
                {m.problem && <div className="mb-3 text-xs text-slate-500"><span className="uppercase">Observation :</span> {m.problem}</div>}
                <div className="space-y-2 mb-4">
                  <Input value={e.subject} onChange={(ev) => setEditing({ ...editing, [m.id]: { ...e, subject: ev.target.value } })} data-testid={`val-subject-${m.id}`} />
                  <Textarea rows={9} value={e.body} onChange={(ev) => setEditing({ ...editing, [m.id]: { ...e, body: ev.target.value } })} data-testid={`val-body-${m.id}`} />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Btn variant="success" onClick={() => act(m.id, "send")} disabled={busy.startsWith(m.id)} data-testid={`validate-send-${m.id}`}>
                    {busy === m.id + "send" ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />} Valider et envoyer
                  </Btn>
                  <Btn variant="secondary" onClick={() => act(m.id, "schedule", { scheduled_date: new Date(Date.now() + 86400000).toISOString() })}><Clock className="w-4 h-4" /> Programmer</Btn>
                  <Btn variant="danger" onClick={() => act(m.id, "refuse")} data-testid={`validate-refuse-${m.id}`}><X className="w-4 h-4" /> Refuser</Btn>
                </div>
              </Card>
            );
          })}
        </div>}
    </div>
  );
}
