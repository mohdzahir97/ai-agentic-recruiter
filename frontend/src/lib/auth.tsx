"use client";

/**
 * Session state and route protection.
 *
 * `AuthProvider` restores the session from localStorage and re-validates it
 * against /auth/me on first load, so a token that was revoked or expired
 * server-side does not leave a stale name in the header.
 *
 * `RequireRole` is the client-side half of RBAC. The backend enforces the real
 * rules — this exists so a candidate who types a recruiter URL sees a redirect
 * rather than a screen full of 403s.
 */
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, clearSession, getStoredUser, getToken, saveSession } from "./api";
import type { Role, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    role: Role;
    company?: string;
  }) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function homeFor(role: Role): string {
  return role === "RECRUITER" ? "/recruiter/dashboard" : "/candidate/dashboard";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = getStoredUser();
    if (!stored || !getToken()) {
      setLoading(false);
      return;
    }
    // Show the stored user immediately, then confirm it in the background.
    setUser(stored);
    api
      .me()
      .then(setUser)
      .catch(() => {
        clearSession();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    saveSession(result.access_token, result.user);
    setUser(result.user);
    return result.user;
  }, []);

  const register = useCallback(
    async (payload: {
      email: string;
      password: string;
      full_name: string;
      role: Role;
      company?: string;
    }) => {
      const result = await api.register(payload);
      saveSession(result.access_token, result.user);
      setUser(result.user);
      return result.user;
    },
    [],
  );

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    window.location.href = "/login";
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function RequireRole({
  role,
  children,
}: {
  role: Role;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
    } else if (user.role !== role) {
      // Signed in, wrong portal: send them to their own instead of a dead end.
      router.replace(homeFor(user.role));
    }
  }, [user, loading, role, router]);

  if (loading || !user || user.role !== role) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-slate-500">
        Loading…
      </div>
    );
  }
  return <>{children}</>;
}
