import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/services/api-client/error-handler";
import { profileService } from "../services/profile-service";
import { ChangePasswordInput, ProfileUpdateInput } from "../types";

export const PROFILE_QUERY_KEY = ["profile"];

/**
 * React Query hook to load the authenticated user's own profile (GET /profile).
 */
export function useProfile() {
  return useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: async () => {
      const res = await profileService.getProfile();
      return res.data;
    },
    staleTime: 1000 * 60 * 5,
  });
}

/**
 * React Query mutation hook to update the mobile number (PUT /profile).
 */
export function useUpdateProfile() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProfileUpdateInput) => profileService.updateProfile(data),
    onSuccess: (res) => {
      queryClient.setQueryData(PROFILE_QUERY_KEY, res.data);
      queryClient.invalidateQueries({ queryKey: PROFILE_QUERY_KEY });
      toast.success("Profile updated successfully");
    },
    onError: (err: ApiError) => {
      toast.error(err?.message || "Failed to update profile");
    },
  });
}

/**
 * React Query mutation hook to change the account password
 * (PUT /profile/change-password). Every other active session is revoked by
 * the backend as a side effect of a successful change.
 */
export function useChangePassword() {
  return useMutation({
    mutationFn: (data: ChangePasswordInput) => profileService.changePassword(data),
    onSuccess: (res) => {
      const revoked = res.data.revoked_session_count;
      toast.success(
        revoked > 0
          ? `Password changed successfully. ${revoked} other session(s) were logged out.`
          : "Password changed successfully."
      );
    },
    onError: (err: ApiError) => {
      toast.error(err?.message || "Failed to change password");
    },
  });
}
