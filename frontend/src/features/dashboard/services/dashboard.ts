import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  DashboardKPIs,
  AttendanceDashboard,
  AttendanceDailyList,
  ShiftSummaryResponse,
  DepartmentAttendanceChart,
  BiometricDeviceList,
  ApprovalDashboard,
} from "../types";

export const dashboardService = {
  getKPIs: async (date?: string, branch_id?: number | null): Promise<ApiResponse<DashboardKPIs>> => {
    const query = new URLSearchParams();
    if (date) query.append("date", date);
    if (branch_id !== undefined && branch_id !== null) query.append("branch_id", String(branch_id));
    const queryString = query.toString();
    const url = queryString ? `/dashboard/kpis?${queryString}` : "/dashboard/kpis";
    return apiClient.get<ApiResponse<DashboardKPIs>>(url);
  },

  getAttendanceSummary: async (date?: string, branch_id?: number | null): Promise<ApiResponse<AttendanceDashboard>> => {
    const query = new URLSearchParams();
    if (date) query.append("date", date);
    if (branch_id !== undefined && branch_id !== null) query.append("branch_id", String(branch_id));
    const queryString = query.toString();
    const url = queryString ? `/dashboard/attendance?${queryString}` : "/dashboard/attendance";
    return apiClient.get<ApiResponse<AttendanceDashboard>>(url);
  },

  getAttendanceDays: async (params: {
    date: string;
    branch_id?: number | null;
    department_id?: number | null;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<AttendanceDailyList>> => {
    const query = new URLSearchParams();
    query.append("date", params.date);
    if (params.branch_id !== undefined && params.branch_id !== null) query.append("branch_id", String(params.branch_id));
    if (params.department_id !== undefined && params.department_id !== null) query.append("department_id", String(params.department_id));
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));

    return apiClient.get<ApiResponse<AttendanceDailyList>>(`/attendance/days?${query.toString()}`);
  },

  getShiftSummary: async (date?: string, branch_id?: number | null): Promise<ApiResponse<ShiftSummaryResponse>> => {
    const query = new URLSearchParams();
    if (date) query.append("date", date);
    if (branch_id !== undefined && branch_id !== null) query.append("branch_id", String(branch_id));
    const queryString = query.toString();
    const url = queryString ? `/dashboard/shifts?${queryString}` : "/dashboard/shifts";
    return apiClient.get<ApiResponse<ShiftSummaryResponse>>(url);
  },

  getDepartmentAttendance: async (date?: string, branch_id?: number | null): Promise<ApiResponse<DepartmentAttendanceChart>> => {
    const query = new URLSearchParams();
    if (date) query.append("date", date);
    if (branch_id !== undefined && branch_id !== null) query.append("branch_id", String(branch_id));
    const queryString = query.toString();
    const url = queryString
      ? `/dashboard/charts/department-attendance?${queryString}`
      : "/dashboard/charts/department-attendance";
    return apiClient.get<ApiResponse<DepartmentAttendanceChart>>(url);
  },

  getDevices: async (params?: {
    page?: number;
    page_size?: number;
    status?: "online" | "offline";
    branch_id?: number | null;
  }): Promise<ApiResponse<BiometricDeviceList>> => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", String(params.page));
    if (params?.page_size) query.append("page_size", String(params.page_size));
    if (params?.status) query.append("status", params.status);
    if (params?.branch_id !== undefined && params?.branch_id !== null) query.append("branch_id", String(params.branch_id));
    
    const queryString = query.toString();
    const url = queryString ? `/devices?${queryString}` : "/devices";
    return apiClient.get<ApiResponse<BiometricDeviceList>>(url);
  },

  getApprovals: async (branch_id?: number | null): Promise<ApiResponse<ApprovalDashboard>> => {
    const query = new URLSearchParams();
    if (branch_id !== undefined && branch_id !== null) query.append("branch_id", String(branch_id));
    const queryString = query.toString();
    const url = queryString ? `/dashboard/approvals?${queryString}` : "/dashboard/approvals";
    return apiClient.get<ApiResponse<ApprovalDashboard>>(url);
  },

  getPendingBiometrics: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
    branch_id?: number | null;
  }): Promise<ApiResponse<{ items: Array<{ employee_id: number; employee_name: string }> }>> => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", String(params.page));
    if (params?.page_size) query.append("page_size", String(params.page_size));
    if (params?.search) query.append("search", params.search);
    if (params?.branch_id !== undefined && params?.branch_id !== null) query.append("branch_id", String(params.branch_id));
    
    return apiClient.get<ApiResponse<any>>(`/dashboard/biometrics/pending?${query.toString()}`);
  },

  approveRequest: async (id: number, remarks: string = ""): Promise<ApiResponse<unknown>> => {
    return apiClient.post<ApiResponse<unknown>>(`/approvals/${id}/approve`, { remarks });
  },

  rejectRequest: async (id: number, remarks: string = ""): Promise<ApiResponse<unknown>> => {
    return apiClient.post<ApiResponse<unknown>>(`/approvals/${id}/reject`, { reject_remarks: remarks });
  },
};
