import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsService } from "../services/settings-service";
import {
  ConfigurationViewResponse,
  OrgSettingsUpdateRequest,
  OrgSalarySlipUpdateRequest,
  PayrollSettingUpdateRequest,
} from "../types";
import { toast } from "sonner";

export const SETTINGS_QUERY_KEY = ["settings"];
export const PAYROLL_SETTINGS_QUERY_KEY = ["payroll-settings"];

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

/**
 * React Query hook to load payroll calculation settings (GET /payroll/settings).
 */
export function usePayrollSettings() {
  return useQuery({
    queryKey: PAYROLL_SETTINGS_QUERY_KEY,
    queryFn: async () => {
      const res = await settingsService.getPayrollSettings();
      return res.data;
    },
    staleTime: 1000 * 60 * 5,
  });
}

export interface UpdateSettingsPayload {
  orgSettings?: OrgSettingsUpdateRequest;
  salarySlipSettings?: OrgSalarySlipUpdateRequest;
  payrollSettings?: PayrollSettingUpdateRequest;
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
      await queryClient.cancelQueries({ queryKey: PAYROLL_SETTINGS_QUERY_KEY });

      // Snapshot the previous values
      const previousSettings = queryClient.getQueryData<ConfigurationViewResponse>(SETTINGS_QUERY_KEY);
      const previousPayroll = queryClient.getQueryData<any>(PAYROLL_SETTINGS_QUERY_KEY);

      // Optimistically update org + salary slip cache
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

      // Optimistically update payroll cache
      if (previousPayroll && newPayload.payrollSettings) {
        queryClient.setQueryData(PAYROLL_SETTINGS_QUERY_KEY, {
          ...previousPayroll,
          ...Object.fromEntries(
            Object.entries(newPayload.payrollSettings).filter(([, v]) => v !== undefined)
          ),
        });
      }

      return { previousSettings, previousPayroll };
    },

    // If mutation fails, rollback to previous cached settings
    onError: (err: any, _newPayload, context) => {
      if (context?.previousSettings) {
        queryClient.setQueryData(SETTINGS_QUERY_KEY, context.previousSettings);
      }
      if (context?.previousPayroll) {
        queryClient.setQueryData(PAYROLL_SETTINGS_QUERY_KEY, context.previousPayroll);
      }
      toast.error(err?.message || "Failed to update settings. Please check input parameters.");
    },

    // Always refetch / invalidate cache after error or success to ensure backend sync
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: SETTINGS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: PAYROLL_SETTINGS_QUERY_KEY });
    },

    onSuccess: () => {
      toast.success("Settings saved successfully");
    },
  });
}
