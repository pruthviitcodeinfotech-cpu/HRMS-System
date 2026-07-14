import axios from "axios";
import { env } from "@/config/env";
import { useAuthStore } from "./store";
import { handleApiError } from "@/services/api-client/error-handler";

export interface LoginPayload {
  email: string;
  password: string;
  device_info?: string;
}

export interface AuthUser {
  id: number;
  org_id: number;
  name: string;
  email: string;
  mobile_country_code: string;
  mobile_number: string;
  is_super_admin: boolean;
  is_active: boolean;
  employee_id: number | null;
  last_login_at: string | null;
}

export interface LoginResponseData {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface AccessTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  refresh_token: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id?: string;
}

// Cookie Helpers
export const setCookie = (name: string, value: string, maxAgeSeconds: number) => {
  if (typeof window === "undefined") return;
  const sameSite = name === "refresh_token" ? "Strict" : "Lax";
  document.cookie = `${name}=${value}; path=/; max-age=${maxAgeSeconds}; Secure; SameSite=${sameSite}`;
};

export const getCookie = (name: string): string | null => {
  if (typeof window === "undefined") return null;
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  if (match) return match[2];
  return null;
};

export const deleteCookie = (name: string) => {
  if (typeof window === "undefined") return;
  document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; Secure; SameSite=Lax`;
};

export const loginSession = async (
  orgId: string,
  payload: LoginPayload
): Promise<ApiResponse<LoginResponseData>> => {
  try {
    const response = await axios.post<ApiResponse<LoginResponseData>>(
      `${env.NEXT_PUBLIC_API_URL}/auth/login`,
      payload,
      {
        headers: {
          "x-org-id": orgId,
        },
        withCredentials: true,
      }
    );

    const data = response.data;
    if (data.success && data.data) {
      const { access_token, refresh_token } = data.data;
      setCookie("access_token", access_token, 900); // 15 mins
      setCookie("refresh_token", refresh_token, 1209600); // 14 days
      localStorage.setItem("refresh_token", refresh_token);
    }
    return data;
  } catch (error) {
    throw handleApiError(error);
  }
};

export const refreshSession = async (): Promise<{ access_token: string }> => {
  try {
    const refreshToken = getCookie("refresh_token") || localStorage.getItem("refresh_token");
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }
    const response = await axios.post<ApiResponse<AccessTokenResponse>>(
      `${env.NEXT_PUBLIC_API_URL}/auth/refresh`,
      { refresh_token: refreshToken },
      { withCredentials: true }
    );

    const data = response.data;
    if (data.success && data.data) {
      const { access_token, refresh_token: newRefreshToken } = data.data;
      setCookie("access_token", access_token, 900);
      if (newRefreshToken) {
        setCookie("refresh_token", newRefreshToken, 1209600);
        localStorage.setItem("refresh_token", newRefreshToken);
      }
      return { access_token };
    }
    throw new Error("Failed to refresh token");
  } catch (error) {
    throw handleApiError(error);
  }
};

export const logoutSession = async (): Promise<void> => {
  try {
    const state = useAuthStore.getState();
    const token = state.accessToken;
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    await axios.post(
      `${env.NEXT_PUBLIC_API_URL}/auth/logout`,
      {},
      { headers, withCredentials: true }
    );
  } catch (err) {
    console.error("Failed to revoke session on backend:", err);
  } finally {
    deleteCookie("access_token");
    deleteCookie("refresh_token");
    localStorage.removeItem("refresh_token");
  }
};
