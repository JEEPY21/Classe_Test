import React, { useEffect, useState } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Input, Textarea, Select } from "@/components/kit";
import { toast } from "sonner";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

function Field({ label, children }) {
  return <div><label className="text-xs text-slate-500 block mb-1">{label}</label>{children}</div>;
}

export default function Settings() {
  const [s, setS] = useState(null);
  const load = () => client.get("/settings").then((r) => setS(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, []);
  const save = async (section, data) => {
    try { await client.put("/settings", { data: { [section]: data } }); toast.success("Paramètres enregistrés"); load(); }
    catch (e) { toast.error(apiError(e)); }
  };
  if (!s) return <Loading />;
  const upd = (section, key, val) => setS({ ...s, [section]: { ...s[section], [key]: val } });

  return (
    <div className="max-w-3xl">
      <PageHeader title="Paramètres" subtitle="Configuration de votre espace de prospection" />
      <Tabs defaultValue="profile">
        <TabsList className="mb-4">
          <TabsTrigger value="profile" data-testid="tab-profile">Profil</TabsTrigger>
          <TabsTrigger value="prospection" data-testid="tab-prospection">Prospection</TabsTrigger>
          <TabsTrigger value="ai" data-testid="tab-ai">IA</TabsTrigger>
          <TabsTrigger value="email" data-testid="tab-email">Email</TabsTrigger>
          <TabsTrigger value="compliance" data-testid="tab-compliance">Conformité</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Card className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Prénom"><Input value={s.profile.first_name} onChange={(e) => upd("profile", "first_name", e.target.value)} /></Field>
              <Field label="Nom"><Input value={s.profile.last_name} onChange={(e) => upd("profile", "last_name", e.target.value)} /></Field>
              <Field label="Entreprise"><Input value={s.profile.company} onChange={(e) => upd("profile", "company", e.target.value)} /></Field>
              <Field label="Email"><Input value={s.profile.email} onChange={(e) => upd("profile", "email", e.target.value)} /></Field>
            </div>
            <Field label="Signature"><Textarea rows={3} value={s.profile.signature} onChange={(e) => upd("profile", "signature", e.target.value)} /></Field>
            <Btn variant="blue" onClick={() => save("profile", s.profile)} data-testid="save-profile-btn">Enregistrer</Btn>
          </Card>
        </TabsContent>

        <TabsContent value="prospection">
          <Card className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Volume quotidien"><Input type="number" value={s.prospection.daily_volume} onChange={(e) => upd("prospection", "daily_volume", +e.target.value)} /></Field>
              <Field label="Score minimal"><Input type="number" value={s.prospection.min_score} onChange={(e) => upd("prospection", "min_score", +e.target.value)} /></Field>
              <Field label="Nombre max de relances"><Input type="number" value={s.prospection.max_followups} onChange={(e) => upd("prospection", "max_followups", +e.target.value)} /></Field>
              <Field label="Délais de relance (jours, ex: 3,7,14)"><Input value={(s.prospection.followup_delays || []).join(",")} onChange={(e) => upd("prospection", "followup_delays", e.target.value.split(",").map(Number).filter(Boolean))} /></Field>
            </div>
            <Btn variant="blue" onClick={() => save("prospection", s.prospection)} data-testid="save-prospection-btn">Enregistrer</Btn>
          </Card>
        </TabsContent>

        <TabsContent value="ai">
          <Card className="p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Fournisseur"><Input value={s.ai.provider} readOnly /></Field>
              <Field label="Modèle"><Input value={s.ai.model} readOnly /></Field>
              <Field label="Langue"><Input value={s.ai.language} onChange={(e) => upd("ai", "language", e.target.value)} /></Field>
              <Field label="Ton"><Input value={s.ai.tone} onChange={(e) => upd("ai", "tone", e.target.value)} /></Field>
            </div>
            <Field label="Instructions de marque personnalisées"><Textarea rows={3} value={s.ai.custom_instructions} onChange={(e) => upd("ai", "custom_instructions", e.target.value)} /></Field>
            <p className="text-xs text-slate-400">Clé IA gérée de manière sécurisée via variable d'environnement (Emergent LLM Key).</p>
            <Btn variant="blue" onClick={() => save("ai", s.ai)} data-testid="save-ai-btn">Enregistrer</Btn>
          </Card>
        </TabsContent>

        <TabsContent value="email">
          <Card className="p-6 space-y-4">
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-700">
              Mode <b>simulation</b> actif : aucun email réel n'est envoyé. Pour un envoi réel, configurez un fournisseur SMTP / Gmail / Brevo (Phase 2).
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Nom expéditeur"><Input value={s.email.sender_name} onChange={(e) => upd("email", "sender_name", e.target.value)} /></Field>
              <Field label="Adresse expéditrice"><Input value={s.email.sender_email} onChange={(e) => upd("email", "sender_email", e.target.value)} /></Field>
              <Field label="Adresse de réponse"><Input value={s.email.reply_to} onChange={(e) => upd("email", "reply_to", e.target.value)} /></Field>
              <Field label="Limite quotidienne"><Input type="number" value={s.email.daily_limit} onChange={(e) => upd("email", "daily_limit", +e.target.value)} /></Field>
            </div>
            <Btn variant="blue" onClick={() => save("email", s.email)} data-testid="save-email-btn">Enregistrer</Btn>
          </Card>
        </TabsContent>

        <TabsContent value="compliance">
          <Card className="p-6 space-y-4">
            <Field label="Durée de conservation (jours)"><Input type="number" value={s.compliance.retention_days} onChange={(e) => upd("compliance", "retention_days", +e.target.value)} /></Field>
            <Field label="Texte d'opposition (désinscription)"><Textarea rows={2} value={s.compliance.opt_out_text} onChange={(e) => upd("compliance", "opt_out_text", e.target.value)} /></Field>
            <Btn variant="blue" onClick={() => save("compliance", s.compliance)} data-testid="save-compliance-btn">Enregistrer</Btn>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
