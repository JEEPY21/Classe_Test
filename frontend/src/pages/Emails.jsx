import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty } from "@/components/kit";
import StatusBadge from "@/components/StatusBadge";
import { toast } from "sonner";

export default function Emails() {
  const [rows, setRows] = useState(null);
  useEffect(() => { client.get("/emails").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e))); }, []);
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Emails" subtitle={`${rows.length} email(s) — suivi des envois (mode simulation)`} />
      <Card className="overflow-hidden">
        {rows.length === 0 ? <Empty text="Aucun email." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
                <tr><th className="px-4 py-3 text-left font-medium">Entreprise</th><th className="px-4 py-3 text-left font-medium">Objet</th><th className="px-4 py-3 text-left font-medium">Statut</th><th className="px-4 py-3 text-left font-medium">Date</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((e) => (
                  <tr key={e.id} className="hover:bg-slate-50 transition-colors" data-testid={`email-row-${e.id}`}>
                    <td className="px-4 py-3 font-medium text-slate-800">{e.company_name}</td>
                    <td className="px-4 py-3 text-slate-600 max-w-md truncate">{e.subject}</td>
                    <td className="px-4 py-3"><StatusBadge status={e.status} /></td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{e.sent_at ? new Date(e.sent_at).toLocaleDateString("fr-FR") : new Date(e.created_at).toLocaleDateString("fr-FR")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
