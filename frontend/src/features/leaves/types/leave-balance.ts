import { EmployeeSummary } from "@/features/employees";
import { LeaveTypeSchema } from "./leave-create";

export interface LeaveBalanceEmployee {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  designation: string;
  leaveBalances: Record<string, number | "Not Assigned">;
  employeeSummary?: EmployeeSummary;
}

export interface EmployeeLeaveBalanceSchema {
  id: number;
  employee_id: number;
  leave_type_id: number;
  cycle_year: number;
  opening_balance: number;
  allocated: number;
  used: number;
  carried_forward: number;
  encashed: number;
  adjusted: number;
  closing_balance: number;
  updated_at: string;
  updated_by: number | null;
  leave_type?: LeaveTypeSchema | null;
}

export interface LeaveBalanceListParams {
  page?: number;
  page_size?: number;
  leave_type_id?: number;
  cycle_year?: number;
  employee_id?: number;
  branch_id?: number;
  dept_id?: number;
}

export interface LeaveBalanceListResponse {
  items: EmployeeLeaveBalanceSchema[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface LeaveCreditDebitRequest {
  leave_type_id: number;
  cycle_year: number;
  days: number;
  adjustment_type?: "manual" | "bulk_adjust" | "bulk_update";
  remarks?: string | null;
}

export interface LeaveBalanceAdjustRequest {
  leave_type_id: number;
  cycle_year: number;
  new_balance: number;
  adjustment_type?: "manual" | "bulk_adjust" | "bulk_update";
  remarks?: string | null;
}
