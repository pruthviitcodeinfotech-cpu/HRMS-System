import axios from "axios";
import { env } from "@/config/env";
import { handleApiError } from "@/services/api-client/error-handler";
import { API_TIMEOUT, HTTP_HEADERS } from "@/services/api-client/constants";
import { useAuthStore } from "@/features/auth/store";

export const axiosClient = axios.create({
  baseURL: env.NEXT_PUBLIC_API_URL,
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
axiosClient.interceptors.response.use(
  (response) => response,
  (error) => {
    return Promise.reject(handleApiError(error));
  }
);
