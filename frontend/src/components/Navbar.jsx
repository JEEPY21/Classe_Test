import { useAuth } from "@/context/AuthContext";
import { useNavigate, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LogOut, LayoutGrid, BriefcaseBusiness } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-white/85 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-5 h-16 flex items-center justify-between">
        <Link to="/dashboard" className="flex items-center gap-2" data-testid="navbar-logo">
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-heading font-bold text-lg">M</span>
          </div>
          <span className="font-heading font-bold text-xl tracking-tight">Matchipy</span>
        </Link>
        {user && user !== false && (
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/dashboard")}
              data-testid="navbar-dashboard-btn"
            >
              <LayoutGrid className="w-4 h-4 mr-2" aria-hidden="true" /> Tableau de bord
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/applications")}
              data-testid="navbar-applications-btn"
            >
              <BriefcaseBusiness className="w-4 h-4 mr-2" aria-hidden="true" /> Suivi
            </Button>
            <span className="text-sm text-muted-foreground hidden sm:inline">{user.email}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
              data-testid="navbar-logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" aria-hidden="true" /> Déconnexion
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
