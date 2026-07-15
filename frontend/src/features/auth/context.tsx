"use client";

import React, { createContext, useEffect } from "react";
import { useAuthStore } from "./store";
import { User } from "./types";

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (token: string) => void;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

import { PermissionProvider } from "./rbac/permission-context";

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    setSession,
    clearSession,
    setLoading,
    setError,
  } = useAuthStore();

  const login = (token: string) => {
    setSession(token);
  };

  const logout = async () => {
    setLoading(true);
    try {
      const { logoutSession } = await import("./services");
      await logoutSession();
    } catch (err) {
      console.error("Failed to call backend logout:", err);
    } finally {
      clearSession();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
    }
  };

  const refresh = async () => {
    setLoading(true);
    try {
      const { refreshSession, fetchCurrentUser } = await import("./services");
      const { access_token } = await refreshSession();
      setSession(access_token);

      const profileRes = await fetchCurrentUser();
      if (profileRes.success && profileRes.data) {
        useAuthStore.getState().setUserProfile(profileRes.data);
      }
    } catch (err) {
      console.error("Failed to refresh session:", err);
      clearSession();
      setError("Session expired");
    } finally {
      setLoading(false);
    }
  };

  // Perform initial session checks on client mount
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { refreshSession, fetchCurrentUser } = await import("./services");
        const { access_token } = await refreshSession();
        setSession(access_token);

        const profileRes = await fetchCurrentUser();
        if (profileRes.success && profileRes.data) {
          useAuthStore.getState().setUserProfile(profileRes.data);
        }
      } catch {
        clearSession();
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, [setSession, clearSession, setLoading]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        error,
        login,
        logout,
        refresh,
      }}
    >
      <PermissionProvider>{children}</PermissionProvider>
    </AuthContext.Provider>
  );
};
