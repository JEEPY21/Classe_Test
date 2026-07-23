import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Input, Select, Textarea, ScoreBadge } from "@/components/kit";
import StatusBadge, { ALL_STATUSES } from "@/components/StatusBadge";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Search, Upload, Download, Trash2, Eye } from "lucide-react";

const SECTORS = ["Conseil", "Cabinet juridique", "Cabinet comptable", "Cabinet administratif",
  "Ressources humaines", "Consultant indépendant", "Agence", "Services aux entreprises"];

export default function Companies() {
  const nav = useNavigate();
  const [rows, setRows] = useState(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [sector, setSector] = useState("");
  const [selected, setSelected] = useState([]);
  const [bulkStatus, setBulkStatus] = useState("Qualifié");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", sector: "Conseil", city: "", postal_code: "", website: "", generic_email: "", phone: "" });
  const fileRef = useRef();

  const load = () => {
    const params = {};
    if (search) params.search = search;
    if (status) params.status = status;
    if (sector) params.sector = sector;
    client.get("/companies", { params }).then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  };
  useEffect(() => { load(); }, [status, sector]);
  useEffect(() => { const t = setTimeout(load, 400); return () => clearTimeout(t); }, [search]);

  const add = async () => {
    if (!form.name) return toast.error("Le nom est requis");
    try {
      await client.post("/companies", form);
      toast.success("Entreprise ajoutée");
      setShowAdd(false);
      setForm({ name: "", sector: "Conseil", city: "", postal_code: "", website: "", generic_email: "", phone: "" });
      load();
    } catch (e) { toast.error(apiError(e)); }
  };

  const importCsv = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const { data } = await client.post("/companies/import-csv", fd);
      toast.success(`${data.imported} importées, ${data.duplicates} doublons ignorés`);
      load();
    } catch (err) { toast.error(apiError(err)); }
    e.target.value = "";
  };

  const exportCsv = async () => {
    const { data } = await client.get("/companies-export/csv", { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([data]));
    const a = document.createElement("a");
    a.href = url; a.download = "prospectia_entreprises.csv"; a.click();
  };

  const applyBulk = async () => {
    await client.post("/companies/bulk-status", { data: { ids: selected, status: bulkStatus } });
    toast.success(`${selected.length} entreprise(s) mise(s) à jour`);
    setSelected([]); load();
  };

  const del = async (id, e) => {
    e.stopPropagation();
    await client.delete(`/companies/${id}`);
    toast.success("Supprimée"); load();
  };

  const toggle = (id) => setSelected((s) => s.includes(id) ? s.filter((x) => x !== id) : [...s, id]);

  if (!rows) return <Loading />;

  return (
    <div>
      <PageHeader title="Entreprises" subtitle={`${rows.length} entreprise(s) dans votre base de prospects`}>
        <input ref={fileRef} type="file" accept=".csv" hidden onChange={importCsv} />
        <Btn variant="secondary" onClick={() => fileRef.current.click()} data-testid="import-csv-btn"><Upload className="w-4 h-4" /> Importer CSV</Btn>
        <Btn variant="secondary" onClick={exportCsv} data-testid="export-csv-btn"><Download className="w-4 h-4" /> Exporter</Btn>
        <Btn variant="blue" onClick={() => setShowAdd(true)} data-testid="add-company-btn"><Plus className="w-4 h-4" /> Ajouter</Btn>
      </PageHeader>

      <Card className="p-4 mb-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input placeholder="Rechercher (nom, ville, email)..." value={search} onChange={(e) => setSearch(e.target.value)} className="pl-9" data-testid="company-search" />
          </div>
          <Select value={status} onChange={(e) => setStatus(e.target.value)} data-testid="filter-status">
            <option value="">Tous les statuts</option>
            {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <Select value={sector} onChange={(e) => setSector(e.target.value)} data-testid="filter-sector">
            <option value="">Tous les secteurs</option>
            {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
        </div>
        {selected.length > 0 && (
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-100">
            <span className="text-sm text-slate-600">{selected.length} sélectionnée(s)</span>
            <Select value={bulkStatus} onChange={(e) => setBulkStatus(e.target.value)}>
              {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
            <Btn variant="secondary" onClick={applyBulk} data-testid="bulk-apply-btn">Appliquer le statut</Btn>
          </div>
        )}
      </Card>

      <Card className="overflow-hidden">
        {rows.length === 0 ? <Empty text="Aucune entreprise. Ajoutez-en une ou importez un CSV." /> : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 text-xs uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 w-8"></th>
                  <th className="px-4 py-3 text-left font-medium">Entreprise</th>
                  <th className="px-4 py-3 text-left font-medium">Secteur</th>
                  <th className="px-4 py-3 text-left font-medium">Ville</th>
                  <th className="px-4 py-3 text-left font-medium">Score</th>
                  <th className="px-4 py-3 text-left font-medium">Statut</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50 transition-colors cursor-pointer" onClick={() => nav(`/entreprises/${c.id}`)} data-testid={`company-row-${c.id}`}>
                    <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                      <input type="checkbox" checked={selected.includes(c.id)} onChange={() => toggle(c.id)} className="rounded border-slate-300" />
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-800">{c.name}{c.is_demo && <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-400 rounded">démo</span>}</td>
                    <td className="px-4 py-3 text-slate-600">{c.sector}</td>
                    <td className="px-4 py-3 text-slate-600">{c.city}</td>
                    <td className="px-4 py-3"><ScoreBadge score={c.score} /></td>
                    <td className="px-4 py-3"><StatusBadge status={c.status} /></td>
                    <td className="px-4 py-3 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="flex items-center gap-1 justify-end">
                        <button onClick={() => nav(`/entreprises/${c.id}`)} className="p-1.5 text-slate-400 hover:text-blue-600 transition-colors"><Eye className="w-4 h-4" /></button>
                        <button onClick={(e) => del(c.id, e)} className="p-1.5 text-slate-400 hover:text-red-600 transition-colors" data-testid={`delete-company-${c.id}`}><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Dialog open={showAdd} onOpenChange={setShowAdd}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Ajouter une entreprise</DialogTitle></DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><label className="text-xs text-slate-500">Nom *</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="company-name-input" /></div>
            <div><label className="text-xs text-slate-500">Secteur</label><Select className="w-full" value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })}>{SECTORS.map((s) => <option key={s}>{s}</option>)}</Select></div>
            <div><label className="text-xs text-slate-500">Ville</label><Input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Code postal</label><Input value={form.postal_code} onChange={(e) => setForm({ ...form, postal_code: e.target.value })} /></div>
            <div><label className="text-xs text-slate-500">Téléphone</label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
            <div className="col-span-2"><label className="text-xs text-slate-500">Site internet</label><Input value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} placeholder="https://..." /></div>
            <div className="col-span-2"><label className="text-xs text-slate-500">Email générique</label><Input value={form.generic_email} onChange={(e) => setForm({ ...form, generic_email: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Btn variant="secondary" onClick={() => setShowAdd(false)}>Annuler</Btn>
            <Btn variant="blue" onClick={add} data-testid="save-company-btn">Enregistrer</Btn>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
