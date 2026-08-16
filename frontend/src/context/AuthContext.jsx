import { createContext, useContext, useEffect, useState } from "react";
import { api, formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // null = checking, false = anon, obj = logged in

  useEffect(() => {
    api
      .me()
      .then((r) => setUser(r.data))
      .catch(() => setUser(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await api.login({ email, password });
    setUser(data);
    return data;
  };

  const register = async (email, password, name) => {
    const { data } = await api.register({ email, password, name });
    setUser(data);
    return data;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch (_) {}
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
