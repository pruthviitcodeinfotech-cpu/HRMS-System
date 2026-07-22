import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  ArrearsCreatePayload,
  ArrearsDetailsSchema,
  ArrearsListParams,
  ArrearsListResponse,
  ArrearsLogsParams,
  ArrearsPayPayload,
  ArrearsSchema,
  ArrearsTransactionListResponse,
  ArrearsTransactionSchema,
  ArrearsUpdatePayload,
} from "../types";

const BASE_URL = "/arrears";

const buildQueryString = (params: Record<string, unknown>): string => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "" && val !== "all") {
      query.append(key, String(val));
    }
  });
  const str = query.toString();
  return str ? `?${str}` : "";
};

export const arrearsService = {
  getArrears: async (
    params: ArrearsListParams = {}
  ): Promise<ApiResponse<ArrearsListResponse>> => {
    const query = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<ArrearsListResponse>>(`${BASE_URL}${query}`);
  },

  getArrearsById: async (
    id: number
  ): Promise<ApiResponse<ArrearsDetailsSchema>> => {
    return apiClient.get<ApiResponse<ArrearsDetailsSchema>>(`${BASE_URL}/${id}`);
  },

  createArrears: async (
    payload: ArrearsCreatePayload
  ): Promise<ApiResponse<ArrearsSchema>> => {
    return apiClient.post<ApiResponse<ArrearsSchema>>(BASE_URL, payload);
  },

  updateArrears: async (
    id: number,
    payload: ArrearsUpdatePayload
  ): Promise<ApiResponse<ArrearsSchema>> => {
    return apiClient.put<ApiResponse<ArrearsSchema>>(`${BASE_URL}/${id}`, payload);
  },

  deleteArrears: async (id: number): Promise<void> => {
    return apiClient.delete<void>(`${BASE_URL}/${id}`);
  },

  payArrears: async (
    id: number,
    payload: ArrearsPayPayload
  ): Promise<ApiResponse<ArrearsTransactionSchema>> => {
    return apiClient.post<ApiResponse<ArrearsTransactionSchema>>(`${BASE_URL}/${id}/pay`, payload);
  },

  getArrearsLogs: async (
    params: ArrearsLogsParams = {}
  ): Promise<ApiResponse<ArrearsTransactionListResponse>> => {
    const query = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<ArrearsTransactionListResponse>>(`${BASE_URL}/logs${query}`);
  },
};
