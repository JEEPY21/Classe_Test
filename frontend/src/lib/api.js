import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const client = axios.create({ baseURL: API, withCredentials: true });

export const TOKEN_KEY = "matchipy_token";
export const REFRESH_KEY = "matchipy_refresh";

client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshingPromise = null;
client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isAuthCall = original?.url?.includes("/auth/");
    if (status === 401 && original && !original._retry && !isAuthCall) {
      original._retry = true;
      const rt = localStorage.getItem(REFRESH_KEY);
      if (!rt) {
        localStorage.removeItem(TOKEN_KEY);
        return Promise.reject(error);
      }
      try {
        if (!refreshingPromise)
          refreshingPromise = axios.post(`${API}/auth/refresh`, { refresh_token: rt }, { withCredentials: true });
        const { data } = await refreshingPromise;
        refreshingPromise = null;
        localStorage.setItem(TOKEN_KEY, data.access_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return client(original);
      } catch (e) {
        refreshingPromise = null;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

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

  createApplication: (data) => client.post("/applications", data),
  listApplications: (statut) => client.get("/applications", { params: statut ? { statut } : {} }),
  updateApplication: (id, data) => client.put(`/applications/${id}`, data),
  deleteApplication: (id) => client.delete(`/applications/${id}`),
  downloadApplicationDoc: (id, data) => client.post(`/applications/${id}/download`, data, { responseType: "blob" }),

  listHistory: () => client.get("/history"),
  deleteHistory: (id) => client.delete(`/history/${id}`),
  downloadHistoryDoc: (id, data) => client.post(`/history/${id}/download`, data, { responseType: "blob" }),
};

export default client;
