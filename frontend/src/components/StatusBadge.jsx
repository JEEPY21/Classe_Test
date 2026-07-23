import React from "react";

export const STATUS_COLORS = {
  "Nouveau": "info", "À analyser": "warning", "En analyse": "warning",
  "À qualifier": "warning", "Qualifié": "success", "Non qualifié": "muted",
  "Contact à rechercher": "warning", "Prêt pour message": "info", "À valider": "warning",
  "Contacté": "info", "Relance 1": "info", "Relance 2": "info", "Relance finale": "info",
  "A répondu": "info", "Intéressé": "success", "À rappeler": "warning", "Rendez-vous": "success",
  "Proposition envoyée": "info", "Négociation": "warning", "Client": "success",
  "Refus": "error", "Injoignable": "muted", "Ne plus contacter": "error", "Archivé": "muted",
  "Envoyé": "success", "Programmé": "info", "Refusé": "error", "Programmée": "warning",
  "Annulée": "muted", "Envoyée": "success", "Active": "success", "Brouillon": "muted",
  "En préparation": "warning", "En pause": "warning", "Terminée": "info",
};

const CLASSES = {
  success: "bg-emerald-50 text-emerald-700 border-emerald-200",
  warning: "bg-amber-50 text-amber-700 border-amber-200",
  error: "bg-red-50 text-red-700 border-red-200",
  info: "bg-blue-50 text-blue-700 border-blue-200",
  muted: "bg-slate-100 text-slate-600 border-slate-200",
};

export default function StatusBadge({ status, testid }) {
  const variant = STATUS_COLORS[status] || "muted";
  return (
    <span data-testid={testid} className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${CLASSES[variant]}`}>
      {status || "—"}
    </span>
  );
}

export const ALL_STATUSES = Object.keys(STATUS_COLORS).slice(0, 24);
