import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, withCredentials: true });

export function formatApiError(detail) {
  if (detail == null) return "Une erreur est survenue. Réessayez.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export const api = {
  register: (data) => client.post("/auth/register", data),
  login: (data) => client.post("/auth/login", data),
  logout: () => client.post("/auth/logout"),
  me: () => client.get("/auth/me"),

  uploadCV: (formData) =>
    client.post("/cv/upload", formData, { headers: { "Content-Type": "multipart/form-data" } }),
  listCVs: () => client.get("/cv"),
  getCV: (id) => client.get(`/cv/${id}`),
  updateCV: (id, structured) => client.put(`/cv/${id}`, { structured }),
  deleteCV: (id) => client.delete(`/cv/${id}`),

  analyzeJob: (raw_text) => client.post("/job/analyze", { raw_text }),

  generate: (data) => client.post("/generate", data),
  getSession: (id) => client.get(`/generate/${id}`),
  confirmSkills: (id, confirmed_skills) => client.put(`/generate/${id}/confirm-skills`, { confirmed_skills }),
  saveDecisions: (id, data) => client.put(`/generate/${id}/decisions`, data),

  atsCheck: (data) => client.post("/ats/check", data),

  templates: () => client.get("/export/templates"),
  preview: (data) => client.post("/export/preview", data),
  download: (data) => client.post("/export/download", data, { responseType: "blob" }),
};

export default client;
