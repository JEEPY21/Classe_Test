import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty } from "@/components/kit";
import { toast } from "sonner";
import { Briefcase } from "lucide-react";

export default function Services() {
  const [rows, setRows] = useState(null);
  useEffect(() => { client.get("/services").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e))); }, []);
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Offres & services" subtitle="Catalogue proposé aux prospects" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rows.map((s) => (
          <Card key={s.id} className="p-5 animate-fade-in" data-testid={`service-${s.id}`}>
            <Briefcase className="w-5 h-5 text-blue-600 mb-3" />
            <h3 className="font-heading font-semibold text-slate-800 text-sm">{s.name}</h3>
            <p className="text-xs text-slate-500 mt-2">{s.problems_solved}</p>
            <div className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-100">{s.price_range}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}
