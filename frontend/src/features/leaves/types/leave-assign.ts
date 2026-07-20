import { EmployeeSummary } from "@/features/employees";

export interface LeaveAssignEmployee {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  designation: string;
  leaveAssignments: Record<string, boolean>;
  employeeSummary?: EmployeeSummary;
}
