import axios from "axios";
import { env } from "@/config/env";
import { handleApiError } from "@/services/api-client/error-handler";
import { API_TIMEOUT, HTTP_HEADERS } from "@/services/api-client/constants";
import { useAuthStore } from "@/features/auth/store";

export const axiosClient = axios.create({
  baseURL: `${env.NEXT_PUBLIC_API_URL}/api/v1`,
  timeout: API_TIMEOUT,
  headers: {
    [HTTP_HEADERS.CONTENT_TYPE]: "application/json",
  },
});

// Request Interceptor (injects Authorization and x-org-id headers dynamically from Zustand store)
axiosClient.interceptors.request.use(
  (config) => {
    const state = useAuthStore.getState();
    const token = state.accessToken;
    const user = state.user;

    if (token) {
      config.headers[HTTP_HEADERS.AUTHORIZATION] = `Bearer ${token}`;
    }

    if (user?.orgId) {
      config.headers[HTTP_HEADERS.X_ORG_ID] = user.orgId;
    }

    return config;
  },
  (error) => {
    return Promise.reject(handleApiError(error));
  }
);

// Response Interceptor
interface FailedRequest {
  resolve: (token: string | null) => void;
  reject: (error: unknown) => void;
}

let isRefreshing = false;
let failedQueue: FailedRequest[] = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

axiosClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Check if error is 401 Unauthorized and not already retried
    if (
      error.response &&
      error.response.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/login") &&
      !originalRequest.url?.includes("/auth/refresh")
    ) {
      if (isRefreshing) {
        return new Promise<string | null>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            originalRequest.headers[HTTP_HEADERS.AUTHORIZATION] = `Bearer ${token}`;
            return axiosClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const { refreshSession } = await import("@/features/auth/services");
        const { access_token } = await refreshSession();

        // Update Zustand auth store
        useAuthStore.getState().setSession(access_token);

        // Retry original request with the new access token
        originalRequest.headers[HTTP_HEADERS.AUTHORIZATION] = `Bearer ${access_token}`;
        processQueue(null, access_token);
        return axiosClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);
        // Clear auth store session since refresh failed (expired or invalid refresh token)
        useAuthStore.getState().clearSession();
        if (typeof window !== "undefined") {
          const currentPath = window.location.pathname + window.location.search;
          window.location.href = `/login?redirectTo=${encodeURIComponent(currentPath)}`;
        }
        return Promise.reject(handleApiError(refreshError));
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(handleApiError(error));
  }
);
