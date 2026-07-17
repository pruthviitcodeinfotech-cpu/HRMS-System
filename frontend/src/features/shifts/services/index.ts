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
};
