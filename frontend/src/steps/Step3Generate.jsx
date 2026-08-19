import { useEffect, useState, useMemo, useRef } from "react";
import { api, formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, ArrowRight, ArrowLeft, Check, Minus, Plus, Info, AlertTriangle, ShieldQuestion } from "lucide-react";
import { toast } from "sonner";

const SOURCE_LABELS = {
  offre: { label: "offre", cls: "bg-blue-50 text-blue-700 border-blue-200" },
  cv: { label: "CV", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  confirmation_utilisateur: { label: "confirmé", cls: "bg-amber-50 text-amber-700 border-amber-200" },
};

function Gauge({ value }) {
  const r = 42, c = 2 * Math.PI * r;
  const off = c - (Math.max(0, Math.min(100, value)) / 100) * c;
  const color = value >= 75 ? "#10B981" : value >= 50 ? "#F59E0B" : "#EF4444";
  return (
    <svg width="120" height="120" viewBox="0 0 100 100" className="shrink-0">
      <circle cx="50" cy="50" r={r} fill="none" stroke="#E2E8F0" strokeWidth="8" />
      <circle cx="50" cy="50" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={off} transform="rotate(-90 50 50)" />
      <text x="50" y="49" textAnchor="middle" fontSize="24" fontWeight="700" fill="#0F172A" fontFamily="Outfit">{value}</text>
      <text x="50" y="66" textAnchor="middle" fontSize="9" fill="#64748B">/ 100</text>
    </svg>
  );
}

const Bar = ({ label, value }) => (
  <div>
    <div className="flex justify-between text-sm mb-1"><span className="text-muted-foreground">{label}</span><span className="font-semibold">{value ?? 0}</span></div>
    <div className="h-2 rounded-full bg-secondary overflow-hidden">
      <div className="h-full rounded-full bg-primary" style={{ width: `${value ?? 0}%`, transition: "width .5s ease" }} />
    </div>
  </div>
);

export default function Step3Generate({ cv, job, session, setSession, onNext, onBack }) {
  const [loading, setLoading] = useState(false);
  const [accepted, setAccepted] = useState({}); // {expId: Set(indices)}
  const [confirmed, setConfirmed] = useState(new Set());
  const [coverAccepted, setCoverAccepted] = useState(true);
  const [savingSkills, setSavingSkills] = useState(false);
  const [saving, setSaving] = useState(false);
  const [genError, setGenError] = useState("");
  const pollRef = useRef(null);

  const initAccept = (s) => {
    const map = {};
    (s.experience_rewrites || []).forEach((r) => { map[r.experience_id] = new Set((r.bullets || []).map((_, i) => i)); });
    setAccepted(map);
  };

  const applyReady = (s) => {
    setSession(s);
    initAccept(s);
    setConfirmed(new Set(s.confirmed_skills || []));
    setLoading(false);
  };

  const startPolling = (sid) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.getSession(sid);
        if (data.status === "ready") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          applyReady(data);
        } else if (data.status === "error") {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setLoading(false);
          setGenError(data.error || "La génération a échoué.");
          toast.error("Échec de la génération IA");
        }
      } catch (err) {
        // transient error during polling — keep trying
      }
    }, 2500);
  };

  const run = async () => {
    if (!cv || !job) { toast.error("Complétez d'abord le CV et l'offre."); return; }
    setLoading(true);
    setGenError("");
    try {
      const { data } = await api.generate({ cv_id: cv.id, job_id: job.id, target_language: job.analysis?.language });
      if (data.status === "ready") { applyReady(data); return; }
      startPolling(data.id);
    } catch (err) {
      setLoading(false);
      setGenError(formatApiError(err.response?.data?.detail));
      toast.error(formatApiError(err.response?.data?.detail));
    }
  };

  useEffect(() => {
    if (!session && cv && job) run();
    else if (session && session.status === "ready") { initAccept(session); }
    else if (session && session.status === "pending") { setLoading(true); startPolling(session.id); }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const score = session?.score || {};
  // Defensive coercion: LLM may occasionally return objects like {skill, source} instead of plain strings.
  const asStr = (x) => (typeof x === "string" ? x : (x && (x.skill || x.keyword || x.name)) || "");
  const missing = useMemo(() => {
    const all = [...(score.missing_hard_skills || []), ...(score.missing_soft_skills || []), ...(score.missing_keywords || [])];
    return [...new Set(all.map(asStr).filter(Boolean))];
  }, [score]);
  const matched = useMemo(() => (
    [...(score.matched_hard_skills || []), ...(score.matched_soft_skills || [])].map(asStr).filter(Boolean)
  ), [score]);

  const toggleBullet = (expId, i) => {
    setAccepted((prev) => {
      const set = new Set(prev[expId] || []);
      set.has(i) ? set.delete(i) : set.add(i);
      return { ...prev, [expId]: set };
    });
  };

  const toggleConfirm = (skill) => {
    setConfirmed((prev) => { const s = new Set(prev); s.has(skill) ? s.delete(skill) : s.add(skill); return s; });
  };

  const saveSkills = async () => {
    setSavingSkills(true);
    try {
      const { data } = await api.confirmSkills(session.id, [...confirmed]);
      // confirm-skills relaunches an async generation so confirmed skills get woven into the
      // matching experience bullets (or placed once in the skills section).
      setSession(data);
      setLoading(true);
      setGenError("");
      startPolling(data.id);
      toast.success("Compétences appliquées — régénération en cours…");
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSavingSkills(false);
    }
  };

  const next = async () => {
    setSaving(true);
    try {
      const rewrites = (session.experience_rewrites || []).map((r) => ({
        experience_id: r.experience_id,
        accepted_bullets: [...(accepted[r.experience_id] || [])],
      }));
      await api.saveDecisions(session.id, { rewrites, cover_letter_accepted: coverAccepted });
      onNext();
    } catch (err) {
      toast.error(formatApiError(err.response?.data?.detail));
    } finally {
      setSaving(false);
    }
  };

  const notReady = loading || !session || session.status !== "ready";
  if (notReady) {
    return (
      <div className="animate-fade-up">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 3</span>
        <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">Génération contrôlée</h1>
        <div className="border border-border rounded-2xl bg-white p-12 mt-6 text-center">
          {genError ? (
            <>
              <AlertTriangle className="w-8 h-8 text-destructive mx-auto mb-3" aria-hidden="true" />
              <p className="font-medium">La génération n'a pas abouti.</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-md mx-auto">{genError}</p>
              <Button className="bg-primary mt-5" onClick={run} data-testid="generate-retry-btn">Réessayer</Button>
            </>
          ) : (
            <>
              <Loader2 className="w-8 h-8 text-brand animate-spin mx-auto mb-3" />
              <p className="font-medium">Croisement de votre CV avec l'offre…</p>
              <p className="text-sm text-muted-foreground mt-1">Reformulation ligne par ligne, sans rien inventer. Cela peut prendre jusqu'à une minute.</p>
              {!cv || !job ? <p className="text-sm text-destructive mt-4">CV ou offre manquant — revenez aux étapes précédentes.</p> : null}
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-up space-y-6">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-brand">Bloc 3</span>
        <h1 className="font-heading text-3xl font-bold tracking-tight mt-1">Génération contrôlée</h1>
        <p className="text-muted-foreground mt-2">Score transparent, confirmation des compétences manquantes, et reformulation validée ligne par ligne.</p>
      </div>

      {/* Score */}
      <div className="border border-border rounded-2xl bg-white p-6" data-testid="score-card">
        <h3 className="font-heading font-semibold text-lg mb-4">Score de correspondance</h3>
        <div className="flex flex-col sm:flex-row gap-6 items-center sm:items-start">
          <div className="text-center">
            <Gauge value={score.overall ?? 0} />
            <p className="text-xs text-muted-foreground mt-1">Score global</p>
          </div>
          <div className="flex-1 w-full space-y-3">
            <Bar label="Compétences techniques" value={score.hard_skills} />
            <Bar label="Compétences comportementales" value={score.soft_skills} />
            <Bar label="Formation" value={score.education} />
            <Bar label="Mots-clés" value={score.keywords} />
          </div>
        </div>
        {score.explanation && (
          <div className="flex gap-2 mt-4 text-sm text-muted-foreground bg-secondary/60 rounded-xl p-3">
            <Info className="w-4 h-4 shrink-0 mt-0.5 text-brand" aria-hidden="true" /> <p>{score.explanation}</p>
          </div>
        )}
        <div className="grid sm:grid-cols-2 gap-3 mt-4">
          <MiniList title="Correspondances" items={matched} tone="ok" />
          <MiniList title="Manquants dans le CV" items={missing} tone="warn" />
        </div>
      </div>

      {/* Missing skills confirmation */}
      {missing.length > 0 && (
        <div className="border border-amber-200 rounded-2xl bg-amber-50/50 p-6" data-testid="missing-skills-card">
          <div className="flex items-center gap-2 mb-2">
            <ShieldQuestion className="w-5 h-5 text-amber-600" aria-hidden="true" />
            <h3 className="font-heading font-semibold text-lg">Compétences manquantes — confirmation requise</h3>
          </div>
          <p className="text-sm text-muted-foreground mb-4">
            L'offre demande des compétences absentes de votre CV. Matchipy ne les ajoutera <b>jamais</b> automatiquement.
            Cochez uniquement celles que vous possédez <b>réellement</b>. Après validation, le CV est <b>régénéré</b> : chaque compétence confirmée est soit intégrée directement dans la mission concernée, soit ajoutée une seule fois à la section compétences.
          </p>
          <div className="grid sm:grid-cols-2 gap-2">
            {missing.map((sk) => (
              <label key={sk} className="flex items-center gap-3 border border-border rounded-xl bg-white px-4 py-3 cursor-pointer hover:border-amber-300"
                data-testid={`missing-skill-${sk}`}>
                <Checkbox checked={confirmed.has(sk)} onCheckedChange={() => toggleConfirm(sk)} />
                <span className="text-sm">Je possède réellement : <b>{sk}</b></span>
              </label>
            ))}
          </div>
          <Button variant="outline" className="mt-4" onClick={saveSkills} disabled={savingSkills} data-testid="confirm-skills-btn">
            {savingSkills && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Appliquer ces compétences et régénérer ({confirmed.size})
          </Button>
        </div>
      )}

      {/* Curated skills section (transverse skills not tied to a specific experience) */}
      {(session.skills_section || []).length > 0 && (
        <div className="border border-border rounded-2xl bg-white p-5" data-testid="skills-section-card">
          <h3 className="font-heading font-semibold text-lg mb-1">Section compétences du CV</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Compétences transverses non rattachées à une mission précise (les autres sont intégrées directement dans les puces). Max 12, priorisées selon l'offre.
          </p>
          <div className="flex flex-wrap gap-2">
            {session.skills_section.map((s, i) => {
              const src = SOURCE_LABELS[s.source] || SOURCE_LABELS.cv;
              return <span key={i} className={`text-sm px-2 py-1 rounded border ${src.cls}`}>{s.skill} · {src.label}</span>;
            })}
          </div>
        </div>
      )}

      {/* Experience rewrites diffs */}
      <div className="space-y-4">
        <h3 className="font-heading font-semibold text-lg">Reformulation par ligne d'expérience</h3>
        {(session.experience_rewrites || []).map((r) => (
          <div key={r.experience_id} className="border border-border rounded-2xl bg-white p-5" data-testid={`rewrite-${r.experience_id}`}>
            <p className="font-semibold">{r.role} {r.company ? `— ${r.company}` : ""}</p>
            <div className="mt-3 space-y-3">
              {(r.bullets || []).map((b, i) => {
                const isAccepted = accepted[r.experience_id]?.has(i);
                return (
                  <div key={i} className="border border-border rounded-xl overflow-hidden">
                    <div className="grid md:grid-cols-2">
                      <div className="p-3 bg-red-50/60 border-b md:border-b-0 md:border-r border-border">
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-red-700 mb-1"><Minus className="w-3.5 h-3.5" /> Avant</div>
                        <p className="text-sm text-slate-700">{b.original || <span className="italic text-muted-foreground">(nouvelle ligne)</span>}</p>
                      </div>
                      <div className={`p-3 ${isAccepted ? "bg-emerald-50/60" : "bg-secondary/40"}`}>
                        <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 mb-1"><Plus className="w-3.5 h-3.5" /> Après</div>
                        <p className="text-sm text-slate-800">{b.proposed}</p>
                        {(b.keywords_used || []).length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {b.keywords_used.map((k, ki) => {
                              const src = SOURCE_LABELS[k.source] || SOURCE_LABELS.cv;
                              return <span key={ki} className={`text-[11px] px-1.5 py-0.5 rounded border ${src.cls}`}>{k.keyword} · {src.label}</span>;
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                    <label className="flex items-center gap-2 px-3 py-2 border-t border-border bg-white cursor-pointer" data-testid={`accept-bullet-${r.experience_id}-${i}`}>
                      <Checkbox checked={isAccepted} onCheckedChange={() => toggleBullet(r.experience_id, i)} />
                      <span className="text-sm">{isAccepted ? "Reformulation acceptée" : "Conserver la version d'origine"}</span>
                    </label>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Cover letter */}
      <div className="border border-border rounded-2xl bg-white p-5" data-testid="cover-letter-card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-heading font-semibold text-lg">Lettre de motivation</h3>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <Checkbox checked={coverAccepted} onCheckedChange={(v) => setCoverAccepted(!!v)} data-testid="accept-cover-checkbox" /> Inclure
          </label>
        </div>
        <div className="space-y-3">
          {(session.cover_letter?.paragraphs || []).map((p, i) => (
            <Textarea key={i} rows={3} defaultValue={p} readOnly className="bg-secondary/30" />
          ))}
          {(session.cover_letter?.paragraphs || []).length === 0 && <p className="text-sm text-muted-foreground">Aucune lettre générée.</p>}
        </div>
      </div>

      <div className="flex justify-between sticky bottom-4 bg-white/80 backdrop-blur-xl border border-border rounded-xl p-3">
        <Button variant="outline" onClick={onBack}><ArrowLeft className="w-4 h-4 mr-2" /> Retour</Button>
        <Button className="bg-primary" onClick={next} disabled={saving} data-testid="generate-next-btn">
          {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />} Contrôle ATS <ArrowRight className="w-4 h-4 ml-2" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

const MiniList = ({ title, items, tone }) => (
  <div className={`rounded-xl border p-3 ${tone === "warn" ? "border-amber-200 bg-amber-50/40" : "border-emerald-200 bg-emerald-50/40"}`}>
    <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide mb-2">
      {tone === "warn" ? <AlertTriangle className="w-3.5 h-3.5 text-amber-600" /> : <Check className="w-3.5 h-3.5 text-emerald-600" />} {title}
    </div>
    <div className="flex flex-wrap gap-1.5">
      {(items || []).length ? [...new Set(items)].map((x, i) => <Badge key={i} variant="outline" className="bg-white">{x}</Badge>) : <span className="text-sm text-muted-foreground">—</span>}
    </div>
  </div>
);
