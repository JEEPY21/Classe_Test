import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty } from "@/components/kit";
import { toast } from "sonner";
import { Bot, User } from "lucide-react";

export default function Activity() {
  const [rows, setRows] = useState(null);
  useEffect(() => { client.get("/activity").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e))); }, []);
  if (!rows) return <Loading />;
  return (
    <div className="max-w-3xl">
      <PageHeader title="Journal d'activité" subtitle="Traçabilité complète des actions" />
      <Card className="p-2">
        {rows.length === 0 ? <Empty text="Aucune activité." /> : (
          <div className="divide-y divide-slate-100">
            {rows.map((l) => (
              <div key={l.id} className="flex items-start gap-3 px-4 py-3" data-testid={`activity-${l.id}`}>
                <div className={`mt-0.5 w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${l.auto ? "bg-blue-50 text-blue-600" : "bg-slate-100 text-slate-500"}`}>
                  {l.auto ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-slate-800"><span className="font-medium">{l.action}</span> <span className="text-slate-400">· {l.entity}</span></div>
                  {(l.new_state || l.detail) && <div className="text-xs text-slate-500 mt-0.5">{l.detail || l.new_state}{l.old_state && ` (${l.old_state} → ${l.new_state})`}</div>}
                </div>
                <div className="text-xs text-slate-400 flex-shrink-0">{new Date(l.created_at).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
