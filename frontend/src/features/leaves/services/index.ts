import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  LeaveTypeCreateRequest,
  LeaveTypeListParams,
  LeaveTypeListResponse,
  LeaveTypeSchema,
  LeaveTypeUpdateRequest,
  LeaveSettingsSchema,
  LeaveSettingsUpdateRequest,
} from "../types";

const buildLeaveTypeQuery = (params: LeaveTypeListParams): string => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", String(params.page));
  if (params.page_size) query.append("page_size", String(params.page_size));
  if (params.search) query.append("search", params.search);
  if (params.is_active !== undefined) query.append("is_active", String(params.is_active));
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return query.toString();
};

export const leaveService = {
  /** GET /leave-types — Search, filter, and paginate leave types */
  getLeaveTypes: async (
    params: LeaveTypeListParams = {}
  ): Promise<ApiResponse<LeaveTypeListResponse>> => {
    const queryString = buildLeaveTypeQuery(params);
    const url = queryString ? `/leave-types?${queryString}` : "/leave-types";
    return apiClient.get<ApiResponse<LeaveTypeListResponse>>(url);
  },

  /** GET /leave-types/{leave_type_id} — Retrieve details of a specific leave type */
  getLeaveType: async (id: number): Promise<ApiResponse<LeaveTypeSchema>> => {
    return apiClient.get<ApiResponse<LeaveTypeSchema>>(`/leave-types/${id}`);
  },

  /** POST /leave-types — Create a new leave type definition */
  createLeaveType: async (
    data: LeaveTypeCreateRequest
  ): Promise<ApiResponse<LeaveTypeSchema>> => {
    return apiClient.post<ApiResponse<LeaveTypeSchema>>("/leave-types", data);
  },

  /** PATCH /leave-types/{leave_type_id} — Update an existing leave type */
  updateLeaveType: async (
    id: number,
    data: LeaveTypeUpdateRequest
  ): Promise<ApiResponse<LeaveTypeSchema>> => {
    return apiClient.patch<ApiResponse<LeaveTypeSchema>>(`/leave-types/${id}`, data);
  },

  /** DELETE /leave-types/{leave_type_id} — Soft-delete a leave type */
  deleteLeaveType: async (id: number): Promise<void> => {
    await apiClient.delete<void>(`/leave-types/${id}`);
  },

  /** GET /leave-settings — Retrieve organization leave cycle settings */
  getLeaveSettings: async (): Promise<ApiResponse<LeaveSettingsSchema>> => {
    return apiClient.get<ApiResponse<LeaveSettingsSchema>>("/leave-settings");
  },

  /** PUT /leave-settings — Update organization leave cycle settings */
  updateLeaveSettings: async (
    data: LeaveSettingsUpdateRequest
  ): Promise<ApiResponse<LeaveSettingsSchema>> => {
    return apiClient.put<ApiResponse<LeaveSettingsSchema>>("/leave-settings", data);
  },

  /** GET /leave-balances — Search and paginate leave balances */
  getLeaveBalances: async (
    params: import("../types").LeaveBalanceListParams = {}
  ): Promise<ApiResponse<import("../types").LeaveBalanceListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.leave_type_id) query.append("leave_type_id", String(params.leave_type_id));
    if (params.cycle_year) query.append("cycle_year", String(params.cycle_year));
    if (params.employee_id) query.append("employee_id", String(params.employee_id));
    if (params.branch_id) query.append("branch_id", String(params.branch_id));
    if (params.dept_id) query.append("dept_id", String(params.dept_id));
    const queryString = query.toString();
    const url = queryString ? `/leave-balances?${queryString}` : "/leave-balances";
    return apiClient.get<ApiResponse<import("../types").LeaveBalanceListResponse>>(url);
  },

  /** POST /employees/{id}/leave-balances/credit — Credit leave balance */
  creditLeaveBalance: async (
    employeeId: number,
    data: import("../types").LeaveCreditDebitRequest
  ): Promise<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>> => {
    return apiClient.post<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>>(
      `/employees/${employeeId}/leave-balances/credit`,
      data
    );
  },

  /** POST /employees/{id}/leave-balances/debit — Debit leave balance */
  debitLeaveBalance: async (
    employeeId: number,
    data: import("../types").LeaveCreditDebitRequest
  ): Promise<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>> => {
    return apiClient.post<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>>(
      `/employees/${employeeId}/leave-balances/debit`,
      data
    );
  },

  /** POST /employees/{id}/leave-balances/adjust — Adjust leave balance */
  adjustLeaveBalance: async (
    employeeId: number,
    data: import("../types").LeaveBalanceAdjustRequest
  ): Promise<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>> => {
    return apiClient.post<ApiResponse<import("../types").EmployeeLeaveBalanceSchema>>(
      `/employees/${employeeId}/leave-balances/adjust`,
      data
    );
  },
};
