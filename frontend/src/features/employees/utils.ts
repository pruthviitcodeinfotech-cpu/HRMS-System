import {
  Employee,
  EmployeeSortBy,
  EmployeeSummary,
  EmployeeUiStatus,
  EmploymentStatus,
  SortField,
} from "./types";

/** Backend employment_status → UI badge label. */
export const STATUS_LABELS: Record<EmploymentStatus, EmployeeUiStatus> = {
  active: "Active",
  inactive: "Inactive",
  terminated: "Terminated",
};

/** UI badge label → backend employment_status (status filter / future actions). */
export const STATUS_VALUES: Record<EmployeeUiStatus, EmploymentStatus> = {
  Active: "active",
  Inactive: "inactive",
  Terminated: "terminated",
};

/**
 * UI table column → backend sort_by column. Columns absent here (branch /
 * department / designation names, satellite data) are not server-sortable.
 */
export const SORT_FIELD_MAP: Partial<Record<SortField | string, EmployeeSortBy>> = {
  employee_id: "employee_code",
  name: "employee_name",
  date_of_joining: "date_of_joining",
  status: "employment_status",
  created_on: "created_at",
};

/** ISO date/datetime → "16 Feb 2026", or "-" when absent. */
export const formatEmployeeDate = (iso: string | null): string => {
  if (!iso) return "-";
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
};

/** Project a GET /employees row onto the table view-model. */
export const toEmployeeRow = (summary: EmployeeSummary): Employee => ({
  id: summary.employee_id,
  employee_id: summary.employee_code,
  name: summary.employee_name,
  display_name: summary.display_name ?? "-",
  mobile_number: summary.mobile_number
    ? `${summary.mobile_country_code} ${summary.mobile_number}`.trim()
    : "-",
  email: summary.email ?? "-",
  gender: summary.gender,
  employee_type: summary.employee_type ?? "-",
  master_branch: summary.branch_name ?? "-",
  department: summary.department_name ?? "-",
  designation: summary.designation_name ?? "-",
  date_of_joining: formatEmployeeDate(summary.date_of_joining),
  created_on: formatEmployeeDate(summary.created_at),
  status: STATUS_LABELS[summary.employment_status],
});
