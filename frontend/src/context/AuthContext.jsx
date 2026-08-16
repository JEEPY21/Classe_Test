import { createContext, useContext, useEffect, useState } from "react";
import { api, TOKEN_KEY, REFRESH_KEY, formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

function storeTokens(data) {
  if (data.access_token) localStorage.setItem(TOKEN_KEY, data.access_token);
  if (data.refresh_token) localStorage.setItem(REFRESH_KEY, data.refresh_token);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = logged in

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setUser(false);
      return;
    }
    api
      .me()
      .then((r) => setUser(r.data))
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        setUser(false);
      });
  }, []);

  const login = async (email, password) => {
    const { data } = await api.login({ email, password });
    storeTokens(data);
    setUser(data);
    return data;
  };

  const register = async (email, password, name) => {
    const { data } = await api.register({ email, password, name });
    storeTokens(data);
    setUser(data);
    return data;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (_) {}
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setUser(false);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
export { formatApiError };
