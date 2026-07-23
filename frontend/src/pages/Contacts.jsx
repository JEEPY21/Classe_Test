import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Loading, Empty, Input } from "@/components/kit";
import { toast } from "sonner";
import { Search, Mail, Phone } from "lucide-react";

export default function Contacts() {
  const [rows, setRows] = useState(null);
  const [search, setSearch] = useState("");
  const load = () => client.get("/contacts", { params: search ? { search } : {} }).then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { const t = setTimeout(load, 300); return () => clearTimeout(t); }, [search]);
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Contacts" subtitle={`${rows.length} contact(s)`} />
      <Card className="p-4 mb-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <Input placeholder="Rechercher un contact..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="contact-search" />
        </div>
      </Card>
      <Card className="overflow-hidden">
        {rows.length === 0 ? <Empty text="Aucun contact." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
                <tr><th className="px-4 py-3 text-left font-medium">Nom</th><th className="px-4 py-3 text-left font-medium">Entreprise</th><th className="px-4 py-3 text-left font-medium">Fonction</th><th className="px-4 py-3 text-left font-medium">Email</th><th className="px-4 py-3 text-left font-medium">Téléphone</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors" data-testid={`contact-row-${c.id}`}>
                    <td className="px-4 py-3 font-medium text-slate-800">{c.first_name} {c.last_name}</td>
                    <td className="px-4 py-3 text-slate-600">{c.company_name}</td>
                    <td className="px-4 py-3 text-slate-600">{c.role}</td>
                    <td className="px-4 py-3">{c.email && <span className="flex items-center gap-1 text-blue-600"><Mail className="w-3.5 h-3.5" /> {c.email}</span>}</td>
                    <td className="px-4 py-3 text-slate-600">{c.phone}</td>
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
