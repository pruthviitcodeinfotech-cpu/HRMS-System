// ---------------------------------------------------------------------------
// Backend contract — Shift Management module
// Field names mirror the FastAPI ShiftSchema / ShiftDetailSchema exactly.
// ---------------------------------------------------------------------------

import { PaginationMeta } from "@/features/employees/types";

/** shifts.shift_type values (backend CHECK constraint). */
export type ShiftType = "fixed" | "open";

/** Sort fields allowed by GET /shifts. */
export type ShiftSortBy =
  | "shift_name"
  | "shift_type"
  | "is_default"
  | "created_at"
  | "updated_at";

/** One row from shift_day_timings. */
export interface ShiftDayTimingSchema {
  timing_id: number;
  day_of_week: number | null; // 0=Sunday … 6=Saturday; null = uniform
  start_time: string | null; // "HH:MM:SS"
  end_time: string | null;
  break_start_time: string | null;
  break_end_time: string | null;
  duration_minutes: number | null;
  is_working_day: boolean;
}

/** Compact shift row returned by GET /shifts. */
export interface ShiftSummarySchema {
  shift_id: number;
  org_id: number;
  shift_name: string;
  shift_type: ShiftType;
  is_open_shift: boolean;
  is_default: boolean;
  is_uniform_time: boolean;
  has_break_time: boolean;
  shift_color: string | null;
  is_advanced_mode: boolean;
  created_at: string; // ISO datetime
}

/** Full shift row (includes remark, is_deleted, updated_at). */
export interface ShiftSchema extends ShiftSummarySchema {
  remark: string | null;
  is_deleted: boolean;
  created_by: number | null;
  updated_at: string;
}

/** Detailed shift response (includes day_timings). */
export interface ShiftDetailSchema extends ShiftSchema {
  day_timings: ShiftDayTimingSchema[];
}

/** Paginated list response from GET /shifts. */
export interface ShiftListResponse {
  items: ShiftSummarySchema[];
  pagination: PaginationMeta;
}

/** Query parameters accepted by GET /shifts. */
export interface ShiftListParams {
  page?: number;
  page_size?: number;
  q?: string;
  shift_type?: ShiftType;
  is_default?: boolean;
  is_open_shift?: boolean;
  sort_by?: ShiftSortBy;
  sort_order?: "asc" | "desc";
}

/** Input for a single timing row (POST /shifts or PATCH /shifts/{id}). */
export interface ShiftDayTimingInput {
  day_of_week?: number | null;
  start_time?: string | null;
  end_time?: string | null;
  break_start_time?: string | null;
  break_end_time?: string | null;
  duration_minutes?: number | null;
  is_working_day?: boolean;
  crosses_midnight?: boolean;
}

/** Body for POST /shifts. */
export interface CreateShiftRequest {
  shift_name: string;
  shift_type?: ShiftType;
  is_open_shift?: boolean;
  is_default?: boolean;
  is_uniform_time?: boolean;
  has_break_time?: boolean;
  shift_color?: string | null;
  remark?: string | null;
  is_advanced_mode?: boolean;
  day_timings?: ShiftDayTimingInput[];
}

/** Body for PATCH /shifts/{id} (all fields optional). */
export interface UpdateShiftRequest {
  shift_name?: string;
  shift_type?: ShiftType;
  is_open_shift?: boolean;
  is_default?: boolean;
  is_uniform_time?: boolean;
  has_break_time?: boolean;
  shift_color?: string | null;
  remark?: string | null;
  is_advanced_mode?: boolean;
  day_timings?: ShiftDayTimingInput[] | null;
}
