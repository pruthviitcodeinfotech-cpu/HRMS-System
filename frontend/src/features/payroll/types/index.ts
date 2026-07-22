export interface PayrollGroup {
  id: number;
  group_name: string;
  code: string;
  pay_frequency: string;
  cutoff_day: number;
  pay_day: number;
  description?: string | null;
  is_active: boolean;
  employee_count?: number;
  created_at?: string;
  updated_at?: string;
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
