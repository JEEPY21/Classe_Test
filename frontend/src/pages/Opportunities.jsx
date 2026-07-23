import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty } from "@/components/kit";
import { toast } from "sonner";

const STAGES = ["Intérêt détecté", "Qualification", "Rendez-vous planifié", "Rendez-vous réalisé", "Besoin confirmé", "Proposition à préparer", "Proposition envoyée", "Négociation", "Gagnée", "Perdue"];

export default function Opportunities() {
  const [rows, setRows] = useState(null);
  const load = () => client.get("/opportunities").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const move = async (o, stage) => { await client.put(`/opportunities/${o.id}`, { data: { stage } }); load(); };
  if (!rows) return <Loading />;
  const byStage = (s) => rows.filter((r) => r.stage === s);
  return (
    <div>
      <PageHeader title="Opportunités" subtitle="Pipeline commercial (Kanban)" />
      {rows.length === 0 ? <Card><Empty text="Aucune opportunité. Elles sont créées automatiquement quand un prospect manifeste de l'intérêt." /></Card> :
        <div className="flex gap-4 overflow-x-auto pb-4">
          {STAGES.filter((s) => byStage(s).length > 0 || ["Intérêt détecté", "Qualification", "Rendez-vous planifié", "Proposition envoyée", "Gagnée"].includes(s)).map((stage) => (
            <div key={stage} className="flex-shrink-0 w-72" data-testid={`stage-${stage}`}>
              <div className="text-xs uppercase tracking-wider text-slate-500 font-medium mb-2 px-1">{stage} <span className="text-slate-300">({byStage(stage).length})</span></div>
              <div className="space-y-2 min-h-[60px]">
                {byStage(stage).map((o) => (
                  <Card key={o.id} className="p-4 animate-fade-in" data-testid={`opp-${o.id}`}>
                    <div className="font-medium text-slate-800 text-sm">{o.company_name}</div>
                    <div className="text-xs text-slate-500 mt-1">{o.service}</div>
                    <div className="flex items-center justify-between mt-2 text-xs">
                      <span className="text-emerald-600 font-medium">{(o.estimated_value || 0).toLocaleString("fr-FR")} €</span>
                      <span className="text-slate-400">{o.probability}%</span>
                    </div>
                    <select value={o.stage} onChange={(e) => move(o, e.target.value)} className="w-full mt-3 text-xs border border-slate-200 rounded px-2 py-1">
                      {STAGES.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>}
    </div>
  );
}
