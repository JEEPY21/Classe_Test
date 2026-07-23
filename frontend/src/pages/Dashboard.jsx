import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading } from "@/components/kit";
import { toast } from "sonner";
import {
  BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, LabelList
} from "recharts";
import {
  Users, UserCheck, Mail, MessageSquare, ThumbsUp, CalendarCheck, Trophy, Euro,
  Database, Trash2, TrendingUp, AlertTriangle, Clock
} from "lucide-react";

const COLORS = ["#2563EB", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#EC4899", "#64748B"];

function Kpi({ icon: Icon, label, value, accent = "text-slate-900", testid }) {
  return (
    <Card className="p-5 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs uppercase tracking-wider text-slate-400 font-medium">{label}</div>
          <div data-testid={testid} className={`text-2xl font-heading font-bold mt-2 ${accent}`}>{value}</div>
        </div>
        <Icon className="w-5 h-5 text-slate-300" />
      </div>
    </Card>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [seeding, setSeeding] = useState(false);

  const load = () => client.get("/dashboard").then((r) => setData(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);

  const seed = async () => {
    setSeeding(true);
    try { await client.post("/demo/seed"); toast.success("Données de démonstration créées"); load(); }
    catch (e) { toast.error(apiError(e)); } finally { setSeeding(false); }
  };
  const clearDemo = async () => {
    try { await client.delete("/demo/clear"); toast.success("Données de démonstration supprimées"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };

  if (!data) return <Loading />;
  const k = data.kpis;
  const p = data.priority;
  const eur = (n) => `${(n || 0).toLocaleString("fr-FR")} €`;

  const priorityItems = [
    { label: "Messages à valider", value: p.messages_a_valider, to: "/validation", icon: Clock, color: "text-amber-600" },
    { label: "Prospects à relancer", value: p.prospects_a_relancer, to: "/relances", icon: MessageSquare, color: "text-blue-600" },
    { label: "Réponses positives non traitées", value: p.reponses_positives_non_traitees, to: "/reponses", icon: ThumbsUp, color: "text-emerald-600" },
    { label: "Prospects sans prochaine action", value: p.prospects_sans_action, to: "/entreprises", icon: Users, color: "text-slate-600" },
    { label: "Erreurs d'automatisation", value: p.erreurs_automatisation, to: "/erreurs", icon: AlertTriangle, color: "text-red-600" },
  ];

  return (
    <div>
      <PageHeader title="Tableau de bord" subtitle="Vue d'ensemble de votre activité de prospection">
        <Btn variant="secondary" onClick={clearDemo}><Trash2 className="w-4 h-4" /> Effacer démo</Btn>
        <Btn variant="blue" onClick={seed} disabled={seeding} data-testid="seed-demo-btn">
          <Database className="w-4 h-4" /> {seeding ? "Création..." : "Données de démo"}
        </Btn>
      </PageHeader>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Kpi icon={Users} label="Total prospects" value={k.total_prospects} testid="kpi-total" />
        <Kpi icon={UserCheck} label="Qualifiés" value={k.qualified} accent="text-emerald-600" testid="kpi-qualified" />
        <Kpi icon={Mail} label="Emails envoyés" value={k.emails_sent} testid="kpi-sent" />
        <Kpi icon={Clock} label="À valider" value={k.to_validate} accent="text-amber-600" testid="kpi-validate" />
        <Kpi icon={MessageSquare} label="Réponses" value={k.replies} />
        <Kpi icon={ThumbsUp} label="Réponses positives" value={k.positive_replies} accent="text-emerald-600" />
        <Kpi icon={CalendarCheck} label="Rendez-vous" value={k.appointments} />
        <Kpi icon={Trophy} label="Clients signés" value={k.clients} accent="text-emerald-600" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Kpi icon={Euro} label="CA potentiel" value={eur(k.potential_revenue)} accent="text-blue-600" />
        <Kpi icon={Euro} label="CA signé" value={eur(k.signed_revenue)} accent="text-emerald-600" />
        <Kpi icon={TrendingUp} label="Taux de réponse" value={`${k.response_rate}%`} />
        <Kpi icon={TrendingUp} label="Taux conversion" value={`${k.conversion_rate}%`} accent="text-emerald-600" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="p-6 lg:col-span-1">
          <h3 className="font-heading font-semibold text-slate-800 mb-4">Actions prioritaires aujourd'hui</h3>
          <div className="space-y-2">
            {priorityItems.map((it) => (
              <Link key={it.label} to={it.to} data-testid={`priority-${it.to.slice(1)}`}
                className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-slate-50 transition-colors group">
                <div className="flex items-center gap-3">
                  <it.icon className={`w-4 h-4 ${it.color}`} />
                  <span className="text-sm text-slate-700">{it.label}</span>
                </div>
                <span className={`text-sm font-semibold ${it.value > 0 ? it.color : "text-slate-300"}`}>{it.value}</span>
              </Link>
            ))}
          </div>
        </Card>

        <Card className="p-6 lg:col-span-2">
          <h3 className="font-heading font-semibold text-slate-800 mb-4">Entonnoir de conversion</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={data.funnel} layout="vertical" margin={{ left: 20 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="stage" width={90} tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} />
              <Tooltip cursor={{ fill: "#f1f5f9" }} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {data.funnel.map((e, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                <LabelList dataKey="value" position="right" style={{ fontSize: 12, fill: "#0f172a", fontWeight: 600 }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-heading font-semibold text-slate-800 mb-4">Répartition par statut</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={data.by_status} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={(e) => e.value}>
                {data.by_status.map((e, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card className="p-6">
          <h3 className="font-heading font-semibold text-slate-800 mb-4">Répartition par secteur</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.by_sector}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#475569" }} interval={0} angle={-20} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} allowDecimals={false} />
              <Tooltip cursor={{ fill: "#f1f5f9" }} />
              <Bar dataKey="value" fill="#2563EB" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  );
}
