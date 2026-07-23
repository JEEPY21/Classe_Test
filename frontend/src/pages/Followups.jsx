import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty } from "@/components/kit";
import StatusBadge from "@/components/StatusBadge";
import { toast } from "sonner";
import { Send, Sparkles, Repeat } from "lucide-react";

export default function Followups() {
  const [rows, setRows] = useState(null);
  const load = () => client.get("/followups").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const send = async (id) => { try { await client.post(`/followups/${id}/send`); toast.success("Relance envoyée (simulation)"); load(); } catch (e) { toast.error(apiError(e)); } };
  const gen = async (id) => { try { await client.post(`/followups/${id}/generate`); toast.success("Relance générée par l'IA"); load(); } catch (e) { toast.error(apiError(e)); } };
  if (!rows) return <Loading />;
  const labels = { 1: "Relance 1 (J+3)", 2: "Relance 2 (J+7)", 3: "Relance finale (J+14)" };
  return (
    <div>
      <PageHeader title="Relances" subtitle="Moteur de relances — arrêt automatique dès qu'un prospect répond" />
      {rows.length === 0 ? <Card><Empty text="Aucune relance programmée." /></Card> :
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
                <tr><th className="px-4 py-3 text-left font-medium">Entreprise</th><th className="px-4 py-3 text-left font-medium">Niveau</th><th className="px-4 py-3 text-left font-medium">Échéance</th><th className="px-4 py-3 text-left font-medium">Statut</th><th className="px-4 py-3"></th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((f) => (
                  <tr key={f.id} className="hover:bg-slate-50 transition-colors" data-testid={`followup-row-${f.id}`}>
                    <td className="px-4 py-3 font-medium text-slate-800">{f.company_name}</td>
                    <td className="px-4 py-3 text-slate-600 flex items-center gap-1.5"><Repeat className="w-3.5 h-3.5 text-blue-500" /> {labels[f.level]}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{new Date(f.due_date).toLocaleDateString("fr-FR")}</td>
                    <td className="px-4 py-3"><StatusBadge status={f.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {f.status === "Programmée" && (
                        <div className="flex items-center gap-1 justify-end">
                          <Btn variant="secondary" onClick={() => gen(f.id)} className="!px-2 !py-1"><Sparkles className="w-3.5 h-3.5" /></Btn>
                          <Btn variant="blue" onClick={() => send(f.id)} className="!px-2 !py-1" data-testid={`send-followup-${f.id}`}><Send className="w-3.5 h-3.5" /></Btn>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>}
    </div>
  );
}
