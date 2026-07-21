export type ApprovalStatus = "pending" | "approved" | "rejected";

export type ApprovalRequestType =
  | "Leave"
  | "Attendance"
  | "Overtime"
  | "Comp Off"
  | "Short Leave";

export type BackendRequestType = "attendance" | "leave" | "login_reset";

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
  numericId: number;
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

// ---------------------------------------------------------------------------
// Backend API Schemas & DTOs
// ---------------------------------------------------------------------------

export interface ApprovalRequestSchema {
  id: number;
  org_id: number;
  request_type: BackendRequestType;
  request_subtype: string | null;
  reference_id: number;
  employee_id: number;
  status: ApprovalStatus;
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by: number | null;
  reject_remarks: string | null;
  created_at: string;
  employee_name?: string;
  employee_code?: string;
  department_name?: string;
  designation_name?: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ApprovalListResponse {
  items: ApprovalRequestSchema[];
  pagination: PaginationMeta;
}

export interface ApprovalDetailsSchema {
  approval: ApprovalRequestSchema;
  source: Record<string, unknown> | null;
}

export interface ApprovalStatusSchema {
  status: ApprovalStatus;
  reviewed_by: number | null;
  reviewed_at: string | null;
  reject_remarks: string | null;
}

export interface ApprovalTimelineEventSchema {
  event: string;
  at: string;
  by: number | null;
  remarks: string | null;
}

export interface ApprovalPendingCountSchema {
  pending_count: number;
  by_request_type: Record<string, number>;
}

export interface ApproveRequestPayload {
  remarks?: string;
}

export interface RejectRequestPayload {
  reject_remarks: string;
}

export interface BulkApprovePayload {
  approval_ids: number[];
  remarks?: string;
}

export interface BulkRejectPayload {
  approval_ids: number[];
  reject_remarks: string;
}

export interface BulkActionItemError {
  code: string;
  message: string;
}

export interface BulkActionItemResult {
  id: number;
  success: boolean;
  error?: BulkActionItemError | null;
}

export interface BulkActionResponse {
  results: BulkActionItemResult[];
}

export interface ApprovalQueryParams {
  status?: ApprovalStatus;
  request_type?: BackendRequestType;
  request_subtype?: string;
  employee_id?: number;
  date_from?: string;
  date_to?: string;
  branch_id?: number;
  dept_id?: number;
  page?: number;
  page_size?: number;
}
