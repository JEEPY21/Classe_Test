import { useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { UploadCloud, Loader2, Plus, X, ArrowRight, ShieldCheck, FileText } from "lucide-react";
import { toast } from "sonner";

const empty = { identity: { full_name: "", title: "", email: "", phone: "", location: "", links: [] }, summary: "", experiences: [], education: [], skills: [], languages: [] };

export default function Step1CV({ cv, setCv, onNext }) {
  const [uploading, setUploading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const s = cv?.structured || empty;

  const handleFile = async (file) => {
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.uploadCV(fd);
      setCv(data);
      toast.success("CV extrait. Vérifiez et corrigez les informations.");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setUploading(false);
    }
  };

  const update = (patch) => setCv({ ...cv, structured: { ...s, ...patch } });
  const updateIdentity = (k, v) => update({ identity: { ...s.identity, [k]: v } });

  const save = async (thenNext) => {
    setSaving(true);
    try {
      const { data } = await api.updateCV(cv.id, s);
      setCv(data);
      toast.success("CV enregistré");
      if (thenNext) onNext();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  // ---- experiences ----
  const addExp = () => update({ experiences: [...s.experiences, { id: crypto.randomUUID(), company: "", role: "", location: "", start_date: "", end_date: "", current: false, bullets: [""] }] });
  const setExp = (i, k, v) => { const e = [...s.experiences]; e[i] = { ...e[i], [k]: v }; update({ experiences: e }); };
  const rmExp = (i) => update({ experiences: s.experiences.filter((_, idx) => idx !== i) });
  const setBullet = (ei, bi, v) => { const e = [...s.experiences]; const b = [...e[ei].bullets]; b[bi] = v; e[ei] = { ...e[ei], bullets: b }; update({ experiences: e }); };
  const addBullet = (ei) => { const e = [...s.experiences]; e[ei] = { ...e[ei], bullets: [...e[ei].bullets, ""] }; update({ experiences: e }); };
  const rmBullet = (ei, bi) => { const e = [...s.experiences]; e[ei] = { ...e[ei], bullets: e[ei].bullets.filter((_, idx) => idx !== bi) }; update({ experiences: e }); };

  // ---- education ----
  const addEdu = () => update({ education: [...s.education, { id: crypto.randomUUID(), institution: "", degree: "", field: "", start_date: "", end_date: "" }] });
  const setEdu = (i, k, v) => { const e = [...s.education]; e[i] = { ...e[i], [k]: v }; update({ education: e }); };
  const rmEdu = (i) => update({ education: s.education.filter((_, idx) => idx !== i) });

  // ---- skills / languages ----
  const [skillInput, setSkillInput] = useState("");
  const addSkill = () => { const v = skillInput.trim(); if (v && !s.skills.includes(v)) update({ skills: [...s.skills, v] }); setSkillInput(""); };
  const rmSkill = (i) => update({ skills: s.skills.filter((_, idx) => idx !== i) });
  const addLang = () => update({ languages: [...s.languages, { language: "", level: "" }] });
  const setLang = (i, k, v) => { const l = [...s.languages]; l[i] = { ...l[i], [k]: v }; update({ languages: l }); };
  const rmLang = (i) => update({ languages: s.languages.filter((_, idx) => idx !== i) });

  return (
    <div className="animate-fade-up">
      <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 1</span>
      <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">CV source</h1>
      <p className="text-muted-foreground mt-2 mb-6">Importez votre CV, puis vérifiez et corrigez les informations extraites. Rien ne sera généré sans votre validation.</p>

      {!cv && (
        <label
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
          className={`grain flex flex-col items-center justify-center text-center border-2 border-dashed rounded-2xl p-12 cursor-pointer transition-colors bg-white ${dragOver ? "border-brand bg-brand/[0.03]" : "border-border"}`}
          data-testid="upload-cv-dropzone"
        >
          <input type="file" accept=".pdf,.docx" className="hidden" disabled={uploading}
            onChange={(e) => handleFile(e.target.files[0])} data-testid="upload-cv-input" />
          {uploading ? (
            <><Loader2 className="w-8 h-8 text-brand animate-spin mb-3" /><p className="font-medium">Extraction et structuration en cours…</p></>
          ) : (
            <>
              <UploadCloud className="w-9 h-9 text-brand mb-3" aria-hidden="true" />
              <p className="font-heading font-semibold text-lg">Déposez votre CV ici</p>
              <p className="text-sm text-muted-foreground mt-1">PDF ou DOCX au texte natif (pas de scan image)</p>
            </>
          )}
        </label>
      )}

      {cv && (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-xl px-4 py-3">
            <ShieldCheck className="w-4 h-4 shrink-0" aria-hidden="true" />
            Données extraites de <b className="mx-1">{cv.filename}</b>. Corrigez toute erreur — l'IA ne s'appuiera que sur ce contenu validé.
          </div>

          {/* Identity */}
          <Card title="Identité">
            <div className="grid sm:grid-cols-2 gap-4">
              <Field label="Nom complet"><Input value={s.identity.full_name} onChange={(e) => updateIdentity("full_name", e.target.value)} data-testid="cv-fullname-input" /></Field>
              <Field label="Titre / poste"><Input value={s.identity.title} onChange={(e) => updateIdentity("title", e.target.value)} placeholder="Développeur Fullstack" /></Field>
              <Field label="Email"><Input value={s.identity.email} onChange={(e) => updateIdentity("email", e.target.value)} /></Field>
              <Field label="Téléphone"><Input value={s.identity.phone} onChange={(e) => updateIdentity("phone", e.target.value)} /></Field>
              <Field label="Localisation"><Input value={s.identity.location} onChange={(e) => updateIdentity("location", e.target.value)} placeholder="Paris" /></Field>
            </div>
          </Card>

          <Card title="Profil">
            <Textarea rows={3} value={s.summary} onChange={(e) => update({ summary: e.target.value })} placeholder="Résumé professionnel (facultatif)" />
          </Card>

          {/* Experiences */}
          <Card title="Expériences" action={<AddBtn onClick={addExp} label="Ajouter" testid="add-exp-btn" />}>
            <div className="space-y-4">
              {s.experiences.map((exp, i) => (
                <div key={exp.id || i} className="border border-border rounded-xl p-4 relative">
                  <button onClick={() => rmExp(i)} className="absolute top-3 right-3 text-muted-foreground hover:text-destructive"><X className="w-4 h-4" /></button>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Field label="Poste"><Input value={exp.role} onChange={(e) => setExp(i, "role", e.target.value)} /></Field>
                    <Field label="Entreprise"><Input value={exp.company} onChange={(e) => setExp(i, "company", e.target.value)} /></Field>
                    <Field label="Début"><Input value={exp.start_date} onChange={(e) => setExp(i, "start_date", e.target.value)} placeholder="2021" /></Field>
                    <Field label="Fin"><Input value={exp.end_date} onChange={(e) => setExp(i, "end_date", e.target.value)} placeholder="2024 / présent" /></Field>
                  </div>
                  <Label className="mt-3 block">Réalisations / missions</Label>
                  <div className="space-y-2 mt-1.5">
                    {exp.bullets.map((b, bi) => (
                      <div key={bi} className="flex gap-2">
                        <Textarea rows={1} value={b} onChange={(e) => setBullet(i, bi, e.target.value)} className="min-h-[38px]" />
                        <button onClick={() => rmBullet(i, bi)} className="text-muted-foreground hover:text-destructive shrink-0"><X className="w-4 h-4" /></button>
                      </div>
                    ))}
                    <Button variant="ghost" size="sm" onClick={() => addBullet(i)}><Plus className="w-3.5 h-3.5 mr-1" /> Ajouter une ligne</Button>
                  </div>
                </div>
              ))}
              {s.experiences.length === 0 && <Empty text="Aucune expérience extraite." />}
            </div>
          </Card>

          {/* Education */}
          <Card title="Formation" action={<AddBtn onClick={addEdu} label="Ajouter" testid="add-edu-btn" />}>
            <div className="space-y-3">
              {s.education.map((ed, i) => (
                <div key={ed.id || i} className="border border-border rounded-xl p-4 relative">
                  <button onClick={() => rmEdu(i)} className="absolute top-3 right-3 text-muted-foreground hover:text-destructive"><X className="w-4 h-4" /></button>
                  <div className="grid sm:grid-cols-2 gap-3">
                    <Field label="Diplôme"><Input value={ed.degree} onChange={(e) => setEdu(i, "degree", e.target.value)} /></Field>
                    <Field label="Domaine"><Input value={ed.field} onChange={(e) => setEdu(i, "field", e.target.value)} /></Field>
                    <Field label="Établissement"><Input value={ed.institution} onChange={(e) => setEdu(i, "institution", e.target.value)} /></Field>
                    <Field label="Années"><Input value={ed.end_date} onChange={(e) => setEdu(i, "end_date", e.target.value)} placeholder="2020" /></Field>
                  </div>
                </div>
              ))}
              {s.education.length === 0 && <Empty text="Aucune formation extraite." />}
            </div>
          </Card>

          {/* Skills */}
          <Card title="Compétences">
            <div className="flex gap-2">
              <Input value={skillInput} onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addSkill(); } }}
                placeholder="Ajouter une compétence puis Entrée" data-testid="skill-input" />
              <Button variant="outline" onClick={addSkill}>Ajouter</Button>
            </div>
            <div className="flex flex-wrap gap-2 mt-3">
              {s.skills.map((sk, i) => (
                <Badge key={i} variant="secondary" className="pr-1 gap-1">{sk}
                  <button onClick={() => rmSkill(i)} className="hover:text-destructive"><X className="w-3 h-3" /></button>
                </Badge>
              ))}
              {s.skills.length === 0 && <span className="text-sm text-muted-foreground">Aucune compétence.</span>}
            </div>
          </Card>

          {/* Languages */}
          <Card title="Langues" action={<AddBtn onClick={addLang} label="Ajouter" testid="add-lang-btn" />}>
            <div className="space-y-2">
              {s.languages.map((l, i) => (
                <div key={i} className="flex gap-2">
                  <Input value={l.language} onChange={(e) => setLang(i, "language", e.target.value)} placeholder="Anglais" />
                  <Input value={l.level} onChange={(e) => setLang(i, "level", e.target.value)} placeholder="Courant" />
                  <button onClick={() => rmLang(i)} className="text-muted-foreground hover:text-destructive shrink-0"><X className="w-4 h-4" /></button>
                </div>
              ))}
              {s.languages.length === 0 && <Empty text="Aucune langue extraite." />}
            </div>
          </Card>

          <div className="flex justify-between items-center gap-3 sticky bottom-4 bg-white/80 backdrop-blur-xl border border-border rounded-xl p-3">
            <Button variant="outline" onClick={() => save(false)} disabled={saving} data-testid="save-cv-btn">
              {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Enregistrer
            </Button>
            <Button className="bg-primary" onClick={() => save(true)} disabled={saving} data-testid="cv-next-btn">
              Analyser une offre <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

const Card = ({ title, action, children }) => (
  <div className="border border-border rounded-2xl bg-white p-5 sm:p-6">
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-heading font-semibold text-lg">{title}</h3>
      {action}
    </div>
    {children}
  </div>
);
const Field = ({ label, children }) => (<div><Label className="text-xs text-muted-foreground">{label}</Label><div className="mt-1">{children}</div></div>);
const AddBtn = ({ onClick, label, testid }) => (<Button variant="ghost" size="sm" onClick={onClick} data-testid={testid}><Plus className="w-4 h-4 mr-1" /> {label}</Button>);
const Empty = ({ text }) => (<div className="flex items-center gap-2 text-sm text-muted-foreground"><FileText className="w-4 h-4" /> {text}</div>);
