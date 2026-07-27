import { apiClient } from "@/services/api-client/client";
import {
  ApiResponse,
  ChangePasswordInput,
  ChangePasswordResult,
  ProfileData,
  ProfileUpdateInput,
} from "../types";

export const profileService = {
  /** GET /profile — Fetch the authenticated user's own profile */
  getProfile: async (): Promise<ApiResponse<ProfileData>> => {
    return apiClient.get<ApiResponse<ProfileData>>("/profile");
  },

  /** PUT /profile — Update the mobile number (the only editable field) */
  updateProfile: async (data: ProfileUpdateInput): Promise<ApiResponse<ProfileData>> => {
    return apiClient.put<ApiResponse<ProfileData>>("/profile", data);
  },

  /** PUT /profile/change-password — Verify current password and set a new one */
  changePassword: async (
    data: ChangePasswordInput
  ): Promise<ApiResponse<ChangePasswordResult>> => {
    return apiClient.put<ApiResponse<ChangePasswordResult>>("/profile/change-password", data);
  },
};
