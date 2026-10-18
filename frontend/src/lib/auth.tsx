import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { api, session } from "./api";
import type { User } from "./types";
import { useQueryClient } from "@tanstack/react-query";
const AuthContext = createContext<{
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}>({ user: null, loading: true, login: async () => {}, logout: () => {} });
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true);
  const client = useQueryClient();
  useEffect(() => {
    const expired = () => {
      session.clear();
      client.clear();
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("civicshield:unauthorized", expired);
    return () =>
      window.removeEventListener("civicshield:unauthorized", expired);
  }, [client]);
  useEffect(() => {
    const bootToken = session.get();
    const controller = new AbortController();
    let active = true;
    const current = () => active && session.get() === bootToken;
    if (bootToken) {
      api<User>("/auth/me", { signal: controller.signal })
        .then((restoredUser) => {
          if (current()) setUser(restoredUser);
        })
        .catch(() => {
          if (current() && !controller.signal.aborted) {
            session.clear();
            setUser(null);
            setLoading(false);
          }
        })
        .finally(() => {
          if (current()) setLoading(false);
        });
    } else {
      setLoading(false);
    }
    return () => {
      active = false;
      controller.abort();
    };
  }, []);
  async function login(email: string, password: string) {
    const result = await api<{ access_token: string; user: User }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    );
    client.clear();
    session.set(result.access_token);
    setUser(result.user);
    setLoading(false);
  }
  function logout() {
    session.clear();
    client.clear();
    setUser(null);
    setLoading(false);
  }
  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
export const useAuth = () => useContext(AuthContext);
