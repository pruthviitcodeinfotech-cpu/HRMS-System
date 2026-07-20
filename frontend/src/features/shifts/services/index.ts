import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  CreateShiftRequest,
  ShiftDetailSchema,
  ShiftListParams,
  ShiftListResponse,
  UpdateShiftRequest,
} from "../types";

const buildShiftQuery = (params: ShiftListParams): string => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", String(params.page));
  if (params.page_size) query.append("page_size", String(params.page_size));
  if (params.q) query.append("q", params.q);
  if (params.shift_type) query.append("shift_type", params.shift_type);
  if (params.is_default !== undefined)
    query.append("is_default", String(params.is_default));
  if (params.is_open_shift !== undefined)
    query.append("is_open_shift", String(params.is_open_shift));
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return query.toString();
};

export const shiftService = {
  /** GET /shifts — paginated, filtered, sorted list. */
  getShifts: async (
    params: ShiftListParams = {}
  ): Promise<ApiResponse<ShiftListResponse>> => {
    const queryString = buildShiftQuery(params);
    const url = queryString ? `/shifts?${queryString}` : "/shifts";
    return apiClient.get<ApiResponse<ShiftListResponse>>(url);
  },

  /** GET /shifts/{shift_id} — full detail with day_timings. */
  getShift: async (
    shiftId: number
  ): Promise<ApiResponse<ShiftDetailSchema>> => {
    return apiClient.get<ApiResponse<ShiftDetailSchema>>(`/shifts/${shiftId}`);
  },

  /** POST /shifts — create a new shift definition. */
  createShift: async (
    data: CreateShiftRequest
  ): Promise<ApiResponse<ShiftDetailSchema>> => {
    return apiClient.post<ApiResponse<ShiftDetailSchema>>("/shifts", data);
  },

  /** PATCH /shifts/{shift_id} — partial update. */
  updateShift: async (
    shiftId: number,
    data: UpdateShiftRequest
  ): Promise<ApiResponse<ShiftDetailSchema>> => {
    return apiClient.patch<ApiResponse<ShiftDetailSchema>>(
      `/shifts/${shiftId}`,
      data
    );
  },

  /**
   * Restore a soft-deleted shift — POST /shifts/{shift_id}/restore.
   * The backend's only "re-activate" path (no separate activate endpoint for shifts).
   */
  restoreShift: async (
    shiftId: number
  ): Promise<ApiResponse<ShiftDetailSchema>> => {
    return apiClient.post<ApiResponse<ShiftDetailSchema>>(
      `/shifts/${shiftId}/restore`,
      {}
    );
  },

  /**
   * Soft-delete a shift — DELETE /shifts/{shift_id}.
   * Blocked by the backend when active assignments reference the shift.
   * Returns 204 No Content; we return void here.
   */
  deleteShift: async (shiftId: number): Promise<void> => {
    await apiClient.delete<void>(`/shifts/${shiftId}`);
  },

  /** Bulk assign shift to multiple employees — POST /shift-assignments/bulk */
  bulkAssignShift: async (
    data: import("../types").ShiftAssignmentBulkRequest
  ): Promise<ApiResponse<import("../types").ShiftAssignmentBulkResponse>> => {
    return apiClient.post<ApiResponse<import("../types").ShiftAssignmentBulkResponse>>(
      "/shift-assignments/bulk",
      data
    );
  },

  /** List shift assignments — GET /shift-assignments */
  listAssignments: async (
    params: import("../types").ShiftAssignmentQuery = {}
  ): Promise<ApiResponse<import("../types").ShiftAssignmentListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.employee_id) query.append("employee_id", String(params.employee_id));
    if (params.shift_id) query.append("shift_id", String(params.shift_id));
    if (params.active_on) query.append("active_on", params.active_on);
    if (params.date) query.append("date", params.date);
    const queryString = query.toString();
    const url = queryString ? `/shift-assignments?${queryString}` : "/shift-assignments";
    return apiClient.get<ApiResponse<import("../types").ShiftAssignmentListResponse>>(url);
  },

  /** Get employee week offs — GET /employees/{employee_id}/weekoffs */
  getEmployeeWeekoffs: async (
    employeeId: number,
    includeHistory: boolean = false
  ): Promise<ApiResponse<import("../types").WeeklyOffListResponse>> => {
    const url = `/employees/${employeeId}/weekoffs${includeHistory ? "?include_history=true" : ""}`;
    return apiClient.get<ApiResponse<import("../types").WeeklyOffListResponse>>(url);
  },

  /** Configure employee week offs — PUT /employees/{employee_id}/weekoffs */
  configureEmployeeWeekoffs: async (
    employeeId: number,
    data: import("../types").WeekoffConfigureRequest
  ): Promise<ApiResponse<import("../types").WeeklyOffListResponse>> => {
    return apiClient.put<ApiResponse<import("../types").WeeklyOffListResponse>>(
      `/employees/${employeeId}/weekoffs`,
      data
    );
  },

  /** Update single week off — PATCH /employees/{employee_id}/weekoffs/{weekoff_id} */
  updateEmployeeWeekoff: async (
    employeeId: number,
    weekoffId: number,
    data: import("../types").WeekoffPatchRequest
  ): Promise<ApiResponse<import("../types").WeeklyOffSchema>> => {
    return apiClient.patch<ApiResponse<import("../types").WeeklyOffSchema>>(
      `/employees/${employeeId}/weekoffs/${weekoffId}`,
      data
    );
  },

  /** GET /roster — Org shift calendar over date range or month */
  getRoster: async (
    params: import("../types").RosterQuery = {}
  ): Promise<ApiResponse<import("../types").RosterListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.date_from) query.append("date_from", params.date_from);
    if (params.date_to) query.append("date_to", params.date_to);
    if (params.month) query.append("month", params.month);
    if (params.branch_id) query.append("branch_id", String(params.branch_id));
    if (params.dept_id) query.append("dept_id", String(params.dept_id));
    if (params.employee_id) query.append("employee_id", String(params.employee_id));
    if (params.shift_id) query.append("shift_id", String(params.shift_id));
    const queryString = query.toString();
    const url = queryString ? `/roster?${queryString}` : "/roster";
    return apiClient.get<ApiResponse<import("../types").RosterListResponse>>(url);
  },

  /** GET /employees/{employee_id}/roster — Employee shift calendar */
  getEmployeeRoster: async (
    employeeId: number,
    params: { date_from?: string; date_to?: string; month?: string } = {}
  ): Promise<ApiResponse<import("../types").RosterListResponse>> => {
    const query = new URLSearchParams();
    if (params.date_from) query.append("date_from", params.date_from);
    if (params.date_to) query.append("date_to", params.date_to);
    if (params.month) query.append("month", params.month);
    const queryString = query.toString();
    const url = `/employees/${employeeId}/roster${queryString ? `?${queryString}` : ""}`;
    return apiClient.get<ApiResponse<import("../types").RosterListResponse>>(url);
  },

  /** PUT /roster — Set Roster Entry (upsert single) */
  upsertRosterEntry: async (
    data: import("../types").RosterUpsertRequest
  ): Promise<ApiResponse<import("../types").RosterUpsertResult>> => {
    return apiClient.put<ApiResponse<import("../types").RosterUpsertResult>>("/roster", data);
  },

  /** POST /roster/bulk — Bulk Set Roster */
  bulkSetRoster: async (
    data: import("../types").RosterBulkRequest
  ): Promise<ApiResponse<import("../types").RosterBulkResponse>> => {
    return apiClient.post<ApiResponse<import("../types").RosterBulkResponse>>("/roster/bulk", data);
  },

  /** PATCH /roster/{roster_id} — Update Roster Entry */
  updateRosterEntry: async (
    rosterId: number,
    data: import("../types").RosterUpdateRequest
  ): Promise<ApiResponse<import("../types").RosterEntrySchema>> => {
    return apiClient.patch<ApiResponse<import("../types").RosterEntrySchema>>(
      `/roster/${rosterId}`,
      data
    );
  },

  /** DELETE /roster/{roster_id} — Delete Roster Entry */
  deleteRosterEntry: async (rosterId: number): Promise<void> => {
    await apiClient.delete<void>(`/roster/${rosterId}`);
  },

  /** GET /shifts/resolve — Resolve shift for an employee on a date */
  resolveShift: async (
    params: import("../types").ShiftResolveQuery
  ): Promise<ApiResponse<import("../types").ShiftResolveResponse>> => {
    const query = new URLSearchParams();
    query.append("employee_id", String(params.employee_id));
    query.append("date", params.date);
    return apiClient.get<ApiResponse<import("../types").ShiftResolveResponse>>(
      `/shifts/resolve?${query.toString()}`
    );
  },
};


