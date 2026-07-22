import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  PayrollGroup,
  PayrollCycle,
  PayrollRecord,
  AttendanceAdjustment,
  FinalizedPayrollRun,
  EmployeeGroupAssignment,
} from "../types";

export const payrollService = {
  // 1. Payroll Groups
  getGroups: async (params?: { page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<{ items: PayrollGroup[]; pagination: any }>>(
      `/payroll/groups${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  createGroup: async (data: Partial<PayrollGroup>) => {
    return apiClient.post<ApiResponse<PayrollGroup>>("/payroll/groups", data);
  },

  updateGroup: async (id: number, data: Partial<PayrollGroup>) => {
    return apiClient.patch<ApiResponse<PayrollGroup>>(`/payroll/groups/${id}`, data);
  },

  deleteGroup: async (id: number) => {
    return apiClient.delete<void>(`/payroll/groups/${id}`);
  },

  // 2. Employee Group Assignment
  assignEmployeeGroup: async (employeeId: number, data: { payroll_group_id: number; effective_from?: string }) => {
    return apiClient.put<ApiResponse<EmployeeGroupAssignment>>(`/employees/${employeeId}/payroll-group`, data);
  },

  // 3. Payroll Cycles
  getCycles: async (params?: { group_id?: number; is_finalized?: boolean; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.group_id) query.append("payroll_group_id", params.group_id.toString());
    if (params?.is_finalized !== undefined) query.append("is_finalized", String(params.is_finalized));
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<{ items: PayrollCycle[]; pagination: any }>>(
      `/payroll/cycles${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  createCycle: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string; payroll_date: string }) => {
    return apiClient.post<ApiResponse<PayrollCycle>>("/payroll/cycles", data);
  },

  // 4. Payroll Processing
  generatePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<any>>("/payroll/processing/generate", data);
  },

  previewPayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<{ items: PayrollRecord[] }>>("/payroll/processing/preview", data);
  },

  recalculatePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<any>>("/payroll/processing/recalculate", data);
  },

  finalizePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<FinalizedPayrollRun>>("/payroll/processing/finalize", data);
  },

  // 5. Finalized Payroll Runs
  getFinalizedRuns: async (params?: { page?: number; page_size?: number; payroll_group_id?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    if (params?.payroll_group_id) query.append("payroll_group_id", params.payroll_group_id.toString());
    return apiClient.get<ApiResponse<{ items: FinalizedPayrollRun[]; pagination: any }>>(
      `/payroll/finalized-runs${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  recordPayment: async (runId: number, data: { payment_date: string; payment_reference?: string; remarks?: string }) => {
    return apiClient.post<ApiResponse<FinalizedPayrollRun>>(`/payroll/finalized-runs/${runId}/payment`, data);
  },

  // 6. Attendance Adjustments
  getAdjustments: async (params?: { employee_id?: number; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.employee_id) query.append("employee_id", params.employee_id.toString());
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<{ items: AttendanceAdjustment[]; pagination: any }>>(
      `/payroll/adjustments${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  addAdjustment: async (data: Partial<AttendanceAdjustment>) => {
    return apiClient.post<ApiResponse<AttendanceAdjustment>>("/payroll/adjustments", data);
  },

  addPenalty: async (data: { employee_id: number; date: string; penalty_amount: number; reason: string }) => {
    return apiClient.post<ApiResponse<any>>("/payroll/adjustments/penalties", data);
  },

  addExtraHours: async (data: { employee_id: number; date: string; extra_hours: number; reason: string }) => {
    return apiClient.post<ApiResponse<any>>("/payroll/adjustments/extra-hours", data);
  },

  deleteAdjustment: async (id: number) => {
    return apiClient.delete<void>(`/payroll/adjustments/${id}`);
  },
};
