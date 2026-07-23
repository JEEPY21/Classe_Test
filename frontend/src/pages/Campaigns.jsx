import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Input, Select, Textarea } from "@/components/kit";
import StatusBadge from "@/components/StatusBadge";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Plus, Megaphone } from "lucide-react";

const STATUSES = ["Brouillon", "En préparation", "Active", "En pause", "Terminée", "Archivée"];

export default function Campaigns() {
  const [rows, setRows] = useState(null);
  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ name: "", sector: "Conseil", geo_zone: "Île-de-France", status: "Brouillon", daily_volume: 5, offer: "Audit gratuit du système d'acquisition digitale", description: "" });
  const load = () => client.get("/campaigns").then((r) => setRows(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const save = async () => {
    if (!form.name) return toast.error("Nom requis");
    await client.post("/campaigns", form); toast.success("Campagne créée"); setShow(false); load();
  };
  const changeStatus = async (c, status) => { await client.put(`/campaigns/${c.id}`, { ...c, status }); load(); };
  if (!rows) return <Loading />;
  return (
    <div>
      <PageHeader title="Campagnes" subtitle="Organisez votre prospection par segment">
        <Btn variant="blue" onClick={() => setShow(true)} data-testid="add-campaign-btn"><Plus className="w-4 h-4" /> Nouvelle campagne</Btn>
      </PageHeader>
      {rows.length === 0 ? <Card><Empty text="Aucune campagne." /></Card> :
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {rows.map((c) => (
            <Card key={c.id} className="p-5 animate-fade-in" data-testid={`campaign-${c.id}`}>
              <div className="flex items-start justify-between mb-3">
                <Megaphone className="w-5 h-5 text-blue-600" />
                <StatusBadge status={c.status} />
              </div>
              <h3 className="font-heading font-semibold text-slate-800">{c.name}</h3>
              <div className="text-xs text-slate-500 mt-1">{c.sector} · {c.geo_zone}</div>
              <div className="text-xs text-slate-400 mt-3 space-y-1">
                <div>Offre : {c.offer}</div>
                <div>Volume/jour : {c.daily_volume} · Relances : J+{(c.followup_sequence || []).join(", J+")}</div>
                <div>{c.prospect_count} prospects · {c.sent_count} envoyés</div>
              </div>
              <div className="mt-4">
                <Select value={c.status} onChange={(e) => changeStatus(c, e.target.value)} className="w-full text-xs">
                  {STATUSES.map((s) => <option key={s}>{s}</option>)}
                </Select>
              </div>
            </Card>
          ))}
        </div>}
      <Dialog open={show} onOpenChange={setShow}>
        <DialogContent>
          <DialogHeader><DialogTitle>Nouvelle campagne</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs text-slate-500">Nom *</label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="campaign-name-input" /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs text-slate-500">Secteur</label><Input value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })} /></div>
              <div><label className="text-xs text-slate-500">Zone</label><Input value={form.geo_zone} onChange={(e) => setForm({ ...form, geo_zone: e.target.value })} /></div>
            </div>
            <div><label className="text-xs text-slate-500">Description</label><Textarea rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Btn variant="secondary" onClick={() => setShow(false)}>Annuler</Btn>
            <Btn variant="blue" onClick={save} data-testid="save-campaign-btn">Créer</Btn>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
