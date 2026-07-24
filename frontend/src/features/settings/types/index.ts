export interface OrgSettingsResponse {
  id: number;
  org_id: number;
  advance_shift_enabled: boolean;
  enable_regularization: boolean;
  enable_photo_punch: boolean;
  device_sync_time: string;
  sync_code: string;
  pass_code: string;
  updated_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface OrgSettingsUpdateRequest {
  advance_shift_enabled?: boolean;
  enable_regularization?: boolean;
  enable_photo_punch?: boolean;
  device_sync_time?: string;
  sync_code?: string;
  pass_code?: string;
}

export interface OrgSalarySlipResponse {
  id: number;
  org_id: number;
  company_logo_url?: string | null;
  company_name: string;
  company_address: string;
  company_contact: string;
  company_website_email?: string | null;
  auto_release_payslip: boolean;
  branch_wise_payslip: boolean;
  updated_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface OrgSalarySlipUpdateRequest {
  company_logo_url?: string | null;
  company_name?: string | null;
  company_address?: string | null;
  company_contact?: string | null;
  company_website_email?: string | null;
  auto_release_payslip?: boolean;
  branch_wise_payslip?: boolean;
}

export interface ModulePointerSchema {
  module: string;
  description: string;
}

export interface ConfigurationViewResponse {
  organization?: OrgSettingsResponse | null;
  salary_slip?: OrgSalarySlipResponse | null;
  cross_module_pointers?: Record<string, ModulePointerSchema>;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

// ---------------------------------------------------------------------------
// Payroll Settings (from GET/PUT /payroll/settings)
// ---------------------------------------------------------------------------

export interface PayrollSettingResponse {
  id: number;
  org_id: number;
  working_hour_type: string;
  full_day_working_hours: string;
  half_day_working_hours: string;
  attendance_mode: string;
  off_day_compensation: string;
  off_day_wage_multiplier: string | number;
  daily_wage_formula: string;
  overtime_type: string;
  overtime_hourly_multiplier: string | number;
  overtime_buffer_period: string;
  overtime_period_interval: string | null;
  full_day_penalty_enabled: boolean;
  half_day_penalty_enabled: boolean;
  late_coming_penalty_enabled: boolean;
  grace_time: string;
  updated_by?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface PayrollSettingUpdateRequest {
  working_hour_type?: string;
  full_day_working_hours?: string;
  half_day_working_hours?: string;
  attendance_mode?: string;
  off_day_compensation?: string;
  off_day_wage_multiplier?: number;
  daily_wage_formula?: string;
  overtime_type?: string;
  overtime_hourly_multiplier?: number;
  overtime_buffer_period?: string;
  overtime_period_interval?: string | null;
  full_day_penalty_enabled?: boolean;
  half_day_penalty_enabled?: boolean;
  late_coming_penalty_enabled?: boolean;
  grace_time?: string;
}
