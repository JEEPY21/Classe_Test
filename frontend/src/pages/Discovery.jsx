import React, { useState, useEffect } from "react";
import client, { apiError } from "@/lib/api";
import { PageHeader, Card, Btn, Loading, Empty, Input, Textarea } from "@/components/kit";
import { toast } from "sonner";
import {
  Radar, Sparkles, Loader2, MapPin, Building2, Check, X, ChevronDown, ChevronUp,
  ShieldCheck, AlertTriangle, Database, FileSearch, Info, Globe, Phone, Wand2, Mail
} from "lucide-react";

const ScoreRing = ({ label, value, max, color }) => (
  <div className="flex flex-col items-center">
    <div className={`text-xl font-heading font-bold ${color}`}>{value}<span className="text-xs font-normal text-slate-400">/{max}</span></div>
    <div className="text-[10px] uppercase text-slate-400 tracking-wide">{label}</div>
  </div>
);

function CandidateCard({ mission, cand, labels, onValidate, onEnrich, enriching, done }) {
  const [open, setOpen] = useState(false);
  const s = cand.scores;
  const pct = (t) => (t.max_total ? Math.round((t.total / t.max_total) * 100) : 0);
  const cColor = (t) => { const p = pct(t); return p >= 80 ? "text-emerald-600" : p >= 50 ? "text-amber-600" : "text-slate-500"; };
  return (
    <Card className="p-5 animate-fade-in" data-testid={`candidate-${cand.siren}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-heading font-semibold text-slate-800">{cand.raison_sociale}</span>
            {cand.is_adjacent && <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-100 text-violet-700 border border-violet-200">Cible adjacente pertinente</span>}
            {cand.is_duplicate && <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">Déjà en base</span>}
            {cand.enriched && <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700 border border-emerald-200 flex items-center gap-1"><Wand2 className="w-2.5 h-2.5" />Enrichi (Google Places)</span>}
          </div>
          <div className="text-xs text-slate-500 mt-1 flex flex-wrap gap-x-3 gap-y-1">
            <span>SIREN {cand.siren}</span>
            <span>NAF {cand.naf} · {cand.naf_label}</span>
            {cand.commune && <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{cand.code_postal} {cand.commune}</span>}
            <span className="text-emerald-600 flex items-center gap-1"><ShieldCheck className="w-3 h-3" />{cand.verification.statut}</span>
            {cand.website && <a href={cand.website} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-600 hover:underline" data-testid={`website-${cand.siren}`}><Globe className="w-3 h-3" />Site</a>}
            {cand.phone && <span className="flex items-center gap-1 text-slate-600" data-testid={`phone-${cand.siren}`}><Phone className="w-3 h-3" />{cand.phone}</span>}
            {cand.email && <a href={`mailto:${cand.email}`} className="flex items-center gap-1 text-blue-600 hover:underline" data-testid={`email-${cand.siren}`}><Mail className="w-3 h-3" />{cand.email}</a>}
          </div>
        </div>
        <div className="flex items-center gap-4 flex-shrink-0">
          <ScoreRing label="Confiance" value={s.confidence.total} max={s.confidence.max_total} color={cColor(s.confidence)} />
          <ScoreRing label="Mission" value={s.match.total} max={s.match.max_total} color={cColor(s.match)} />
          <ScoreRing label="Complétude" value={s.completeness.total} max={s.completeness.max_total} color={cColor(s.completeness)} />
        </div>
      </div>

      <button onClick={() => setOpen(!open)} className="text-xs text-blue-600 mt-3 flex items-center gap-1" data-testid={`toggle-detail-${cand.siren}`}>
        {open ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />} Explication des scores & traçabilité
      </button>

      {open && (
        <div className="mt-3 pt-3 border-t border-slate-100 grid md:grid-cols-3 gap-4 text-xs">
          {[["confidence", "Confiance d'identité"], ["match", "Correspondance mission"], ["completeness", "Complétude"]].map(([k, title]) => (
            <div key={k}>
              <div className="font-medium text-slate-700 mb-1">{title} — {s[k].total}/{s[k].max_total}</div>
              <ul className="space-y-1">
                {Object.entries(s[k].detail).map(([crit, c]) => {
                  const neutral = c.status === "neutral";
                  return (
                    <li key={crit} data-testid={`crit-${cand.siren}-${crit}`}>
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-slate-500">{c.label}</span>
                        {neutral
                          ? <span className="text-slate-400 italic whitespace-nowrap">non évalué</span>
                          : <span className={c.pts > 0 ? "text-emerald-600 font-medium" : "text-slate-300"}>{c.pts}/{c.max}</span>}
                      </div>
                      {c.note && <div className={`text-[10px] ${neutral ? "text-amber-600" : "text-slate-400"}`}>{c.note}</div>}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
          <div className="md:col-span-3 text-slate-500 bg-slate-50 rounded-lg p-3">
            <div className="flex items-center gap-1 font-medium text-slate-600 mb-1"><Info className="w-3.5 h-3.5" /> Traçabilité</div>
            Source : {(cand.source || {}).endpoint} · Collecté le {new Date((cand.source || {}).collected_at).toLocaleString("fr-FR")} · Mode {(cand.source || {}).mode}<br />
            Site officiel : {cand.verification.site_officiel} · Coordonnées : {cand.verification.coordonnees}<br />
            Confirmation Ordre des Experts-Comptables : <span className="text-amber-600">{cand.verification.ordre_experts_comptables || "Non disponible — source non exploitable automatiquement"}</span>
            {cand.verification.coherence && <><br />Cohérence multi-source : <span className={cand.contradictions && cand.contradictions.length ? "text-red-600" : "text-emerald-600"}>{cand.verification.coherence}</span></>}
            {cand.places && <><br />Source secondaire : {cand.places.source} · {cand.places.formattedAddress} · Collecté le {new Date(cand.places.collected_at).toLocaleString("fr-FR")}</>}
            {cand.email_source && <><br />Email : {cand.email ? <span className="text-emerald-600">{cand.email} — trouvé sur {cand.email_source.source_url}</span> : <span className="text-amber-600">{cand.email_source.note || "Email non trouvé sur le site officiel"}</span>}{cand.email_source.collected_at && <> · Collecté le {new Date(cand.email_source.collected_at).toLocaleString("fr-FR")}</>}</>}
            {cand.dirigeants_count > 0 && <> · {cand.dirigeants_count} dirigeant(s) recensé(s) (RGPD : intérêt légitime B2B)</>}
          </div>
        </div>
      )}

      <div className="flex items-center gap-2 mt-4">
        {done !== "reject" && (
          <Btn variant="secondary" onClick={() => onEnrich(cand.siren)} disabled={enriching} data-testid={`enrich-${cand.siren}`}>
            {enriching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Wand2 className="w-4 h-4" />} {cand.enriched ? "Ré-enrichir" : "Enrichir (Google Places)"}
          </Btn>
        )}
        {done === "accept" ? <span className="text-sm text-emerald-600 flex items-center gap-1"><Check className="w-4 h-4" /> Validée et ajoutée au CRM</span>
          : done === "reject" ? <span className="text-sm text-slate-400 flex items-center gap-1"><X className="w-4 h-4" /> Rejetée</span>
          : done === "duplicate" ? <span className="text-sm text-slate-500">Déjà présente en base</span>
          : (
            <>
              <Btn variant="success" onClick={() => onValidate(cand.siren, "accept")} data-testid={`accept-${cand.siren}`}><Check className="w-4 h-4" /> Valider et ajouter au CRM</Btn>
              <Btn variant="danger" onClick={() => onValidate(cand.siren, "reject")} data-testid={`reject-${cand.siren}`}><X className="w-4 h-4" /> Rejeter</Btn>
            </>
          )}
      </div>
    </Card>
  );
}

export default function Discovery() {
  const [text, setText] = useState("Trouver jusqu'à 10 cabinets d'expertise comptable indépendants situés en Île-de-France");
  const [interp, setInterp] = useState(null);
  const [mission, setMission] = useState(null);
  const [labels, setLabels] = useState({});
  const [mode, setMode] = useState("real");
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState({});
  const [missions, setMissions] = useState([]);
  const [enriching, setEnriching] = useState({});

  useEffect(() => {
    client.get("/discovery/score-labels").then((r) => setLabels(r.data)).catch(() => {});
    loadMissions();
  }, []);
  const loadMissions = () => client.get("/discovery/missions").then((r) => setMissions(r.data)).catch(() => {});

  const interpret = async () => {
    setLoading(true); setMission(null); setInterp(null);
    try {
      const { data } = await client.post("/discovery/interpret", { mission_text: text });
      setInterp(data);
      if (!data.recognized) toast.warning("Secteur non reconnu — précisez (ex: comptable, juridique, conseil).");
    } catch (e) { toast.error(apiError(e)); } finally { setLoading(false); }
  };

  const run = async () => {
    setRunning(true); setDone({});
    try {
      const { data } = await client.post("/discovery/run", { interpretation: interp, mode });
      setMission(data);
      if (data.meta?.source_unavailable) toast.error("Source Sirene indisponible — aucune donnée générée par défaut.");
      else if (data.candidates.length === 0) toast.warning("Aucun résultat trouvé pour ces critères.");
      else toast.success(`${data.candidates.length} entreprise(s) réelle(s) trouvée(s)`);
      loadMissions();
    } catch (e) { toast.error(apiError(e)); } finally { setRunning(false); }
  };

  const validate = async (siren, action) => {
    try {
      const { data } = await client.post("/discovery/validate", { mission_id: mission.id, siren, action });
      setDone((d) => ({ ...d, [siren]: data.action }));
      if (action === "accept") toast.success(data.action === "duplicate" ? "Déjà en base (dédup SIREN)" : "Entreprise ajoutée au CRM");
    } catch (e) { toast.error(apiError(e)); }
  };

  const enrich = async (siren) => {
    setEnriching((e) => ({ ...e, [siren]: true }));
    try {
      const { data } = await client.post("/discovery/enrich", { mission_id: mission.id, siren });
      setMission((m) => ({ ...m, candidates: m.candidates.map((c) => (c.siren === siren ? data.candidate : c)) }));
      const u = data.usage || {};
      const c = data.candidate;
      const parts = [];
      if (c.website) parts.push("site");
      if (c.phone) parts.push("téléphone");
      if (c.email) parts.push("email");
      const found = parts.length > 0;
      toast[found ? "success" : "warning"](
        `${found ? "Enrichi (Google Places) : " + parts.join(", ") : "Aucune donnée trouvée"} · ${u.remaining}/${u.cap} requête(s) Google restante(s) ce mois`);
    } catch (e) { toast.error(apiError(e)); }
    finally { setEnriching((e) => ({ ...e, [siren]: false })); }
  };

  return (
    <div className="max-w-5xl">
      <PageHeader title="Discovery Agent" subtitle="Trouver des entreprises réelles, vérifiées et sourcées (API Sirene / data.gouv.fr)" />

      <Card className="p-6 mb-6">
        <label className="text-sm font-medium text-slate-700 flex items-center gap-2 mb-2"><Radar className="w-4 h-4 text-blue-600" /> Mission</label>
        <Textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} data-testid="mission-input"
          placeholder="Ex : Trouver jusqu'à 20 cabinets d'expertise comptable indépendants en Île-de-France" />
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <Btn variant="blue" onClick={interpret} disabled={loading} data-testid="interpret-btn">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />} Interpréter la mission
          </Btn>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-500">Mode :</span>
            <button onClick={() => setMode("real")} className={`px-2.5 py-1 rounded-full border ${mode === "real" ? "bg-blue-600 text-white border-blue-600" : "bg-white text-slate-600 border-slate-300"}`} data-testid="mode-real">Réel (Sirene)</button>
            <button onClick={() => setMode("simulation")} className={`px-2.5 py-1 rounded-full border ${mode === "simulation" ? "bg-amber-500 text-white border-amber-500" : "bg-white text-slate-600 border-slate-300"}`} data-testid="mode-simulation">Simulation</button>
          </div>
        </div>
      </Card>

      {interp && (
        <Card className="p-6 mb-6" data-testid="interpretation-card">
          <h3 className="font-heading font-semibold text-slate-800 mb-3 flex items-center gap-2"><FileSearch className="w-4 h-4 text-blue-600" /> Interprétation de la mission (vérifiez avant exécution)</h3>
          <div className="grid md:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-xs uppercase text-slate-400 mb-1">Code(s) NAF ciblé(s)</div>
              {interp.naf_codes.length ? interp.naf_codes.map((c) => (
                <span key={c} className="inline-block mr-2 mb-1 px-2 py-1 rounded-md bg-blue-50 text-blue-700 font-medium">{c} — {interp.naf_labels[c]}</span>
              )) : <span className="text-red-600">Aucun — précisez le secteur</span>}
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400 mb-1">Localisation</div>
              <span className="text-slate-700">{interp.region || "France (aucun filtre)"} {interp.departements.length ? `· ${interp.departements.length} département(s)` : ""}</span>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400 mb-1">Codes NAF voisins (cible adjacente)</div>
              {interp.adjacent_naf.length ? interp.adjacent_naf.map((c) => <span key={c} className="inline-block mr-2 mb-1 px-2 py-0.5 rounded bg-violet-50 text-violet-700 text-xs">{c}</span>) : <span className="text-slate-400">—</span>}
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400 mb-1">Nombre max / Exclusions</div>
              <span className="text-slate-700">Max {interp.max_results} · {interp.exclusions.length ? interp.exclusions.join(", ") : "aucune exclusion"}</span>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400 mb-1">Fourchette de taille demandée</div>
              <span className="text-slate-700" data-testid="interp-size-range">{interp.size_range ? `${interp.size_range[0]}–${interp.size_range[1]} salariés` : "Aucune (critère taille non évalué)"}</span>
            </div>
          </div>
          <div className="mt-4">
            <Btn variant="success" onClick={run} disabled={running || !interp.naf_codes.length} data-testid="run-btn">
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radar className="w-4 h-4" />} {running ? "Recherche en cours..." : "Lancer la recherche"}
            </Btn>
          </div>
        </Card>
      )}

      {mission && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-heading font-semibold text-slate-800">Résultats — {mission.candidates.length} entreprise(s)</h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 flex items-center gap-1"><Database className="w-3.5 h-3.5" /> {mission.meta.api_calls} appel(s) API · {mission.meta.total_api_results} au total dans Sirene</span>
              <Btn variant="secondary" onClick={() => { setMission(null); setInterp(null); loadMissions(); }} data-testid="new-mission-btn">Nouvelle mission</Btn>
            </div>
          </div>
          {mission.meta.source_unavailable && (
            <div className="flex items-center gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-3">
              <AlertTriangle className="w-4 h-4" /> {mission.meta.error} — aucune donnée n'a été inventée.
            </div>
          )}
          {mission.candidates.length === 0 ? <Card><Empty text="Aucun résultat trouvé pour ces critères." /></Card> :
            <div className="space-y-3">
              {mission.candidates.map((c) => (
                <CandidateCard key={c.siren} mission={mission} cand={c} labels={labels} onValidate={validate} onEnrich={enrich} enriching={enriching[c.siren]} done={done[c.siren]} />
              ))}
            </div>}
        </div>
      )}

      {!mission && missions.length > 0 && (
        <Card className="p-6">
          <h3 className="font-heading font-semibold text-slate-800 mb-1">Historique des missions</h3>
          <p className="text-xs text-slate-400 mb-3 flex items-center gap-1"><ShieldCheck className="w-3.5 h-3.5" /> RGPD : les fiches non validées sont automatiquement purgées après 90 jours.</p>
          <div className="divide-y divide-slate-100">
            {missions.map((m) => (
              <div key={m.id} className="py-2.5 flex items-center justify-between text-sm" data-testid={`mission-${m.id}`}>
                <div className="min-w-0">
                  <div className="text-slate-700 truncate">{m.mission_text}</div>
                  <div className="text-xs text-slate-400">{new Date(m.created_at).toLocaleString("fr-FR")} · {m.mode} · {m.candidate_count} candidat(s) · {m.validated_count} validé(s)</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
