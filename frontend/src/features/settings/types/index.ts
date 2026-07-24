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
