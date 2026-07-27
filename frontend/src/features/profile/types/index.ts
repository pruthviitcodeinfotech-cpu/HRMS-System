// Mirrors backend/app/modules/profile/schemas.py

export interface OrganizationSummary {
  org_id: number;
  org_code: string;
  org_name: string;
  contact_phone?: string | null;
  contact_email?: string | null;
  is_active: boolean;
}

export interface BranchSummary {
  branch_id: number;
  branch_name: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  country?: string | null;
}

export interface EmployeeSummary {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  department_name?: string | null;
  designation_name?: string | null;
  date_of_joining?: string | null;
}

export interface ProfileData {
  user_id: number;
  name: string;
  email: string;
  mobile_country_code: string;
  mobile_number: string;
  is_super_admin: boolean;
  is_active: boolean;
  role_name?: string | null;
  profile_photo_url?: string | null;
  last_login_at?: string | null;
  created_at: string;
  organization: OrganizationSummary;
  branch?: BranchSummary | null;
  employee?: EmployeeSummary | null;
}

export interface ProfileUpdateInput {
  mobile_country_code?: string;
  mobile_number?: string;
}

export interface ChangePasswordInput {
  current_password: string;
  new_password: string;
  confirm_password: string;
}

export interface ChangePasswordResult {
  revoked_session_count: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}
