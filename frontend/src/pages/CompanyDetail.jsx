import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import client, { apiError } from "@/lib/api";
import { Card, Btn, Loading, Input, Select, Textarea, ScoreBadge } from "@/components/kit";
import StatusBadge, { ALL_STATUSES } from "@/components/StatusBadge";
import { toast } from "sonner";
import { ArrowLeft, Sparkles, Mail, Save, Loader2, Globe, Phone, MapPin, Plus, AlertCircle } from "lucide-react";

const BLOCK_COLORS = {
  emerald: "text-emerald-700", amber: "text-amber-700", blue: "text-blue-700", slate: "text-slate-600",
};
function Block({ title, items, color = "slate", italic }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <div className={`text-xs uppercase font-medium mb-1 ${BLOCK_COLORS[color]}`}>{title}</div>
      <ul className={`list-disc list-inside space-y-0.5 text-slate-700 ${italic ? "italic" : ""}`}>
        {items.map((x, i) => <li key={i}>{x}</li>)}
      </ul>
    </div>
  );
}

export default function CompanyDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [c, setC] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [genLoading, setGenLoading] = useState(false);
  const [email, setEmail] = useState(null);
  const [tone, setTone] = useState("consultative");
  const [showContact, setShowContact] = useState(false);
  const [contact, setContact] = useState({ first_name: "", last_name: "", role: "", email: "", decision_level: "dirigeant" });

  const load = () => client.get(`/companies/${id}`).then((r) => setC(r.data)).catch((e) => toast.error(apiError(e)));
  useEffect(() => { load(); }, [id]);

  const analyze = async () => {
    setAnalyzing(true);
    try { await client.post(`/companies/${id}/analyze`); toast.success("Analyse IA terminée"); load(); }
    catch (e) { toast.error(apiError(e)); } finally { setAnalyzing(false); }
  };

  const saveStatus = async (status) => {
    await client.put(`/companies/${id}`, { ...c, status });
    toast.success("Statut mis à jour"); load();
  };

  const generate = async () => {
    setGenLoading(true);
    try {
      const { data } = await client.post("/emails/generate", { data: { company_id: id, tone } });
      setEmail({ ...data.result, problem: data.problem, service: data.service });
    } catch (e) { toast.error(apiError(e)); } finally { setGenLoading(false); }
  };

  const sendToValidation = async () => {
    await client.post("/emails", {
      company_id: id, subject: email.subject, body: email.body, tone,
      problem: email.problem, service: email.service, status: "À valider",
    });
    toast.success("Email ajouté à la file de validation");
    setEmail(null); load();
  };

  const addContact = async () => {
    if (!contact.first_name) return toast.error("Prénom requis");
    await client.post("/contacts", { ...contact, company_id: id });
    toast.success("Contact ajouté"); setShowContact(false);
    setContact({ first_name: "", last_name: "", role: "", email: "", decision_level: "dirigeant" });
    load();
  };

  if (!c) return <Loading />;
  const a = c.analysis;
  const sd = c.score_detail;

  return (
    <div className="max-w-5xl">
      <button onClick={() => nav("/entreprises")} className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 mb-4 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Retour aux entreprises
      </button>

      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="font-heading text-2xl font-bold text-slate-900 tracking-tight">{c.name}</h1>
            <ScoreBadge score={c.score} />
            {c.is_demo && <span data-testid="demo-badge" className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 border border-slate-200 font-medium">Démo</span>}
          </div>
          <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-slate-500">
            <span>{c.sector}</span>
            {c.city && <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" /> {c.city} {c.postal_code}</span>}
            {c.website && <a href={c.website} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-600 hover:underline"><Globe className="w-3.5 h-3.5" /> Site</a>}
            {c.phone && <span className="flex items-center gap-1"><Phone className="w-3.5 h-3.5" /> {c.phone}</span>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={c.status} onChange={(e) => saveStatus(e.target.value)} data-testid="detail-status-select">
            {ALL_STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </Select>
          <Btn variant="blue" onClick={analyze} disabled={analyzing} data-testid="analyze-btn">
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
            {analyzing ? "Analyse..." : "Analyser (IA)"}
          </Btn>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Analysis */}
          <Card className="p-6">
            <h3 className="font-heading font-semibold text-slate-800 mb-4 flex items-center gap-2"><Sparkles className="w-4 h-4 text-blue-600" /> Analyse du dossier</h3>
            {!a ? <p className="text-sm text-slate-400">Aucune analyse. Lancez l'analyse IA (basée uniquement sur les données du dossier, sans vérification extérieure).</p> :
              a.insufficient ? (
                <div className="text-sm">
                  <div className="flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
                    <AlertCircle className="w-4 h-4" /> Analyse insuffisante pour produire un diagnostic fiable.
                  </div>
                  {(a.missing_or_unverified?.length > 0) && <Block title="Informations à rechercher" items={a.missing_or_unverified} color="amber" />}
                  {(a.questions_to_ask?.length > 0) && <Block title="Questions à poser au prospect" items={a.questions_to_ask} color="blue" />}
                </div>
              ) : (
              <div className="space-y-5 text-sm">
                <div><div className="text-xs uppercase text-slate-400 mb-1">Résumé prudent</div><p className="text-slate-700">{a.summary}</p></div>

                <Block title="A. Données disponibles (faits du dossier)" items={a.data_available || a.problems} color="emerald" />
                <Block title="B. Informations manquantes ou non vérifiées" items={a.missing_or_unverified} color="amber" />
                <Block title="C. Hypothèses commerciales (conditionnelles)" items={a.hypotheses || a.consequences} color="blue" italic />
                {(a.questions_to_ask?.length > 0) && <Block title="Questions à poser au prospect" items={a.questions_to_ask} color="slate" />}

                <div className="flex flex-wrap gap-4 pt-2 border-t border-slate-100">
                  <div><div className="text-xs uppercase text-slate-400 mb-1">Service potentiel à explorer</div>
                    <span className="inline-block px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 font-medium">{a.potential_service || a.recommended_service || "—"}</span></div>
                  <div><div className="text-xs uppercase text-slate-400 mb-1">Offre d'entrée</div><span className="text-slate-700">{a.entry_offer || "Audit gratuit"}</span></div>
                  <div><div className="text-xs uppercase text-slate-400 mb-1">Confiance</div><span className="text-slate-700 capitalize">{a.confidence}</span></div>
                </div>
                {a.service_condition && <p className="text-xs text-slate-500 italic">Condition : {a.service_condition}</p>}
                {a.prospecting_angle && <div><div className="text-xs uppercase text-slate-400 mb-1">Angle de prospection</div><p className="text-slate-700 italic">{a.prospecting_angle}</p></div>}
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5">{a.reliability_note || "Fiabilité faible — aucune vérification extérieure effectuée."}</div>
              </div>
            )}
          </Card>

          {/* Email generation */}
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-semibold text-slate-800 flex items-center gap-2"><Mail className="w-4 h-4 text-blue-600" /> Génération d'email</h3>
              <div className="flex items-center gap-2">
                <Select value={tone} onChange={(e) => setTone(e.target.value)}>
                  <option value="directe">Directe</option>
                  <option value="consultative">Consultative</option>
                  <option value="chaleureuse et professionnelle">Chaleureuse</option>
                </Select>
                <Btn variant="secondary" onClick={generate} disabled={genLoading || !a} data-testid="generate-email-btn">
                  {genLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Générer
                </Btn>
              </div>
            </div>
            {!a && <p className="text-sm text-amber-600">Analyse insuffisante — lancez d'abord l'analyse IA.</p>}
            {email && (
              <div className="space-y-3">
                <div><label className="text-xs text-slate-500">Objet</label><Input value={email.subject} onChange={(e) => setEmail({ ...email, subject: e.target.value })} data-testid="email-subject-input" /></div>
                <div><label className="text-xs text-slate-500">Message</label><Textarea rows={12} value={email.body} onChange={(e) => setEmail({ ...email, body: e.target.value })} data-testid="email-body-input" /></div>
                <div className="flex gap-2">
                  <Btn variant="secondary" onClick={generate}><Sparkles className="w-4 h-4" /> Régénérer</Btn>
                  <Btn variant="blue" onClick={sendToValidation} data-testid="send-validation-btn"><Save className="w-4 h-4" /> Envoyer en validation</Btn>
                </div>
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-6">
          {/* Score detail */}
          <Card className="p-6">
            <h3 className="font-heading font-semibold text-slate-800 mb-1">Score commercial</h3>
            {a?.insufficient ? (
              <div className="py-4" data-testid="score-insufficient">
                <div className="text-base font-medium text-amber-700">Analyse insuffisante pour un diagnostic fiable</div>
                <p className="text-xs text-slate-400 mt-2">Complétez le dossier (secteur, site, contact, email…) puis relancez l'analyse pour un score fiable.</p>
              </div>
            ) : c.score === null || c.score === undefined ? (
              <div className="py-4">
                <div className="text-lg font-medium text-slate-400" data-testid="score-not-calculated">Score commercial : non calculé</div>
                <p className="text-xs text-slate-400 mt-2">Lancez l'analyse IA pour obtenir un score provisoire basé sur les données du dossier.</p>
              </div>
            ) : (
              <>
                <div className="text-xs text-slate-500 mb-2">{sd?.score_label || "Score provisoire basé sur les données du dossier"}</div>
                <div className="flex items-center gap-3 mb-2">
                  <div className="text-4xl font-heading font-bold text-slate-900" data-testid="score-value">{c.score}</div>
                  <div className="text-sm text-slate-400">/ 100</div>
                  {sd && <span className="ml-auto text-xs px-2 py-1 rounded-md bg-slate-100 text-slate-600">{sd.recommendation}</span>}
                </div>
                <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 mb-3">
                  {sd?.reliability || "Fiabilité faible — aucune vérification extérieure effectuée."}
                </div>
                {sd?.breakdown && (
                  <div className="space-y-1.5 text-xs">
                    {Object.entries(sd.breakdown).map(([k, v]) => (
                      <div key={k} className="flex items-center justify-between">
                        <span className="text-slate-500 capitalize">{k.replace(/_/g, " ")}</span>
                        <span className="font-medium text-slate-700">{v}</span>
                      </div>
                    ))}
                  </div>
                )}
                {sd?.explanation && <p className="text-xs text-slate-500 mt-3 pt-3 border-t border-slate-100">{sd.explanation}</p>}
                {(sd?.data_used?.length > 0) && <div className="mt-3"><div className="text-[10px] uppercase text-slate-400 mb-1">Données utilisées</div><ul className="list-disc list-inside text-xs text-slate-600">{sd.data_used.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                {(sd?.data_absent?.length > 0) && <div className="mt-2"><div className="text-[10px] uppercase text-slate-400 mb-1">Données absentes (limitent le score)</div><ul className="list-disc list-inside text-xs text-slate-600">{sd.data_absent.map((x, i) => <li key={i}>{x}</li>)}</ul></div>}
                {sd?.limits && <p className="text-xs text-slate-400 mt-2">Limites : {sd.limits}</p>}
                <p className="text-[11px] text-slate-400 mt-2">Recherche extérieure : {sd?.external_search_done ? "effectuée" : "non effectuée"}</p>
              </>
            )}
          </Card>

          {/* Vérifications externes */}
          <Card className="p-6" data-testid="external-verifications-card">
            <h3 className="font-heading font-semibold text-slate-800 mb-3 flex items-center gap-2"><AlertCircle className="w-4 h-4 text-amber-500" /> Vérifications externes</h3>
            <ul className="space-y-2 text-xs">
              <li className="flex items-start justify-between gap-2">
                <span className="text-slate-500">Identité légale (SIREN / Sirene)</span>
                <span className={c.siren ? "text-emerald-600 font-medium text-right" : "text-slate-400 text-right"} data-testid="verif-sirene">{c.siren ? `Confirmée · ${c.siren}` : "Non renseignée"}</span>
              </li>
              <li className="flex items-start justify-between gap-2" data-testid="verif-ordre">
                <span className="text-slate-500">Confirmation Ordre des Experts-Comptables</span>
                <span className="text-amber-600 text-right">Non disponible</span>
              </li>
              <li className="flex items-start justify-between gap-2" data-testid="verif-site-content">
                <span className="text-slate-500">Contenu du site officiel (analyse IA)</span>
                {c.analysis_site_context?.used
                  ? <span className="text-emerald-600 text-right">Lu · {c.analysis_site_context.pages_used?.length || 0} page(s)</span>
                  : <span className="text-slate-400 text-right">{c.website ? (c.analysis_site_context?.robots_blocked ? "Bloqué (robots.txt)" : "Non lu") : "Aucun site"}</span>}
              </li>
            </ul>
            {c.analysis_site_context?.used && (
              <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100" data-testid="site-content-pages">
                Pages lues : {(c.analysis_site_context.pages_used || []).join(", ")}
                {c.analysis_site_context.collected_at && <> · le {new Date(c.analysis_site_context.collected_at).toLocaleString("fr-FR")}</>}
              </p>
            )}
            {c.analysis_site_context && !c.analysis_site_context.used && c.analysis_site_context.note && (
              <p className="text-[11px] text-amber-600 mt-2">{c.analysis_site_context.note}</p>
            )}
            <p className="text-[11px] text-slate-400 mt-3 pt-3 border-t border-slate-100">
              L'annuaire du CNOEC n'est pas exploitable automatiquement (droit d'auteur, robots.txt, RGPD). Cette confirmation reste donc « non disponible » tant qu'aucune source autorisée n'est activée.
            </p>
          </Card>
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-heading font-semibold text-slate-800">Contacts</h3>
              <button onClick={() => setShowContact(!showContact)} className="text-blue-600 hover:text-blue-700"><Plus className="w-4 h-4" /></button>
            </div>
            {showContact && (
              <div className="space-y-2 mb-4 pb-4 border-b border-slate-100">
                <Input placeholder="Prénom" value={contact.first_name} onChange={(e) => setContact({ ...contact, first_name: e.target.value })} data-testid="contact-firstname" />
                <Input placeholder="Nom" value={contact.last_name} onChange={(e) => setContact({ ...contact, last_name: e.target.value })} />
                <Input placeholder="Fonction" value={contact.role} onChange={(e) => setContact({ ...contact, role: e.target.value })} />
                <Input placeholder="Email" value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} />
                <Btn variant="blue" onClick={addContact} className="w-full" data-testid="save-contact-btn">Ajouter le contact</Btn>
              </div>
            )}
            {(c.contacts || []).length === 0 ? <p className="text-sm text-slate-400">Aucun contact.</p> :
              c.contacts.map((ct) => (
                <div key={ct.id} className="py-2 border-b border-slate-50 last:border-0">
                  <div className="text-sm font-medium text-slate-800">{ct.first_name} {ct.last_name}</div>
                  <div className="text-xs text-slate-500">{ct.role}</div>
                  {ct.email && <div className="text-xs text-blue-600">{ct.email}</div>}
                </div>
              ))}
          </Card>
        </div>
      </div>
    </div>
  );
}
