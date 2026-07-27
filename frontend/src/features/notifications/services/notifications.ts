import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  MyNotificationListResponse,
  MyNotificationCountResponse,
  MyNotificationSchema,
  MyNotificationParams,
  NotificationCreatePayload,
  NotificationSchema,
  NotificationListResponse,
} from "../types";

const buildQueryString = (params?: Record<string, unknown>): string => {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "") {
      query.append(key, String(val));
    }
  });
  const str = query.toString();
  return str ? `?${str}` : "";
};

export const notificationService = {
  // 1. My Notifications (Self-Service)
  getMyNotifications: async (
    params: MyNotificationParams = {}
  ): Promise<ApiResponse<MyNotificationListResponse>> => {
    const q = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<MyNotificationListResponse>>(`/me/notifications${q}`);
  },

  getMyNotificationCounts: async (): Promise<ApiResponse<MyNotificationCountResponse>> => {
    return apiClient.get<ApiResponse<MyNotificationCountResponse>>("/me/notifications/count");
  },

  getMyNotification: async (id: number): Promise<ApiResponse<MyNotificationSchema>> => {
    return apiClient.get<ApiResponse<MyNotificationSchema>>(`/me/notifications/${id}`);
  },

  markRead: async (id: number): Promise<ApiResponse<null>> => {
    return apiClient.post<ApiResponse<null>>(`/me/notifications/${id}/read`);
  },

  markUnread: async (id: number): Promise<ApiResponse<null>> => {
    return apiClient.post<ApiResponse<null>>(`/me/notifications/${id}/unread`);
  },

  archiveNotification: async (id: number): Promise<ApiResponse<null>> => {
    return apiClient.post<ApiResponse<null>>(`/me/notifications/${id}/archive`);
  },

  unarchiveNotification: async (id: number): Promise<ApiResponse<null>> => {
    return apiClient.post<ApiResponse<null>>(`/me/notifications/${id}/unarchive`);
  },

  deleteNotification: async (id: number): Promise<void> => {
    return apiClient.delete<void>(`/me/notifications/${id}`);
  },

  bulkMarkRead: async (payload: { notification_ids?: number[]; all_unread?: boolean }): Promise<ApiResponse<{ affected_count: number }>> => {
    return apiClient.post<ApiResponse<{ affected_count: number }>>("/me/notifications/bulk-read", payload);
  },

  bulkArchive: async (payload: { notification_ids?: number[]; all_read?: boolean }): Promise<ApiResponse<{ affected_count: number }>> => {
    return apiClient.post<ApiResponse<{ affected_count: number }>>("/me/notifications/bulk-archive", payload);
  },

  bulkDelete: async (payload: { notification_ids?: number[]; all_archived?: boolean }): Promise<void> => {
    return apiClient.delete<void>("/me/notifications/bulk-delete", { data: payload });
  },

  // 2. Admin Management (Feature Key: notification)
  createNotification: async (payload: NotificationCreatePayload): Promise<ApiResponse<NotificationSchema>> => {
    return apiClient.post<ApiResponse<NotificationSchema>>("/notifications", payload);
  },

  getNotifications: async (params?: Record<string, unknown>): Promise<ApiResponse<NotificationListResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<NotificationListResponse>>(`/notifications${q}`);
  },
};
