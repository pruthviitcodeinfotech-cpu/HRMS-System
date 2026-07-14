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
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}
