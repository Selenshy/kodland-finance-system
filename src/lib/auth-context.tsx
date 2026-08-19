"use client";

import { createContext, useContext, useEffect, useState, ReactNode, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiRequest, setToken } from "./api";
import { User } from "./types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasEntityAccess: (entityId: number) => boolean;
  isAtLeast: (role: "admin" | "accountant" | "viewer") => boolean;
};

const RANK: Record<string, number> = { viewer: 0, accountant: 1, admin: 2 };

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const loadMe = useCallback(async () => {
    try {
      const me = await apiRequest<User>("/api/auth/me");
      setUser(me);
    } catch {
      setUser(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMe();
  }, [loadMe]);

  useEffect(() => {
    if (!loading && !user && pathname !== "/login") {
      router.replace("/login");
    }
  }, [loading, user, pathname, router]);

  const login = async (email: string, password: string) => {
    const res = await apiRequest<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: { email, password },
    });
    setToken(res.access_token);
    await loadMe();
    router.replace("/");
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    router.replace("/login");
  };

  const hasEntityAccess = (entityId: number) => {
    if (!user) return false;
    return user.entity_ids === null || user.entity_ids.includes(entityId);
  };

  const isAtLeast = (role: "admin" | "accountant" | "viewer") => {
    if (!user) return false;
    return RANK[user.global_role] >= RANK[role];
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasEntityAccess, isAtLeast }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
