export interface PermissionCatalogItem {
  feature_key: string;
  feature_label: string;
  parent_feature_key?: string | null;
  supported_actions: string[];
}

export interface RightsTemplate {
  id: number;
  name: string;
  description?: string;
  permission_count?: number;
  assigned_user_count?: number;
  created_at: string;
  updated_at: string;
  is_deleted?: boolean;
}

export interface RightsTemplateDetail extends RightsTemplate {
  permissions: TemplatePermission[];
}

export interface TemplatePermission {
  id?: number;
  feature_key: string;
  feature_label: string;
  parent_feature_key?: string | null;
  can_create: boolean;
  can_read: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export interface TemplatePermissionInput {
  feature_key: string;
  feature_label: string;
  parent_feature_key?: string | null;
  can_create: boolean;
  can_read: boolean;
  can_edit: boolean;
  can_delete: boolean;
}

export interface CreateRightsTemplateInput {
  name: string;
  description?: string;
  permissions?: TemplatePermissionInput[];
}

export interface UpdateRightsTemplateInput {
  name: string;
  description?: string;
  is_deleted?: boolean;
}

export interface RightsTemplateLogsItem {
  id: number;
  action: string;
  description: string;
  created_at: string;
  created_by?: string;
}
