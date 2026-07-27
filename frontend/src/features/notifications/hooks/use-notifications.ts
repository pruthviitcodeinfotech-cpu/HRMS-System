import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { notificationService } from "../services/notifications";
import { MyNotificationParams, NotificationCreatePayload } from "../types";
import { useBranchContext } from "@/context/branch-context";

export const notificationKeys = {
  all: ["notifications"] as const,
  myNotifications: (params?: MyNotificationParams) => [...notificationKeys.all, "me", params || {}] as const,
  myCounts: () => [...notificationKeys.all, "me-counts"] as const,
  myDetail: (id: number) => [...notificationKeys.all, "me-detail", id] as const,
  adminList: (params?: Record<string, unknown>) => [...notificationKeys.all, "admin", params || {}] as const,
};

export const useMyNotifications = (params: MyNotificationParams = {}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: notificationKeys.myNotifications(effectiveParams),
    queryFn: async () => {
      const res = await notificationService.getMyNotifications(effectiveParams);
      return res.data;
    },
    placeholderData: keepPreviousData,
    refetchInterval: 1000 * 30, // Poll every 30s for real-time notification updates
  });
};

export const useMyNotificationCounts = () => {
  return useQuery({
    queryKey: notificationKeys.myCounts(),
    queryFn: async () => {
      const res = await notificationService.getMyNotificationCounts();
      return res.data;
    },
    refetchInterval: 1000 * 30, // Poll badge count every 30s
  });
};

export const useMyNotificationDetail = (id: number | null) => {
  return useQuery({
    queryKey: notificationKeys.myDetail(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await notificationService.getMyNotification(id);
      return res.data;
    },
    enabled: !!id,
  });
};

export const useMarkNotificationRead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationService.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useMarkNotificationUnread = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationService.markUnread(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useArchiveNotification = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationService.archiveNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useDeleteNotification = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationService.deleteNotification(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useBulkMarkRead = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { notification_ids?: number[]; all_unread?: boolean }) =>
      notificationService.bulkMarkRead(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useBulkArchive = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { notification_ids?: number[]; all_read?: boolean }) =>
      notificationService.bulkArchive(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};

export const useCreateNotification = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NotificationCreatePayload) => notificationService.createNotification(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: notificationKeys.all });
    },
  });
};
