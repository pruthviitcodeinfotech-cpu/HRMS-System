import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  LoanAdvanceCreatePayload,
  LoanAdvanceDetailsSchema,
  LoanAdvanceListParams,
  LoanAdvanceListResponse,
  LoanAdvanceLogsParams,
  LoanAdvanceSchema,
  LoanAdvanceTransactionCreatePayload,
  LoanAdvanceTransactionListResponse,
  LoanAdvanceTransactionSchema,
  LoanAdvanceUpdatePayload,
} from "../types";

const BASE_URL = "/loan-advance";

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

export const loanAdvanceService = {
  getLoansAdvances: async (
    params: LoanAdvanceListParams = {}
  ): Promise<ApiResponse<LoanAdvanceListResponse>> => {
    const query = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<LoanAdvanceListResponse>>(`${BASE_URL}${query}`);
  },

  getLoanAdvanceById: async (
    id: number
  ): Promise<ApiResponse<LoanAdvanceDetailsSchema>> => {
    return apiClient.get<ApiResponse<LoanAdvanceDetailsSchema>>(`${BASE_URL}/${id}`);
  },

  createLoanAdvance: async (
    payload: LoanAdvanceCreatePayload
  ): Promise<ApiResponse<LoanAdvanceSchema>> => {
    return apiClient.post<ApiResponse<LoanAdvanceSchema>>(BASE_URL, payload);
  },

  updateLoanAdvance: async (
    id: number,
    payload: LoanAdvanceUpdatePayload
  ): Promise<ApiResponse<LoanAdvanceSchema>> => {
    return apiClient.put<ApiResponse<LoanAdvanceSchema>>(`${BASE_URL}/${id}`, payload);
  },

  closeLoanAdvance: async (
    id: number
  ): Promise<ApiResponse<LoanAdvanceSchema>> => {
    return apiClient.post<ApiResponse<LoanAdvanceSchema>>(`${BASE_URL}/${id}/close`);
  },

  deleteLoanAdvance: async (id: number): Promise<void> => {
    return apiClient.delete<void>(`${BASE_URL}/${id}`);
  },

  getLoanAdvanceLogs: async (
    params: LoanAdvanceLogsParams = {}
  ): Promise<ApiResponse<LoanAdvanceTransactionListResponse>> => {
    const query = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<LoanAdvanceTransactionListResponse>>(`${BASE_URL}/logs${query}`);
  },

  addTransaction: async (
    id: number,
    payload: LoanAdvanceTransactionCreatePayload
  ): Promise<ApiResponse<LoanAdvanceTransactionSchema>> => {
    return apiClient.post<ApiResponse<LoanAdvanceTransactionSchema>>(
      `/loans-advances/${id}/transactions`,
      payload
    );
  },

  getActiveLoansForEmployee: async (
    employeeId: number
  ): Promise<ApiResponse<LoanAdvanceSchema[]>> => {
    return apiClient.get<ApiResponse<LoanAdvanceSchema[]>>(`/loans/${employeeId}/active`);
  },

  submitLoanTransaction: async (payload: {
    loan_id: number;
    transaction_type: string;
    amount: number;
    comment: string;
    transaction_date: string;
  }): Promise<ApiResponse<LoanAdvanceTransactionSchema>> => {
    return apiClient.post<ApiResponse<LoanAdvanceTransactionSchema>>(
      "/loan-transactions",
      payload
    );
  },
  getLoanTransactions: async (
    params: LoanAdvanceLogsParams = {}
  ): Promise<ApiResponse<LoanAdvanceTransactionListResponse>> => {
    const query = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<LoanAdvanceTransactionListResponse>>(`/loan-transactions${query}`);
  },
  updateInstallment: async (
    loanId: number,
    payload: { installment_amount: number }
  ): Promise<ApiResponse<LoanAdvanceSchema>> => {
    return apiClient.patch<ApiResponse<LoanAdvanceSchema>>(
      `/loans/${loanId}/installment`,
      payload
    );
  },
};


