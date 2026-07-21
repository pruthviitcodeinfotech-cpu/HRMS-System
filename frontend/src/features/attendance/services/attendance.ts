import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";

export interface AttendanceDayItemSchema {
  id?: number | null;
  attendance_date?: string | null;
  employee_id: number;
  status: string;
  first_in: string | null;
  last_out: string | null;
  worked_minutes: number;
  late_minutes: number;
  overtime_minutes: number;
  is_locked: boolean;
  is_on_break: boolean;
  employee_code?: string | null;
  employee_name?: string | null;
  department_name?: string | null;
  designation?: string | null;
  first_punch?: string | null;
  last_punch?: string | null;
  working_hours?: number | null;
  break_hours?: number | null;
  overtime?: number | null;
  shift_id?: number | null;
  shift_name?: string | null;
}

export interface AttendanceDailyListResponse {
  items: AttendanceDayItemSchema[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export interface AttendanceDailyQueryParams {
  date?: string;
  date_from?: string;
  date_to?: string;
  branch_id?: number;
  department_id?: number;
  shift_id?: number;
  page?: number;
  page_size?: number;
}

export interface AttendanceDailySummaryParams {
  date: string;
  branch_id?: number;
  department_id?: number;
  shift_id?: number;
}

export interface AttendanceMonthlySummaryParams {
  month: number;
  year: number;
  employee_id?: number;
  branch_id?: number;
  department_id?: number;
  shift_id?: number;
}

export interface AttendancePunchesQueryParams {
  from: string;
  to: string;
  employee_id?: number;
  device_id?: number;
  page?: number;
  page_size?: number;
}

export interface AttendancePunchSchema {
  id: number;
  org_id: number;
  employee_id: number;
  attendance_day_id: number;
  punch_type: string;
  punch_time: string;
  sequence_no: number;
  punch_source: string;
  device_id?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  is_valid: boolean;
  created_at: string;
}

export interface AttendancePunchesResponse {
  items: AttendancePunchSchema[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export interface ManualPunchPayload {
  employee_id: number;
  punch_time: string;
  punch_type: "in" | "out" | "break_in" | "break_out";
  latitude?: number;
  longitude?: number;
}

export interface ManualAttendancePayload {
  employee_id: number;
  date: string;
  in_time: string;
  out_time: string;
  reason: string;
}

export interface AttendanceCorrectionPayload {
  employee_id: number;
  date: string;
  requested_in: string;
  requested_out: string;
  reason: string;
}

export interface AttendanceCorrectionApprovePayload {
  decision: "approved" | "rejected";
  comment?: string;
}

export interface AttendanceCorrectionSchema {
  id: number;
  employee_id: number;
  date: string;
  old_punch_time?: string | null;
  new_punch_time: string;
  employee_reason?: string | null;
  applied_on: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  updated_at: string;
}

export interface AttendanceLockPayload {
  period_start: string;
  period_end: string;
  scope: "company" | "branch";
  branch_id?: number;
  reason?: string;
}

export interface AttendanceUnlockPayload {
  period_start: string;
  period_end: string;
  scope: "company" | "branch";
  branch_id?: number;
  reason?: string;
}

export interface AttendanceLockSchema {
  id: number;
  org_id: number;
  lock_month: number;
  lock_year: number;
  lock_type: string;
  branch_id?: number | null;
  status: string;
  locked_by: number;
  locked_at: string;
  reason?: string | null;
  created_at: string;
  updated_at: string;
}

const buildQueryString = (params?: object): string => {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params as Record<string, unknown>).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, String(value));
    }
  });
  return query.toString();
};

export const attendanceService = {
  // GET /attendance/days
  getAttendanceDays: async (
    params: AttendanceDailyQueryParams
  ): Promise<ApiResponse<AttendanceDailyListResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<AttendanceDailyListResponse>>(
      q ? `/attendance/days?${q}` : "/attendance/days"
    );
  },

  // GET /attendance/summary/daily
  getDailySummary: async (
    params: AttendanceDailySummaryParams
  ): Promise<ApiResponse<Record<string, unknown>>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<Record<string, unknown>>>(`/attendance/summary/daily?${q}`);
  },

  // GET /attendance/summary/monthly
  getMonthlySummary: async (
    params: AttendanceMonthlySummaryParams
  ): Promise<ApiResponse<Record<string, unknown>[]>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<Record<string, unknown>[]>>(
      `/attendance/summary/monthly?${q}`
    );
  },

  // GET /attendance/punches
  getAttendancePunches: async (
    params: AttendancePunchesQueryParams
  ): Promise<ApiResponse<AttendancePunchesResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<AttendancePunchesResponse>>(`/attendance/punches?${q}`);
  },

  // POST /attendance/punches
  addManualPunch: async (
    payload: ManualPunchPayload
  ): Promise<ApiResponse<AttendancePunchSchema>> => {
    const q = buildQueryString({
      employee_id: payload.employee_id,
      punch_time: payload.punch_time,
      punch_type: payload.punch_type,
      latitude: payload.latitude,
      longitude: payload.longitude,
    });
    return apiClient.post<ApiResponse<AttendancePunchSchema>>(`/attendance/punches?${q}`, {});
  },

  // POST /attendance/manual
  createManualAttendance: async (
    payload: ManualAttendancePayload
  ): Promise<ApiResponse<Record<string, unknown>>> => {
    return apiClient.post<ApiResponse<Record<string, unknown>>>("/attendance/manual", payload);
  },

  // POST /attendance/corrections
  requestCorrection: async (
    payload: AttendanceCorrectionPayload
  ): Promise<ApiResponse<AttendanceCorrectionSchema>> => {
    return apiClient.post<ApiResponse<AttendanceCorrectionSchema>>(
      "/attendance/corrections",
      payload
    );
  },

  // PUT /attendance/corrections/{request_id}/approve
  approveCorrection: async (
    requestId: number,
    payload: AttendanceCorrectionApprovePayload
  ): Promise<ApiResponse<AttendanceCorrectionSchema>> => {
    return apiClient.put<ApiResponse<AttendanceCorrectionSchema>>(
      `/attendance/corrections/${requestId}/approve`,
      payload
    );
  },

  // POST /attendance/lock
  lockAttendance: async (payload: AttendanceLockPayload): Promise<ApiResponse<boolean>> => {
    return apiClient.post<ApiResponse<boolean>>("/attendance/lock", payload);
  },

  // POST /attendance/unlock
  unlockAttendance: async (payload: AttendanceUnlockPayload): Promise<ApiResponse<boolean>> => {
    return apiClient.post<ApiResponse<boolean>>("/attendance/unlock", payload);
  },

  // GET /attendance/locks
  getAttendanceLocks: async (): Promise<ApiResponse<AttendanceLockSchema[]>> => {
    return apiClient.get<ApiResponse<AttendanceLockSchema[]>>("/attendance/locks");
  },

  // POST /attendance/generate
  generateAttendance: async (payload: {
    date_from: string;
    date_to: string;
    branch_id?: number | null;
    department_id?: number | null;
    employee_ids?: number[];
  }): Promise<ApiResponse<{ success: boolean; message: string; records_generated: number }>> => {
    return apiClient.post<
      ApiResponse<{ success: boolean; message: string; records_generated: number }>
    >("/attendance/generate", payload);
  },

  // GET /reports/attendance/daily-punch
  getDailyPunchReport: async (
    params: DailyPunchReportQueryParams
  ): Promise<ApiResponse<DailyPunchMatrixReportData>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<DailyPunchMatrixReportData>>(
      q ? `/reports/attendance/daily-punch?${q}` : "/reports/attendance/daily-punch"
    );
  },
};

export interface DailyPunchCell {
  first_in: string | null;
  last_out: string | null;
  status: string;
  is_missing_punch: boolean;
  is_off_day: boolean;
}

export interface DailyPunchMatrixRow {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department_name: string;
  designation_name: string;
  daily_punches: Record<string, DailyPunchCell>;
}

export interface DailyPunchMatrixReportData {
  dates: string[];
  items: DailyPunchMatrixRow[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export interface DailyPunchReportQueryParams {
  date_from?: string;
  date_to?: string;
  branch_id?: number;
  dept_id?: number;
  employee_id?: number;
  page?: number;
  page_size?: number;
  format?: string;
  sort_by?: string;
  sort_dir?: "asc" | "desc";
}
