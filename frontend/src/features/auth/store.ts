import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { AuthState } from "./types";
import { decodeJwt, mapClaimsToUser } from "./utils";

interface AuthActions {
  setSession: (token: string | null) => void;
  clearSession: () => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAuthStore = create<AuthState & AuthActions>()(
  devtools(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: true,
      error: null,

      setSession: (token) => {
        if (!token) {
          set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
          return;
        }

        const claims = decodeJwt(token);
        if (!claims) {
          set({
            user: null,
            accessToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: "Invalid session token",
          });
          return;
        }

        const user = mapClaimsToUser(claims);
        set({ user, accessToken: token, isAuthenticated: true, isLoading: false, error: null });
      },

      clearSession: () => {
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    { name: "AuthStore" }
  )
);
