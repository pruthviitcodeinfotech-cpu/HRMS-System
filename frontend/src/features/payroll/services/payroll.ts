import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  PayrollGroupItem,
  PayrollGroupCreatePayload,
  PayrollGroupUpdatePayload,
  PayrollGroupAssignEmployeesPayload,
  GroupEmployeesResponse,
  PayrollCycle,
  PayrollRecord,
  AttendanceAdjustment,
  FinalizedPayrollRun,
  EmployeeGroupAssignment,
  FinalizedPayrollItem,
  FinalizedPayrollPayPayload,
} from "../types";

export const payrollService = {
  // 1. Payroll Groups
  getGroups: async (params?: {
    search?: string;
    payroll_type?: string;
    is_default?: boolean;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    if (params?.search) query.append("search", params.search);
    if (params?.payroll_type) query.append("payroll_type", params.payroll_type);
    if (params?.is_default !== undefined) query.append("is_default", String(params.is_default));
    if (params?.sort_by) query.append("sort_by", params.sort_by);
    if (params?.sort_order) query.append("sort_order", params.sort_order);
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<{ items: PayrollGroupItem[]; meta: Record<string, unknown> }>>(
      `/payroll-groups${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  getGroupDetails: async (id: number) => {
    return apiClient.get<ApiResponse<PayrollGroupItem>>(`/payroll-groups/${id}`);
  },

  createGroup: async (data: PayrollGroupCreatePayload) => {
    return apiClient.post<ApiResponse<PayrollGroupItem>>("/payroll-groups", data);
  },

  updateGroup: async (id: number, data: PayrollGroupUpdatePayload) => {
    return apiClient.put<ApiResponse<PayrollGroupItem>>(`/payroll-groups/${id}`, data);
  },

  deleteGroup: async (id: number) => {
    return apiClient.delete<void>(`/payroll-groups/${id}`);
  },

  assignEmployeesToGroup: async (groupId: number, data: PayrollGroupAssignEmployeesPayload) => {
    return apiClient.post<ApiResponse<{ assigned_count: number }>>(`/payroll-groups/${groupId}/assign`, data);
  },

  getGroupEmployees: async (groupId: number, params?: { page?: number; page_size?: number; search?: string }) => {
    const query = new URLSearchParams();
    if (params?.search) query.append("search", params.search);
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<GroupEmployeesResponse>>(
      `/payroll-groups/${groupId}/employees${query.toString() ? `?${query.toString()}` : ""}`
    );
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
    return apiClient.get<ApiResponse<{ items: PayrollCycle[]; pagination: Record<string, unknown> }>>(
      `/payroll/cycles${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  createCycle: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string; payroll_date: string }) => {
    return apiClient.post<ApiResponse<PayrollCycle>>("/payroll/cycles", data);
  },

  // 4. Payroll Processing
  generatePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/processing/generate", data);
  },

  previewPayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<{ items: PayrollRecord[] }>>("/payroll/processing/preview", data);
  },

  recalculatePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/processing/recalculate", data);
  },

  finalizePayroll: async (data: { payroll_group_id: number; cycle_start_date: string; cycle_end_date: string }) => {
    return apiClient.post<ApiResponse<FinalizedPayrollRun>>("/payroll/processing/finalize", data);
  },

  // 5. Finalized Payroll Runs & History
  getFinalizedRuns: async (params?: { page?: number; page_size?: number; payroll_group_id?: number }) => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    if (params?.payroll_group_id) query.append("payroll_group_id", params.payroll_group_id.toString());
    return apiClient.get<ApiResponse<{ items: FinalizedPayrollRun[]; pagination: Record<string, unknown> }>>(
      `/payroll/finalized-runs${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  recordPayment: async (runId: number, data: { payment_date: string; payment_reference?: string; remarks?: string }) => {
    return apiClient.post<ApiResponse<FinalizedPayrollRun>>(`/payroll/finalized-runs/${runId}/payment`, data);
  },

  // 5.1 Finalized Payroll History Engine APIs
  getFinalizedPayroll: async (params?: {
    page?: number;
    page_size?: number;
    payroll_group_id?: number;
    from_date?: string;
    to_date?: string;
    status?: string;
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    if (params?.payroll_group_id) query.append("payroll_group_id", params.payroll_group_id.toString());
    if (params?.from_date) query.append("from_date", params.from_date);
    if (params?.to_date) query.append("to_date", params.to_date);
    if (params?.status) query.append("status", params.status);

    return apiClient.get<ApiResponse<{ items: FinalizedPayrollItem[]; pagination: Record<string, unknown> }>>(
      `/finalized-payroll${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  getFinalizedPayrollDetails: async (id: number) => {
    return apiClient.get<ApiResponse<FinalizedPayrollItem>>(`/finalized-payroll/${id}`);
  },

  payFinalizedPayroll: async (id: number, payload?: FinalizedPayrollPayPayload) => {
    return apiClient.post<ApiResponse<FinalizedPayrollItem>>(`/finalized-payroll/${id}/pay`, payload || {});
  },

  // 6. Attendance Adjustments
  getAdjustments: async (params?: { employee_id?: number; page?: number; page_size?: number }) => {
    const query = new URLSearchParams();
    if (params?.employee_id) query.append("employee_id", params.employee_id.toString());
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    return apiClient.get<ApiResponse<{ items: AttendanceAdjustment[]; pagination: Record<string, unknown> }>>(
      `/payroll/adjustments${query.toString() ? `?${query.toString()}` : ""}`
    );
  },

  addAdjustment: async (data: Partial<AttendanceAdjustment>) => {
    return apiClient.post<ApiResponse<AttendanceAdjustment>>("/payroll/adjustments", data);
  },

  addPenalty: async (data: { employee_id: number; date: string; penalty_amount: number; reason: string }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/adjustments/penalties", data);
  },

  addExtraHours: async (data: { employee_id: number; date: string; extra_hours: number; reason: string }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/adjustments/extra-hours", data);
  },

  deleteAdjustment: async (id: number) => {
    return apiClient.delete<void>(`/payroll/adjustments/${id}`);
  },

  // 7. Bulk Attendance Adjustments (Phase 2)
  getBulkAttendanceMatrix: async (params: {
    date_from: string;
    date_to: string;
    branch_id?: number;
    dept_id?: number;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    query.append("date_from", params.date_from);
    query.append("date_to", params.date_to);
    if (params.branch_id) query.append("branch_id", params.branch_id.toString());
    if (params.dept_id) query.append("dept_id", params.dept_id.toString());
    if (params.search) query.append("search", params.search);
    if (params.page) query.append("page", params.page.toString());
    if (params.page_size) query.append("page_size", params.page_size.toString());

    return apiClient.get<ApiResponse<{ dates: string[]; items: Record<string, unknown>[]; pagination: Record<string, unknown> }>>(
      `/payroll/bulk-attendance-adjustments?${query.toString()}`
    );
  },

  batchUpdateBulkAttendanceAdjustments: async (data: {
    date_from?: string;
    date_to?: string;
    updates: {
      employee_id: number;
      attendance_date: string;
      adjusted_status: string;
      original_status?: string | null;
      reason?: string | null;
    }[];
  }) => {
    return apiClient.put<ApiResponse<{ updated_count: number; message: string }>>(
      "/payroll/bulk-attendance-adjustments",
      data
    );
  },

  resetBulkAttendanceAdjustments: async (data: {
    date_from: string;
    date_to: string;
    branch_id?: number;
    employee_ids?: number[];
  }) => {
    return apiClient.post<ApiResponse<{ reset_count: number }>>(
      "/payroll/bulk-attendance-adjustments/reset",
      data
    );
  },

  // 8. Process Payroll APIs (Phase 3 Integration)
  getProcessPayrollMatrix: async (params: {
    date_from: string;
    date_to: string;
    payroll_group_id?: number;
    branch_id?: number;
    dept_id?: number;
    search?: string;
    page?: number;
    page_size?: number;
  }) => {
    const query = new URLSearchParams();
    query.append("date_from", params.date_from);
    query.append("date_to", params.date_to);
    if (params.payroll_group_id) query.append("payroll_group_id", params.payroll_group_id.toString());
    if (params.branch_id) query.append("branch_id", params.branch_id.toString());
    if (params.dept_id) query.append("dept_id", params.dept_id.toString());
    if (params.search) query.append("search", params.search);
    if (params.page) query.append("page", params.page.toString());
    if (params.page_size) query.append("page_size", params.page_size.toString());

    return apiClient.get<ApiResponse<{ items: Record<string, unknown>[]; pagination: Record<string, unknown> }>>(
      `/payroll/process?${query.toString()}`
    );
  },

  calculateProcessPayroll: async (data: {
    payroll_group_id: number;
    cycle_from: string;
    cycle_to: string;
    employee_ids?: number[];
  }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/process/calculate", data);
  },

  finalizeProcessPayroll: async (data: {
    payroll_group_id: number;
    cycle_from: string;
    cycle_to: string;
  }) => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/payroll/process/finalize", data);
  },

  getProcessPayrollEmployeeDetail: async (
    employeeId: number,
    params: { date_from: string; date_to: string }
  ) => {
    const query = new URLSearchParams();
    query.append("date_from", params.date_from);
    query.append("date_to", params.date_to);
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/payroll/process/${employeeId}?${query.toString()}`);
  },

  exportProcessPayroll: async (params: {
    date_from: string;
    date_to: string;
    payroll_group_id?: number;
    branch_id?: number;
    dept_id?: number;
  }) => {
    const query = new URLSearchParams();
    query.append("date_from", params.date_from);
    query.append("date_to", params.date_to);
    if (params.payroll_group_id) query.append("payroll_group_id", params.payroll_group_id.toString());
    if (params.branch_id) query.append("branch_id", params.branch_id.toString());
    if (params.dept_id) query.append("dept_id", params.dept_id.toString());

    return apiClient.get<ArrayBuffer>(`/payroll/process/export?${query.toString()}`, {
      responseType: "arraybuffer",
    });
  },
};
