import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty } from "@/components/kit";
import { toast } from "sonner";
import { FileText } from "lucide-react";

export default function Templates() {
  const [rows, setRows] = useState(null);
  useEffect(() => { client.get("/templates").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e))); }, []);
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Modèles de messages" subtitle="Bibliothèque de modèles avec variables dynamiques" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rows.map((t) => (
          <Card key={t.id} className="p-5 animate-fade-in" data-testid={`template-${t.id}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-heading font-semibold text-slate-800 flex items-center gap-2"><FileText className="w-4 h-4 text-blue-600" /> {t.name}</span>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">{t.type}</span>
            </div>
            <div className="text-xs text-slate-500 mb-2">Objet : {t.subject}</div>
            <pre className="text-xs text-slate-600 whitespace-pre-wrap font-sans bg-slate-50 rounded-lg p-3 max-h-40 overflow-y-auto">{t.content}</pre>
          </Card>
        ))}
      </div>
    </div>
  );
}
