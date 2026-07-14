import { User } from "./types";

export interface JwtClaims {
  sub?: string;
  org_id?: string;
  is_super_admin?: boolean;
  is_active?: boolean;
  sid?: string;
  roles?: string[];
  permissions?: Array<{
    feature_key: string;
    can_create: boolean;
    can_read: boolean;
    can_edit: boolean;
    can_delete: boolean;
  }>;
  branch_ids?: number[];
  department_ids?: number[];
  email?: string;
}

export const decodeJwt = (token: string): JwtClaims | null => {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload) as JwtClaims;
  } catch (error) {
    console.error("Failed to decode JWT token:", error);
    return null;
  }
};

export const mapClaimsToUser = (claims: JwtClaims): User => {
  return {
    id: claims.sub || "",
    orgId: claims.org_id || "",
    isSuperAdmin: !!claims.is_super_admin,
    isActive: !!claims.is_active,
    sessionId: claims.sid || "",
    roles: claims.roles || [],
    permissions: claims.permissions || [],
    branchIds: claims.branch_ids || [],
    departmentIds: claims.department_ids || [],
    email: claims.email || "",
  };
};
