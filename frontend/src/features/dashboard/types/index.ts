export interface DashboardKPIs {
  total_employees: number;
  active_employees: number;
  new_employees: number;
  present_today: number;
  absent_today: number;
  half_day_today?: number;
  late_arrivals: number;
  early_exits: number;
  on_leave_today: number;
  on_break_today: number;
  pending_biometrics: number;
  pending_leaves: number;
  pending_approvals: number;
  current_payroll_status: string;
  total_outstanding_loans_advances: string;
  total_outstanding_arrears: string;
  online_devices: number;
  offline_devices: number;
  unread_notifications: number;
  generated_at: string;
}

export interface AttendanceDailyTrendPoint {
  date: string;
  present: number;
  absent: number;
  late: number;
}

export interface AttendanceDashboard {
  present_today: number;
  absent_today: number;
  half_day_today: number;
  on_leave_today: number;
  on_break_today: number;
  pending_biometrics: number;
  late_arrivals: number;
  early_exits: number;
  not_marked: number;
  trend: AttendanceDailyTrendPoint[];
  generated_at: string;
}

export interface AttendanceDailyRecord {
  employee_id: number;
  status: string;
  first_in: string | null;
  last_out: string | null;
  worked_minutes: number;
  late_minutes: number;
  overtime_minutes: number;
  is_locked: boolean;
  employee_code: string | null;
  employee_name: string | null;
  department_name: string | null;
  designation: string | null;
  first_punch: string | null;
  last_punch: string | null;
  working_hours: number | null;
  break_hours: number | null;
  overtime: number | null;
  is_on_break?: boolean;
  shift_id?: number | null;
  shift_name?: string | null;
}

export interface AttendanceDailyList {
  items: AttendanceDailyRecord[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ShiftSummaryItem {
  shift_id: number;
  shift_name: string;
  total_employees: number;
  present: number;
  late: number;
  absent: number;
  on_leave: number;
}

export interface ShiftSummaryResponse {
  shifts: ShiftSummaryItem[];
  generated_at: string;
}

export interface DepartmentAttendanceChartPoint {
  name: string;
  points: number[];
}

export interface DepartmentAttendanceChart {
  labels: string[];
  series: DepartmentAttendanceChartPoint[];
  generated_at: string;
}

export interface BiometricDevice {
  id: number;
  org_id: number;
  branch_id: number | null;
  device_name: string;
  device_code: string;
  serial_number: string;
  model: string | null;
  manufacturer: string | null;
  ip_address: string | null;
  port: number | null;
  protocol: string;
  domain: string | null;
  mac_address: string | null;
  adms_enabled: boolean;
  adms_server: string | null;
  adms_port: number | null;
  cloud_id: string | null;
  timezone: string | null;
  status: "online" | "offline";
  last_seen_at: string | null;
  last_sync_at: string | null;
  total_users: number;
  total_fingerprints: number;
  total_faces: number;
  total_cards: number;
  total_logs: number;
  installation_location: string | null;
  remarks: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BiometricDeviceList {
  items: BiometricDevice[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApprovalRequestBrief {
  id: number;
  request_type: "leave" | "attendance_regularization" | string;
  status: "pending" | "approved" | "rejected";
  requester_name: string;
  submitted_at: string;
}

export interface ApprovalDashboard {
  pending_approvals: number;
  by_request_type: Record<string, number>;
  approved_recent: number;
  rejected_recent: number;
  recent: ApprovalRequestBrief[];
  generated_at: string;
}
