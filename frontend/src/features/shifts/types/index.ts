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

// ---------------------------------------------------------------------------
// Shift Assignments
// ---------------------------------------------------------------------------

export interface ShiftAssignmentSchema {
  assignment_id: number;
  org_id: number;
  employee_id: number;
  shift_id: number;
  effective_from: string;
  effective_to?: string | null;
  assigned_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ShiftAssignmentListResponse {
  items: ShiftAssignmentSchema[];
  pagination: PaginationMeta;
}

export interface ShiftAssignmentQuery {
  page?: number;
  page_size?: number;
  employee_id?: number;
  shift_id?: number;
  active_on?: string;
  date?: string;
}

export interface ShiftAssignmentBulkRequest {
  employee_ids: number[];
  shift_id: number;
  effective_from: string;
  effective_to?: string | null;
}

export interface ShiftAssignmentBulkItemResult {
  employee_id: number;
  status: "created" | "skipped";
  reason?: string | null;
  assignment_id?: number | null;
}

export interface ShiftAssignmentBulkResponse {
  created_count: number;
  skipped_count: number;
  results: ShiftAssignmentBulkItemResult[];
}

// ---------------------------------------------------------------------------
// Week Off Management
// ---------------------------------------------------------------------------

export type WeekoffType = "working" | "week_off" | "occasional_week_off";
export type DayOfWeek = 0 | 1 | 2 | 3 | 4 | 5 | 6; // 0=Sunday … 6=Saturday

export interface WeeklyOffSchema {
  weekoff_id: number;
  employee_id: number;
  day_of_week: DayOfWeek;
  weekoff_type: WeekoffType;
  occurrence_1st: boolean;
  occurrence_2nd: boolean;
  occurrence_3rd: boolean;
  occurrence_4th: boolean;
  occurrence_5th: boolean;
  effective_from: string | null;
  effective_to: string | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface WeeklyOffListResponse {
  items: WeeklyOffSchema[];
  pagination: PaginationMeta;
}

export interface WeekoffItemInput {
  day_of_week: DayOfWeek;
  weekoff_type: WeekoffType;
  occurrence_1st?: boolean;
  occurrence_2nd?: boolean;
  occurrence_3rd?: boolean;
  occurrence_4th?: boolean;
  occurrence_5th?: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
}

export interface WeekoffConfigureRequest {
  weekoffs: WeekoffItemInput[];
}

export interface WeekoffPatchRequest {
  weekoff_type?: WeekoffType;
  occurrence_1st?: boolean;
  occurrence_2nd?: boolean;
  occurrence_3rd?: boolean;
  occurrence_4th?: boolean;
  occurrence_5th?: boolean;
  effective_to?: string | null;
}

export interface WeeklyOffUpdateRequest {
  employee_id?: number | null;
  department_id?: number | null;
  day_of_week: DayOfWeek;
  weekoff_type: WeekoffType;
  occurrence_1st?: boolean;
  occurrence_2nd?: boolean;
  occurrence_3rd?: boolean;
  occurrence_4th?: boolean;
  occurrence_5th?: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
}

// ---------------------------------------------------------------------------
// Roster / Shift Calendar
// ---------------------------------------------------------------------------

export interface RosterEntrySchema {
  roster_id: number;
  org_id: number;
  employee_id: number;
  roster_date: string;
  shift_id: number | null;
  is_week_off: boolean;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface RosterListResponse {
  items: RosterEntrySchema[];
  pagination: PaginationMeta;
}

export interface RosterQuery {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  month?: string;
  branch_id?: number;
  dept_id?: number;
  employee_id?: number;
  shift_id?: number;
}

export interface RosterUpsertRequest {
  employee_id: number;
  roster_date: string;
  shift_id?: number | null;
  is_week_off?: boolean;
}

export interface RosterUpsertResult {
  created: boolean;
  entry: RosterEntrySchema;
}

export interface RosterBulkEntry {
  employee_id: number;
  roster_date: string;
  shift_id?: number | null;
  is_week_off?: boolean;
}

export interface RosterBulkRequest {
  entries: RosterBulkEntry[];
}

export interface RosterBulkItemResult {
  employee_id: number;
  roster_date: string;
  status: "created" | "updated" | "skipped";
  reason?: string | null;
  roster_id?: number | null;
}

export interface RosterBulkResponse {
  created_count: number;
  updated_count: number;
  skipped_count: number;
  results: RosterBulkItemResult[];
}

export interface RosterUpdateRequest {
  shift_id?: number | null;
  is_week_off?: boolean;
}

export interface ShiftResolveQuery {
  employee_id: number;
  date: string;
}

export interface ShiftResolveResponse {
  employee_id: number;
  date: string;
  effective_shift_id: number | null;
  is_weekly_off: boolean;
  is_working_day: boolean;
  resolution_source: "roster" | "weekoff" | "assignment" | "default";
}


