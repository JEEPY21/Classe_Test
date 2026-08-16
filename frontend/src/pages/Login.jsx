import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth, formatApiError } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(email, password);
      toast.success("Connexion réussie");
      navigate("/dashboard");
    } catch (err) {
      setError(formatApiError(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:block relative">
        <img
          src="https://images.unsplash.com/photo-1698047681432-006d2449c631?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxNzV8MHwxfHNlYXJjaHwyfHxwcm9mZXNzaW9uYWwlMjByZXN1bWUlMjBqb2IlMjBhcHBsaWNhdGlvbiUyMGRlc2t8ZW58MHx8fHwxNzg2ODc0NjU5fDA&ixlib=rb-4.1.0&q=85"
          alt="Recherche d'emploi"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-primary/70" />
        <div className="absolute bottom-10 left-10 right-10 text-primary-foreground">
          <h2 className="font-heading text-3xl font-bold">Matchipy</h2>
          <p className="mt-2 text-primary-foreground/80 max-w-md">
            Des candidatures optimisées, honnêtes et traçables.
          </p>
        </div>
      </div>

      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <h1 className="font-heading text-3xl font-bold tracking-tight">Connexion</h1>
          <p className="text-muted-foreground mt-2 mb-8">Accédez à votre espace Matchipy.</p>

          <div className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                required placeholder="vous@exemple.com" className="mt-1.5" data-testid="login-email-input" />
            </div>
            <div>
              <Label htmlFor="password">Mot de passe</Label>
              <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required placeholder="••••••••" className="mt-1.5" data-testid="login-password-input" />
            </div>
          </div>

          {error && <p className="text-sm text-destructive mt-4" data-testid="login-error">{error}</p>}

          <Button type="submit" disabled={loading} className="w-full mt-6 bg-primary h-11" data-testid="login-submit-btn">
            {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" aria-hidden="true" />}
            Se connecter
          </Button>

          <p className="text-sm text-muted-foreground mt-6 text-center">
            Pas encore de compte ?{" "}
            <Link to="/register" className="text-brand font-medium hover:underline" data-testid="login-to-register">Créer un compte</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
