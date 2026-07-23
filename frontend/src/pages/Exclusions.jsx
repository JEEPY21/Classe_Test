import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Input } from "@/components/kit";
import { toast } from "sonner";
import { Plus, Trash2, Ban } from "lucide-react";

export default function Exclusions() {
  const [rows, setRows] = useState(null);
  const [form, setForm] = useState({ email: "", company: "", reason: "" });
  const load = () => client.get("/exclusions").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const add = async () => {
    if (!form.email) return toast.error("Email requis");
    await client.post("/exclusions", { data: form }); toast.success("Ajouté à la liste d'exclusion");
    setForm({ email: "", company: "", reason: "" }); load();
  };
  const del = async (id) => { await client.delete(`/exclusions/${id}`); load(); };
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Liste d'exclusion" subtitle="« Ne plus contacter » — vérifiée avant chaque envoi" />
      <Card className="p-4 mb-4">
        <div className="flex flex-col md:flex-row gap-3">
          <Input placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="exclusion-email" />
          <Input placeholder="Entreprise" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <Input placeholder="Motif" value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          <Btn variant="blue" onClick={add} data-testid="add-exclusion-btn"><Plus className="w-4 h-4" /> Ajouter</Btn>
        </div>
      </Card>
      <Card className="overflow-hidden">
        {rows.length === 0 ? <Empty text="Aucune exclusion." /> : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
              <tr><th className="px-4 py-3 text-left font-medium">Email</th><th className="px-4 py-3 text-left font-medium">Entreprise</th><th className="px-4 py-3 text-left font-medium">Motif</th><th className="px-4 py-3 text-left font-medium">Source</th><th className="px-4 py-3"></th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((x) => (
                <tr key={x.id} className="hover:bg-slate-50" data-testid={`exclusion-${x.id}`}>
                  <td className="px-4 py-3 text-slate-800 flex items-center gap-2"><Ban className="w-3.5 h-3.5 text-red-500" /> {x.email}</td>
                  <td className="px-4 py-3 text-slate-600">{x.company}</td>
                  <td className="px-4 py-3 text-slate-600">{x.reason}</td>
                  <td className="px-4 py-3 text-slate-400 text-xs">{x.source}</td>
                  <td className="px-4 py-3 text-right"><button onClick={() => del(x.id)} className="text-slate-400 hover:text-red-600"><Trash2 className="w-4 h-4" /></button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
