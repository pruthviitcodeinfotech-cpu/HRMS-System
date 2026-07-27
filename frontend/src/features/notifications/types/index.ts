export type NotificationType =
  | "system"
  | "alert"
  | "reminder"
  | "announcement"
  | "workflow"
  | "attendance"
  | "leave"
  | "payroll"
  | "shift"
  | "approval";

export type NotificationPriority = "low" | "medium" | "high" | "urgent";

export type RecipientStatus = "unread" | "read" | "archived";

export interface MyNotificationSchema {
  notification_id: number;
  recipient_id: number;
  title: string;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  source_module?: string | null;
  source_entity_type?: string | null;
  source_entity_id?: number | null;
  status: RecipientStatus;
  is_archived: boolean;
  delivered_at?: string | null;
  read_at?: string | null;
  archived_at?: string | null;
  created_at: string;
  expires_at?: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface MyNotificationListResponse {
  items: MyNotificationSchema[];
  pagination: PaginationMeta;
}

export interface MyNotificationCountResponse {
  unread_count: number;
  archived_count: number;
  total_count: number;
}

export interface MyNotificationParams {
  status?: RecipientStatus;
  archived?: boolean;
  notification_type?: string;
  priority?: string;
  source_module?: string;
  include_expired?: boolean;
  page?: number;
  page_size?: number;
}

export interface NotificationCreatePayload {
  title: string;
  message: string;
  notification_type?: NotificationType;
  priority?: NotificationPriority;
  source_module?: string;
  source_entity_type?: string;
  source_entity_id?: number;
  expires_at?: string;
  recipient_user_ids?: number[];
}

export interface NotificationSchema {
  id: number;
  org_id: number;
  branch_id?: number | null;
  title: string;
  message: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  source_module?: string | null;
  source_entity_type?: string | null;
  source_entity_id?: number | null;
  created_by?: number | null;
  created_at: string;
  expires_at?: string | null;
}

export interface NotificationListResponse {
  items: NotificationSchema[];
  pagination: PaginationMeta;
}
