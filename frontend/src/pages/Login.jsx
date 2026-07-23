import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { apiError } from "@/lib/api";
import { ScanSearch, Loader2 } from "lucide-react";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("jp.koffi@prospectia.app");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email.trim(), password.trim());
      navigate("/");
    } catch (err) {
      setError(apiError(err));
    } finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex bg-slate-900">
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-14 bg-slate-900 relative overflow-hidden">
        <div className="absolute -right-20 -top-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl" />
        <div className="flex items-center gap-3 relative">
          <div className="w-10 h-10 rounded-lg bg-blue-600 flex items-center justify-center">
            <ScanSearch className="w-6 h-6 text-white" />
          </div>
          <span className="font-heading font-extrabold text-2xl text-white tracking-tight">PROSPECTIA</span>
        </div>
        <div className="relative">
          <h1 className="font-heading text-4xl font-bold text-white leading-tight tracking-tight">
            Votre machine commerciale<br />semi-automatisée
          </h1>
          <p className="text-slate-400 mt-6 text-lg leading-relaxed max-w-md">
            Trouvez, analysez, qualifiez et contactez vos prospects B2B avec l'aide d'une intelligence artificielle — sous votre contrôle.
          </p>
        </div>
        <div className="text-slate-600 text-sm relative">Agent IA de prospection et de suivi commercial</div>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 bg-slate-50">
        <div className="w-full max-w-md">
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center">
              <ScanSearch className="w-5 h-5 text-white" />
            </div>
            <span className="font-heading font-extrabold text-xl tracking-tight">PROSPECTIA</span>
          </div>
          <h2 className="font-heading text-2xl font-bold text-slate-900 tracking-tight">Connexion</h2>
          <p className="text-slate-500 mt-1 mb-8 text-sm">Accédez à votre espace de prospection</p>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">Email</label>
              <input data-testid="login-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" required />
            </div>
            <div>
              <label className="text-sm font-medium text-slate-700 block mb-1.5">Mot de passe</label>
              <input data-testid="login-password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white border border-slate-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" required />
            </div>
            {error && <div data-testid="login-error" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>}
            <button data-testid="login-submit" type="submit" disabled={loading}
              className="w-full bg-slate-900 text-white rounded-lg py-2.5 font-medium hover:bg-slate-800 transition-colors active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-60">
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Se connecter
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
