import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";
import type { LoginResponse, User } from "../types/auth";

type AuthContextValue = {
  user: User | null;
  token: string;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState(localStorage.getItem("smartloan_token") || "");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    api
      .get<User>("/auth/me")
      .then((response) => {
        setUser(response.data);
      })
      .catch(() => {
        localStorage.removeItem("smartloan_token");
        setToken("");
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token]);

  const login = async (email: string, password: string) => {
    const response = await api.post<LoginResponse>("/auth/login", {
      email,
      password,
    });

    localStorage.setItem("smartloan_token", response.data.access_token);
    setToken(response.data.access_token);
    setUser(response.data.user);
  };

  const signOut = () => {
    localStorage.removeItem("smartloan_token");
    setToken("");
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
