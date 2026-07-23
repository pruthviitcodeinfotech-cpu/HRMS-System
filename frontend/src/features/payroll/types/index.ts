export interface PayrollGroup {
  id: number;
  org_id?: number;
  name: string;
  group_name?: string;
  payroll_type?: string;
  code?: string;
  pay_frequency?: string;
  cutoff_day?: number;
  pay_day?: number;
  description?: string | null;
  is_default?: boolean;
  is_deleted?: boolean;
  is_active?: boolean;
  employee_count?: number;
  created_by?: number | null;
  updated_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface PayrollGroupItem {
  id: number;
  org_id: number;
  name: string;
  payroll_type: string;
  is_default: boolean;
  is_deleted: boolean;
  employee_count: number;
  created_by?: number | null;
  updated_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface PayrollGroupCreatePayload {
  name: string;
  payroll_type: string;
  is_default?: boolean;
}

export interface PayrollGroupUpdatePayload {
  name?: string;
  payroll_type?: string;
  is_default?: boolean;
}

export interface PayrollGroupAssignEmployeesPayload {
  employee_ids: number[];
  salary_type?: "monthly" | "hourly";
}

export interface GroupAssignedEmployeeItem {
  employee_id: number;
  employee_code?: string | null;
  employee_name: string;
  department_name?: string | null;
  designation_name?: string | null;
  assigned_at?: string | null;
}

export interface GroupEmployeesResponse {
  payroll_group_id: number;
  payroll_group_name: string;
  total_employees: number;
  items: GroupAssignedEmployeeItem[];
}

export interface PayrollCycle {
  id: number;
  payroll_group_id: number;
  group_name?: string;
  cycle_start_date: string;
  cycle_end_date: string;
  payroll_date: string;
  is_finalized: boolean;
  total_employees?: number;
  total_gross_pay?: number;
  total_net_pay?: number;
}

export interface AttendanceAdjustment {
  id: number;
  employee_id: number;
  employee_name?: string;
  employee_code?: string;
  date: string;
  adjustment_type: "penalty" | "extra_hours" | "status_change";
  status_override?: string;
  extra_hours?: number;
  penalty_amount?: number;
  reason: string;
  created_at?: string;
}

export interface PayrollRecord {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department_name?: string;
  designation_name?: string;
  branch_name?: string;
  payroll_group_name?: string;
  basic_salary: number;
  gross_earnings: number;
  total_deductions: number;
  net_payable: number;
  paid_days: number;
  unpaid_days: number;
  overtime_hours: number;
  penalty_deductions: number;
  payment_status: "pending" | "processing" | "paid" | "failed";
  is_finalized: boolean;
}

export interface FinalizedPayrollRun {
  id: number;
  run_code: string;
  payroll_group_id: number;
  payroll_group_name: string;
  cycle_start_date: string;
  cycle_end_date: string;
  total_employees: number;
  total_gross: number;
  total_deductions: number;
  total_net: number;
  payment_status: "unpaid" | "partial" | "paid";
  finalized_at: string;
  finalized_by_name?: string;
}

export interface EmployeeGroupAssignment {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department_name: string;
  designation_name: string;
  current_group_id?: number | null;
  current_group_name?: string | null;
  effective_from?: string | null;
}

export interface BulkAttendanceMatrixItem {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department_name: string;
  designation_name: string;
  branch_id: number;
  branch_name: string;
  attendance: Record<string, string>;
}

export interface BulkAttendanceMatrixResponse {
  dates: string[];
  items: BulkAttendanceMatrixItem[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
  };
}

export interface BulkAttendanceCellUpdate {
  employee_id: number;
  attendance_date: string;
  adjusted_status: string;
  original_status?: string | null;
  reason?: string | null;
}

export interface BulkAttendanceBatchUpdatePayload {
  date_from?: string;
  date_to?: string;
  updates: BulkAttendanceCellUpdate[];
}

export interface FinalizedPayrollEmployeeItem {
  id: number;
  payroll_finalization_id: number;
  employee_id: number;
  employee_code: string | null;
  employee_name: string | null;
  attendance_summary?: Record<string, any> | null;
  earnings_summary?: Record<string, any> | null;
  deduction_summary?: Record<string, any> | null;
  loan_amount: number;
  arrears_amount: number;
  net_salary: number;
  json_snapshot: Record<string, any>;
  created_at: string;
}

export interface FinalizedPayrollItem {
  id: number;
  org_id: number;
  payroll_group_id: number;
  payroll_group_name?: string | null;
  payroll_period_id?: number | null;
  from_date: string;
  to_date: string;
  payroll_module: string;
  employee_count: number;
  gross_amount: number;
  deduction_amount: number;
  net_payable: number;
  finalized_amount: number;
  paid_amount?: number | null;
  paid_on?: string | null;
  status: "Draft" | "Finalized" | "Paid" | "Cancelled";
  finalized_by: number;
  finalized_on: string;
  remarks?: string | null;
  created_at: string;
  updated_at: string;
  employees?: FinalizedPayrollEmployeeItem[];
}

export interface FinalizedPayrollPayPayload {
  paid_amount?: number;
  paid_on?: string;
  payment_method?: string;
  remarks?: string;
}
