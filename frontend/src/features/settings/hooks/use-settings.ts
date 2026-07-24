import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsService } from "../services/settings-service";
import {
  ConfigurationViewResponse,
  OrgSettingsUpdateRequest,
  OrgSalarySlipUpdateRequest,
} from "../types";
import { toast } from "sonner";

export const SETTINGS_QUERY_KEY = ["settings"];

/**
 * React Query hook to load combined settings (GET /settings).
 */
export function useSettings() {
  return useQuery({
    queryKey: SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const res = await settingsService.getSettings();
      return res.data;
    },
    staleTime: 1000 * 60 * 5, // 5 minutes stale time
  });
}

export interface UpdateSettingsPayload {
  orgSettings?: OrgSettingsUpdateRequest;
  salarySlipSettings?: OrgSalarySlipUpdateRequest;
}

/**
 * React Query mutation hook to update settings with Optimistic Updates,
 * Cache Invalidation, Error handling, and Success Toast.
 */
export function useUpdateSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: UpdateSettingsPayload) => {
      // Validate inputs if needed
      if (payload.salarySlipSettings?.company_name === "") {
        throw new Error("Company Name cannot be empty.");
      }
      return settingsService.updateAllSettings(payload);
    },

    // Optimistic Updates
    onMutate: async (newPayload: UpdateSettingsPayload) => {
      // Cancel any outgoing refetches (so they don't overwrite optimistic update)
      await queryClient.cancelQueries({ queryKey: SETTINGS_QUERY_KEY });

      // Snapshot the previous value
      const previousSettings = queryClient.getQueryData<ConfigurationViewResponse>(SETTINGS_QUERY_KEY);

      // Optimistically update the cache with new values
      if (previousSettings) {
        queryClient.setQueryData<ConfigurationViewResponse>(SETTINGS_QUERY_KEY, {
          ...previousSettings,
          organization: previousSettings.organization
            ? {
                ...previousSettings.organization,
                advance_shift_enabled: newPayload.orgSettings?.advance_shift_enabled ?? previousSettings.organization.advance_shift_enabled,
                enable_regularization: newPayload.orgSettings?.enable_regularization ?? previousSettings.organization.enable_regularization,
                enable_photo_punch: newPayload.orgSettings?.enable_photo_punch ?? previousSettings.organization.enable_photo_punch,
                device_sync_time: newPayload.orgSettings?.device_sync_time ?? previousSettings.organization.device_sync_time,
                sync_code: newPayload.orgSettings?.sync_code ?? previousSettings.organization.sync_code,
                pass_code: newPayload.orgSettings?.pass_code ?? previousSettings.organization.pass_code,
              }
            : null,
          salary_slip: previousSettings.salary_slip
            ? {
                ...previousSettings.salary_slip,
                company_name: newPayload.salarySlipSettings?.company_name ?? previousSettings.salary_slip.company_name,
                company_address: newPayload.salarySlipSettings?.company_address ?? previousSettings.salary_slip.company_address,
                company_contact: newPayload.salarySlipSettings?.company_contact ?? previousSettings.salary_slip.company_contact,
                company_website_email: newPayload.salarySlipSettings?.company_website_email ?? previousSettings.salary_slip.company_website_email,
                auto_release_payslip: newPayload.salarySlipSettings?.auto_release_payslip ?? previousSettings.salary_slip.auto_release_payslip,
                branch_wise_payslip: newPayload.salarySlipSettings?.branch_wise_payslip ?? previousSettings.salary_slip.branch_wise_payslip,
              }
            : null,
        });
      }

      return { previousSettings };
    },

    // If mutation fails, rollback to previous cached settings
    onError: (err: any, _newPayload, context) => {
      if (context?.previousSettings) {
        queryClient.setQueryData(SETTINGS_QUERY_KEY, context.previousSettings);
      }
      toast.error(err?.message || "Failed to update settings. Please check input parameters.");
    },

    // Always refetch / invalidate cache after error or success to ensure backend sync
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
    },

    onSuccess: () => {
      toast.success("Settings saved successfully");
    },
  });
}
