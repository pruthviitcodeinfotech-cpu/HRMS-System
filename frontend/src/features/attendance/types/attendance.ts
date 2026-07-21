export type AttendanceStatus =
  | "FD"
  | "Present"
  | "Absent"
  | "Half Day"
  | "Weekly Off"
  | "Holiday"
  | "Leave"
  | "Late"
  | "Early Exit"
  | "Missed Punch";

export interface AttendanceRecord {
  id: string;
  employeeId: string;
  employeeName: string;
  department: string;
  designation: string;
  date: string;
  day: string;
  firstPunch: string;
  lastPunch: string;
  totalWorkingHours: string;
  totalBreakHours: string;
  status: AttendanceStatus;
  hasAnomaly?: boolean;
}

export interface AttendanceFilter {
  fromDate: string;
  toDate: string;
  branchId: string;
  searchQuery?: string;
}

export interface AttendancePagination {
  currentPage: number;
  pageSize: number;
  totalRecords: number;
  totalPages: number;
}

export type SortField = "employeeId" | "employeeName" | "department" | "designation" | "date" | "status";
export type SortOrder = "asc" | "desc";
