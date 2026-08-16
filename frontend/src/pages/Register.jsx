import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth, formatApiError } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(form.email, form.password, form.name);
      toast.success("Compte créé");
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="flex items-center justify-center p-6 order-2 lg:order-1">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="register-form">
          <h1 className="font-heading text-3xl font-bold tracking-tight">Créer un compte</h1>
          <p className="text-muted-foreground mt-2 mb-8">Commencez à optimiser vos candidatures.</p>

          <div className="space-y-4">
            <div>
              <Label htmlFor="name">Nom complet</Label>
              <Input id="name" value={form.name} onChange={set("name")} required
                placeholder="Camille Dupont" className="mt-1.5" data-testid="register-name-input" />
            </div>
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={form.email} onChange={set("email")} required
                placeholder="vous@exemple.com" className="mt-1.5" data-testid="register-email-input" />
            </div>
            <div>
              <Label htmlFor="password">Mot de passe</Label>
              <Input id="password" type="password" value={form.password} onChange={set("password")} required
                minLength={6} placeholder="6 caractères minimum" className="mt-1.5" data-testid="register-password-input" />
            </div>
          </div>

          {error && <p className="text-sm text-destructive mt-4" data-testid="register-error">{error}</p>}

          <Button type="submit" disabled={loading} className="w-full mt-6 bg-primary h-11" data-testid="register-submit-btn">
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />}
            Créer mon compte
          </Button>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            Déjà inscrit ?{" "}
            <Link to="/login" className="text-brand font-medium hover:underline" data-testid="register-to-login">Se connecter</Link>
          </p>
        </form>
      </div>

      <div className="hidden lg:block relative order-1 lg:order-2">
        <img
          src="https://images.unsplash.com/photo-1586281380349-632531db7ed4?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxNzV8MHwxfHNlYXJjaHwzfHxwcm9mZXNzaW9uYWwlMjByZXN1bWUlMjBqb2IlMjBhcHBsaWNhdGlvbiUyMGRlc2t8ZW58MHx8fHwxNzg2ODc0NjU5fDA&ixlib=rb-4.1.0&q=85"
          alt="Espace de travail"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-primary/70" />
      </div>
    </div>
  );
}
