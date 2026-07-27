import React from "react";
import { Loader2 } from "lucide-react";

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">{title}</h1>
        {subtitle && <p className="text-slate-500 text-sm mt-1">{subtitle}</p>}
      </div>
      {children && <div className="flex items-center gap-2 flex-wrap">{children}</div>}
    </div>
  );
}

export function Card({ children, className = "", ...props }) {
  return <div className={`bg-white rounded-lg border border-slate-200 shadow-sm ${className}`} {...props}>{children}</div>;
}

export function Btn({ children, variant = "primary", className = "", ...props }) {
  const styles = {
    primary: "bg-slate-900 text-white hover:bg-slate-800",
    secondary: "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50",
    blue: "bg-blue-600 text-white hover:bg-blue-700",
    danger: "bg-red-50 text-red-600 hover:bg-red-100 border border-red-200",
    success: "bg-emerald-600 text-white hover:bg-emerald-700",
  };
  return (
    <button {...props} className={`inline-flex items-center gap-2 rounded-lg font-medium px-4 py-2 text-sm transition-colors active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none ${styles[variant]} ${className}`}>
      {children}
    </button>
  );
}

export function Loading() {
  return <div className="flex items-center justify-center py-20 text-slate-400"><Loader2 className="w-6 h-6 animate-spin" /></div>;
}

export function Empty({ text }) {
  return <div className="text-center py-16 text-slate-400 text-sm">{text}</div>;
}

export function Input(props) {
  return <input {...props} className={`w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${props.className || ""}`} />;
}

export function Select({ children, ...props }) {
  return <select {...props} className={`bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${props.className || ""}`}>{children}</select>;
}

export function Textarea(props) {
  return <textarea {...props} className={`w-full bg-white border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent ${props.className || ""}`} />;
}

export function ScoreBadge({ score }) {
  if (score === null || score === undefined) {
    return <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-slate-100 text-slate-400">Non calculé</span>;
  }
  const s = score;
  const color = s >= 80 ? "bg-emerald-100 text-emerald-700" : s >= 65 ? "bg-blue-100 text-blue-700" : s >= 50 ? "bg-amber-100 text-amber-700" : "bg-slate-100 text-slate-500";
  return <span className={`inline-flex items-center justify-center min-w-[2.5rem] px-2 py-0.5 rounded-md text-xs font-semibold ${color}`}>{s}</span>;
}
