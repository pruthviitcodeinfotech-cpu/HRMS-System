import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { AuthState, CurrentUserProfile } from "./types";
import { decodeJwt, mapClaimsToUser } from "./utils";

interface AuthActions {
  setSession: (token: string | null) => void;
  clearSession: () => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  setUserProfile: (profile: CurrentUserProfile) => void;
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

      setUserProfile: (profile) => {
        set((state) => {
          if (!state.user) return state;
          return {
            user: {
              ...state.user,
              id: String(profile.id),
              email: profile.email,
              orgId: String(profile.org_id),
              isSuperAdmin: !!profile.is_super_admin,
              isActive: !!profile.is_active,
              permissions: profile.permissions || [],
              branchIds: profile.data_scope?.branch_ids || [],
              departmentIds: profile.data_scope?.department_ids || [],
              name: profile.name,
              employeeId: profile.employee_id ? String(profile.employee_id) : null,
              mobileCountryCode: profile.mobile_country_code,
              mobileNumber: profile.mobile_number,
            },
          };
        });
      },

      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
    }),
    { name: "AuthStore" }
  )
);
