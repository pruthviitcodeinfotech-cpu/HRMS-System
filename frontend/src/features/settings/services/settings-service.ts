import { apiClient } from "@/services/api-client/client";
import {
  ApiResponse,
  ConfigurationViewResponse,
  OrgSettingsResponse,
  OrgSettingsUpdateRequest,
  OrgSalarySlipResponse,
  OrgSalarySlipUpdateRequest,
} from "../types";

export const settingsService = {
  /** GET /settings — Fetch combined organization configuration view */
  getSettings: async (): Promise<ApiResponse<ConfigurationViewResponse>> => {
    return apiClient.get<ApiResponse<ConfigurationViewResponse>>("/settings");
  },

  /** GET /settings/organization — Fetch organization settings row */
  getOrgSettings: async (): Promise<ApiResponse<OrgSettingsResponse>> => {
    return apiClient.get<ApiResponse<OrgSettingsResponse>>("/settings/organization");
  },

  /** PATCH /settings/organization — Update organization settings */
  updateOrgSettings: async (
    data: OrgSettingsUpdateRequest
  ): Promise<ApiResponse<OrgSettingsResponse>> => {
    return apiClient.patch<ApiResponse<OrgSettingsResponse>>("/settings/organization", data);
  },

  /** GET /settings/salary-slip — Fetch salary slip settings row */
  getSalarySlipSettings: async (): Promise<ApiResponse<OrgSalarySlipResponse>> => {
    return apiClient.get<ApiResponse<OrgSalarySlipResponse>>("/settings/salary-slip");
  },

  /** PATCH /settings/salary-slip — Update salary slip settings */
  updateSalarySlipSettings: async (
    data: OrgSalarySlipUpdateRequest
  ): Promise<ApiResponse<OrgSalarySlipResponse>> => {
    return apiClient.patch<ApiResponse<OrgSalarySlipResponse>>("/settings/salary-slip", data);
  },

  /** Combined Update method to update settings */
  updateAllSettings: async (payload: {
    orgSettings?: OrgSettingsUpdateRequest;
    salarySlipSettings?: OrgSalarySlipUpdateRequest;
  }): Promise<{
    org?: OrgSettingsResponse;
    salarySlip?: OrgSalarySlipResponse;
  }> => {
    const promises: Promise<any>[] = [];
    let orgRes: ApiResponse<OrgSettingsResponse> | undefined;
    let slipRes: ApiResponse<OrgSalarySlipResponse> | undefined;

    if (payload.orgSettings && Object.keys(payload.orgSettings).length > 0) {
      promises.push(
        settingsService.updateOrgSettings(payload.orgSettings).then((res) => {
          orgRes = res;
        })
      );
    }

    if (payload.salarySlipSettings && Object.keys(payload.salarySlipSettings).length > 0) {
      promises.push(
        settingsService.updateSalarySlipSettings(payload.salarySlipSettings).then((res) => {
          slipRes = res;
        })
      );
    }

    await Promise.all(promises);

    return {
      org: orgRes?.data,
      salarySlip: slipRes?.data,
    };
  },
};
