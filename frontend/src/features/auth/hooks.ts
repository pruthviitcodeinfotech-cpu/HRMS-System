import { useContext } from "react";
import { useMutation } from "@tanstack/react-query";
import { AuthContext } from "./context";
import { apiClient } from "@/services/api-client/client";
import { AUTH_ENDPOINTS } from "@/services/api-client/constants";
import { LoginPayload, LoginResponseData, ApiResponse, setCookie } from "./services";

export const useLogin = () => {
  return useMutation<
    ApiResponse<LoginResponseData>,
    Error,
    { payload: LoginPayload; orgId: string }
  >({
    mutationFn: async ({ payload, orgId }) => {
      const response = await apiClient.post<ApiResponse<LoginResponseData>>(
        AUTH_ENDPOINTS.LOGIN,
        payload,
        {
          headers: {
            "x-org-id": orgId,
          },
        }
      );

      if (response.success && response.data) {
        const { access_token, refresh_token } = response.data;
        setCookie("access_token", access_token, 900); // 15 mins
        setCookie("refresh_token", refresh_token, 1209600); // 14 days
        localStorage.setItem("refresh_token", refresh_token);
      }

      return response;
    },
  });
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const usePermission = (feature: string, action: "create" | "read" | "edit" | "delete") => {
  const { user } = useAuth();

  if (!user) return false;
  if (user.isSuperAdmin) return true;

  const permission = user.permissions.find((p) => p.feature_key === feature);
  if (!permission) return false;

  switch (action) {
    case "create":
      return permission.can_create;
    case "read":
      return permission.can_read;
    case "edit":
      return permission.can_edit;
    case "delete":
      return permission.can_delete;
    default:
      return false;
  }
};
