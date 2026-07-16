// ---------------------------------------------------------------------------
// Backend contract — GET /api/v1/employees (Employee Management module)
// Field names mirror the FastAPI EmployeeSummarySchema exactly.
// ---------------------------------------------------------------------------

/** employees.employment_status values (backend CHECK constraint). */
export type EmploymentStatus = "active" | "inactive" | "terminated";

export type Gender = "Male" | "Female" | "Other";

/** One row of the paginated GET /employees response. */
export interface EmployeeSummary {
  employee_id: number;
  org_id: number;
  employee_code: string;
  employee_name: string;
  display_name: string | null;
  mobile_country_code: string;
  mobile_number: string;
  email: string | null;
  gender: Gender;
  master_branch_id: number;
  dept_id: number;
  designation_id: number;
  employee_type: string | null;
  employment_status: EmploymentStatus;
  date_of_joining: string | null; // ISO date
  profile_photo_url: string | null;
  created_at: string; // ISO datetime
  // Denormalised org names (added in Phase 7.3.1 for list rendering)
  branch_name: string | null;
  department_name: string | null;
  designation_name: string | null;
}

/** Shared paged-list metadata returned by every list endpoint. */
export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface EmployeeListResponse {
  items: EmployeeSummary[];
  pagination: PaginationMeta;
}

/** Columns the backend allows in sort_by (unknown values fall back to created_at). */
export type EmployeeSortBy =
  | "employee_code"
  | "employee_name"
  | "date_of_joining"
  | "employment_status"
  | "created_at"
  | "updated_at";

export type SortOrder = "asc" | "desc";

/** Query parameters accepted by GET /employees. */
export interface EmployeeListParams {
  page?: number;
  page_size?: number;
  q?: string;
  branch_id?: number;
  department_id?: number;
  designation_id?: number;
  status?: EmploymentStatus;
  sort_by?: EmployeeSortBy;
  sort_order?: SortOrder;
}

// ---------------------------------------------------------------------------
// Filter dropdown lookups (organization module list endpoints)
// ---------------------------------------------------------------------------

export interface BranchOption {
  branch_id: number;
  branch_name: string;
}

export interface DepartmentOption {
  dept_id: number;
  dept_name: string;
}

export interface DesignationOption {
  designation_id: number;
  designation_name: string;
}

export interface LookupListResponse<T> {
  items: T[];
  pagination: PaginationMeta;
}

// ---------------------------------------------------------------------------
// UI view-model — shape consumed by the Employee List table markup
// ---------------------------------------------------------------------------

/** Display labels for employment_status ("Left" does not exist in the backend contract). */
export type EmployeeUiStatus = "Active" | "Inactive" | "Terminated";

export interface Employee {
  /** employees PK (numeric id used for row selection / detail navigation). */
  id: number;
  /** Display code (backend employee_code, e.g. "EMP00037"). */
  employee_id: string;
  name: string;
  display_name: string;
  mobile_number: string;
  email: string;
  gender: string;
  employee_type: string;
  master_branch: string;
  department: string;
  designation: string;
  date_of_joining: string; // "16 Feb 2026" or "-"
  created_on: string;
  status: EmployeeUiStatus;
}

export type SortField =
  | "employee_id"
  | "name"
  | "master_branch"
  | "department"
  | "designation"
  | "date_of_joining"
  | "status";

// ---------------------------------------------------------------------------
// Backend contract — GET /api/v1/departments (Organization module)
// ---------------------------------------------------------------------------

export interface DepartmentSchema {
  dept_id: number;
  org_id: number;
  dept_name: string;
  is_active: boolean;
  is_deleted: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
  employee_count: number;
}

export interface DepartmentListResponse {
  items: DepartmentSchema[];
  pagination: PaginationMeta;
}

export interface DepartmentListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  include_deleted?: boolean;
  sort_by?: "dept_name" | "created_at";
  sort_order?: SortOrder;
}

// ---------------------------------------------------------------------------
// Backend contract — GET /api/v1/designations (Organization module)
// ---------------------------------------------------------------------------

export interface DesignationSchema {
  designation_id: number;
  org_id: number;
  designation_name: string;
  is_active: boolean;
  is_deleted: boolean;
  created_by: number | null;
  created_at: string;
  updated_at: string;
  employee_count: number;
}

export interface DesignationListResponse {
  items: DesignationSchema[];
  pagination: PaginationMeta;
}

export interface DesignationListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  include_deleted?: boolean;
  sort_by?: "designation_name" | "created_at";
  sort_order?: SortOrder;
}
