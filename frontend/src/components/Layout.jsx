import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import {
  LayoutDashboard, Building2, Users, ScanSearch, CheckSquare, Megaphone, Mail,
  Repeat, MessageSquare, Target, FileText, Ban, Activity, Settings, AlertTriangle,
  Menu, X, LogOut, Briefcase, ChevronRight, Radar
} from "lucide-react";

const NAV = [
  { to: "/", label: "Tableau de bord", icon: LayoutDashboard, testid: "nav-dashboard" },
  { to: "/discovery", label: "Discovery Agent", icon: Radar, testid: "nav-discovery" },
  { to: "/entreprises", label: "Entreprises", icon: Building2, testid: "nav-companies" },
  { to: "/contacts", label: "Contacts", icon: Users, testid: "nav-contacts" },
  { to: "/validation", label: "File de validation", icon: CheckSquare, testid: "nav-validation" },
  { to: "/campagnes", label: "Campagnes", icon: Megaphone, testid: "nav-campaigns" },
  { to: "/emails", label: "Emails", icon: Mail, testid: "nav-emails" },
  { to: "/relances", label: "Relances", icon: Repeat, testid: "nav-followups" },
  { to: "/reponses", label: "Réponses", icon: MessageSquare, testid: "nav-replies" },
  { to: "/opportunites", label: "Opportunités", icon: Target, testid: "nav-opportunities" },
  { to: "/services", label: "Offres & services", icon: Briefcase, testid: "nav-services" },
  { to: "/modeles", label: "Modèles de messages", icon: FileText, testid: "nav-templates" },
  { to: "/exclusions", label: "Liste d'exclusion", icon: Ban, testid: "nav-exclusions" },
  { to: "/journal", label: "Journal d'activité", icon: Activity, testid: "nav-activity" },
  { to: "/erreurs", label: "Centre d'erreurs", icon: AlertTriangle, testid: "nav-errors" },
  { to: "/parametres", label: "Paramètres", icon: Settings, testid: "nav-settings" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  const SidebarContent = () => (
    <>
      <div className="px-6 py-5 border-b border-slate-800">
        <div className="flex items-center gap-2.5 select-none cursor-default" data-testid="brand-logo">
          <div className="w-9 h-9 rounded-lg bg-blue-600 flex items-center justify-center flex-shrink-0">
            <ScanSearch className="w-5 h-5 text-white" />
          </div>
          <div className="leading-none">
            <div className="font-heading font-extrabold text-white text-lg tracking-tight">PROSPECTIA</div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-slate-500 mt-1">Agent IA commercial</div>
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-0.5">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.to === "/"} data-testid={n.testid}
            onClick={() => setOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150 ${
                isActive ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}>
            <n.icon className="w-4 h-4 flex-shrink-0" />
            <span className="truncate">{n.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-800 p-3">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-white text-xs font-semibold">
            {(user?.name || "JP").split(" ").map((s) => s[0]).slice(0, 2).join("")}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">{user?.name}</div>
            <div className="text-xs text-slate-500 truncate">Administrateur</div>
          </div>
          <button data-testid="logout-btn" onClick={logout} className="text-slate-400 hover:text-white transition-colors">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </>
  );

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <aside className="w-64 flex-shrink-0 bg-slate-900 flex-col hidden md:flex">
        <SidebarContent />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpen(false)} />
          <aside className="absolute left-0 top-0 bottom-0 w-64 bg-slate-900 flex flex-col">
            <SidebarContent />
          </aside>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 md:px-6 flex-shrink-0">
          <button className="md:hidden text-slate-600" onClick={() => setOpen(true)} data-testid="mobile-menu-btn">
            <Menu className="w-6 h-6" />
          </button>
          <div className="hidden md:block text-sm text-slate-400">Prospection commerciale assistée par IA</div>
          <div className="flex items-center gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> Mode simulation
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
