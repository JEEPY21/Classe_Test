import React, { createContext, useContext, useEffect, useState } from "react";
import client from "@/lib/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("prospectia_token");
    if (!token) { setLoading(false); return; }
    client.get("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => localStorage.removeItem("prospectia_token"))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const attempt = () => client.post("/auth/login", { email, password });
    let data;
    try {
      ({ data } = await attempt());
    } catch (err) {
      const status = err.response?.status;
      const transient = !err.response || [404, 502, 503, 504].includes(status) || status >= 500;
      if (transient) {
        await new Promise((r) => setTimeout(r, 1500));
        ({ data } = await attempt());
      } else {
        throw err;
      }
    }
    localStorage.setItem("prospectia_token", data.token);
    setUser(data.user);
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("prospectia_token");
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
