export type ApprovalStatus = "pending" | "approved" | "rejected";

export type ApprovalRequestType =
  | "Leave"
  | "Attendance"
  | "Overtime"
  | "Comp Off"
  | "Short Leave";

export interface ApprovalRequestDetails {
  fromDate?: string;
  toDate?: string;
  totalDays?: string;
  date?: string;
  inTime?: string;
  outTime?: string;
  totalHours?: string;
  reason?: string;
}

export interface ApprovalRequest {
  id: string;
  type: ApprovalRequestType;
  subtype: string; // e.g. "LWP", "New Punch Added", "Casual Leave", "Missed Punch"
  employeeCode: string; // e.g. "22"
  employeeName: string; // e.g. "Nitisha"
  designation: string; // e.g. "Backend Developer"
  department: string; // e.g. "Developer"
  avatarUrl?: string;
  details: ApprovalRequestDetails;
  submittedDate: string; // e.g. "20-07-2026 10:00 AM"
  status: ApprovalStatus;
  pendingApprover?: string; // e.g. "Balkrushn koladiya"
  approvedBy?: string;
  rejectedBy?: string;
  actionDate?: string;
  remarks?: string;
}

export interface ApprovalFilterState {
  status: ApprovalStatus;
  typeFilter: string;
  searchQuery: string;
}
