import { EmployeeSummary } from "@/features/employees";

export interface LeaveBalanceEmployee {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  designation: string;
  leaveBalances: Record<string, number | "Not Assigned">;
  employeeSummary?: EmployeeSummary;
}
