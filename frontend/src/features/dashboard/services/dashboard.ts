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
  getKPIs: async (date?: string): Promise<ApiResponse<DashboardKPIs>> => {
    const url = date ? `/dashboard/kpis?date=${date}` : "/dashboard/kpis";
    return apiClient.get<ApiResponse<DashboardKPIs>>(url);
  },

  getAttendanceSummary: async (date?: string): Promise<ApiResponse<AttendanceDashboard>> => {
    const url = date ? `/dashboard/attendance?date=${date}` : "/dashboard/attendance";
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
    if (params.branch_id) query.append("branch_id", String(params.branch_id));
    if (params.department_id) query.append("department_id", String(params.department_id));
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));

    return apiClient.get<ApiResponse<AttendanceDailyList>>(`/attendance/days?${query.toString()}`);
  },

  getShiftSummary: async (date?: string): Promise<ApiResponse<ShiftSummaryResponse>> => {
    const url = date ? `/dashboard/shifts?date=${date}` : "/dashboard/shifts";
    return apiClient.get<ApiResponse<ShiftSummaryResponse>>(url);
  },

  getDepartmentAttendance: async (date?: string): Promise<ApiResponse<DepartmentAttendanceChart>> => {
    const url = date
      ? `/dashboard/charts/department-attendance?date=${date}`
      : "/dashboard/charts/department-attendance";
    return apiClient.get<ApiResponse<DepartmentAttendanceChart>>(url);
  },

  getDevices: async (params?: {
    page?: number;
    page_size?: number;
    status?: "online" | "offline";
  }): Promise<ApiResponse<BiometricDeviceList>> => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", String(params.page));
    if (params?.page_size) query.append("page_size", String(params.page_size));
    if (params?.status) query.append("status", params.status);
    
    const queryString = query.toString();
    const url = queryString ? `/devices?${queryString}` : "/devices";
    return apiClient.get<ApiResponse<BiometricDeviceList>>(url);
  },

  getApprovals: async (): Promise<ApiResponse<ApprovalDashboard>> => {
    return apiClient.get<ApiResponse<ApprovalDashboard>>("/dashboard/approvals");
  },

  getPendingBiometrics: async (params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<ApiResponse<{ items: Array<{ employee_id: number; employee_name: string }> }>> => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", String(params.page));
    if (params?.page_size) query.append("page_size", String(params.page_size));
    if (params?.search) query.append("search", params.search);
    
    return apiClient.get<ApiResponse<any>>(`/dashboard/biometrics/pending?${query.toString()}`);
  },

  approveRequest: async (id: number, remarks: string = ""): Promise<ApiResponse<unknown>> => {
    return apiClient.post<ApiResponse<unknown>>(`/approvals/${id}/approve`, { remarks });
  },

  rejectRequest: async (id: number, remarks: string = ""): Promise<ApiResponse<unknown>> => {
    return apiClient.post<ApiResponse<unknown>>(`/approvals/${id}/reject`, { reject_remarks: remarks });
  },
};
