export interface Permission {
  feature_key: string;
  can_create: boolean;
  can_read: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export interface User {
  id: string;
  email: string;
  orgId: string;
  isSuperAdmin: boolean;
  isActive: boolean;
  sessionId: string;
  roles: string[];
  permissions: Permission[];
  branchIds: number[];
  departmentIds: number[];
  name?: string;
  employeeId?: string | null;
  mobileCountryCode?: string;
  mobileNumber?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface CurrentUserProfile {
  id: number;
  org_id: number;
  name: string;
  email: string;
  mobile_country_code: string;
  mobile_number: string;
  is_super_admin: boolean;
  is_active: boolean;
  employee_id: number | null;
  last_login_at: string | null;
  permissions: Array<{
    feature_key: string;
    can_create: boolean;
    can_read: boolean;
    can_edit: boolean;
    can_delete: boolean;
  }>;
  data_scope: {
    branch_ids: number[];
    department_ids: number[];
  };
  available_organizations: Array<{
    org_id: number;
    org_code: string;
    org_name: string;
    is_primary: boolean;
    is_active: boolean;
  }>;
}
