import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Navbar from "@/components/Navbar";
import Stepper from "@/components/Stepper";
import Step1CV from "@/steps/Step1CV";
import Step2Job from "@/steps/Step2Job";
import Step3Generate from "@/steps/Step3Generate";
import Step4ATS from "@/steps/Step4ATS";
import Step5Export from "@/steps/Step5Export";
import { api } from "@/lib/api";

export default function Workflow() {
  const [params] = useSearchParams();
  const [step, setStep] = useState(1);
  const [maxReached, setMaxReached] = useState(1);
  const [cv, setCv] = useState(null);
  const [job, setJob] = useState(null);
  const [session, setSession] = useState(null);
  const [templateId, setTemplateId] = useState("classic");

  useEffect(() => {
    const cvId = params.get("cv");
    if (cvId) api.getCV(cvId).then((r) => setCv(r.data)).catch(() => {});
  }, [params]);

  const go = (n) => {
    setStep(n);
    setMaxReached((m) => Math.max(m, n));
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen bg-secondary/40">
      <Navbar />
      <main className="max-w-7xl mx-auto px-5 py-8 grid lg:grid-cols-[280px_1fr] gap-8">
        <aside>
          <Stepper current={step} maxReached={maxReached} onNavigate={go} />
        </aside>
        <section className="min-w-0" data-testid="workflow-content">
          {step === 1 && <Step1CV cv={cv} setCv={setCv} onNext={() => go(2)} />}
          {step === 2 && <Step2Job job={job} setJob={setJob} onNext={() => go(3)} />}
          {step === 3 && (
            <Step3Generate cv={cv} job={job} session={session} setSession={setSession} onNext={() => go(4)} onBack={() => go(2)} />
          )}
          {step === 4 && (
            <Step4ATS session={session} templateId={templateId} onNext={() => go(5)} onBack={() => go(3)} />
          )}
          {step === 5 && (
            <Step5Export session={session} templateId={templateId} setTemplateId={setTemplateId} onBack={() => go(4)} />
          )}
        </section>
      </main>
    </div>
  );
}
