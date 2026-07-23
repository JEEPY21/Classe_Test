import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty } from "@/components/kit";
import { toast } from "sonner";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

export default function Errors() {
  const [rows, setRows] = useState(null);
  const load = () => client.get("/errors").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const resolve = async (id) => { await client.post(`/errors/${id}/resolve`); toast.success("Erreur marquée comme résolue"); load(); };
  if (!rows) return <Loading />;
  return (
    <div className="max-w-3xl">
      <PageHeader title="Centre d'erreurs" subtitle="Aucune donnée n'est perdue silencieusement" />
      {rows.length === 0 ? <Card><Empty text="Aucune erreur enregistrée." /></Card> :
        <div className="space-y-3">
          {rows.map((e) => (
            <Card key={e.id} className={`p-5 ${e.resolved ? "opacity-50" : ""}`} data-testid={`error-${e.id}`}>
              <div className="flex items-start gap-3">
                <AlertTriangle className={`w-5 h-5 flex-shrink-0 ${e.resolved ? "text-slate-400" : "text-red-500"}`} />
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-slate-800 text-sm">{e.type}</span>
                    <span className="text-xs text-slate-400">{new Date(e.created_at).toLocaleString("fr-FR")}</span>
                  </div>
                  <p className="text-sm text-slate-600 mt-1">{e.message}</p>
                  {e.corrective_action && <p className="text-xs text-blue-600 mt-1">Action : {e.corrective_action}</p>}
                </div>
                {!e.resolved && <Btn variant="secondary" onClick={() => resolve(e.id)} className="!px-2 !py-1"><CheckCircle2 className="w-4 h-4" /></Btn>}
              </div>
            </Card>
          ))}
        </div>}
    </div>
  );
}
