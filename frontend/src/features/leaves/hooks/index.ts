import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { leaveService } from "../services";
import {
  LeaveTypeCreateRequest,
  LeaveTypeListParams,
  LeaveTypeUpdateRequest,
  LeaveSettingsUpdateRequest,
} from "../types";

// Query-key factory
export const leaveKeys = {
  all: ["leaves"] as const,
  lists: () => [...leaveKeys.all, "list"] as const,
  list: (params: LeaveTypeListParams) => [...leaveKeys.lists(), params] as const,
  detail: (id: number) => [...leaveKeys.all, "detail", id] as const,
  settings: () => [...leaveKeys.all, "settings"] as const,
};

/**
 * Paginated / filtered / sorted leave types list (GET /leave-types).
 */
export const useLeaveTypes = (params: LeaveTypeListParams = {}) => {
  return useQuery({
    queryKey: leaveKeys.list(params),
    queryFn: async () => {
      const response = await leaveService.getLeaveTypes(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/**
 * Single leave type detail (GET /leave-types/{id}).
 */
export const useLeaveType = (id: number, enabled = true) => {
  return useQuery({
    queryKey: leaveKeys.detail(id),
    queryFn: async () => {
      const response = await leaveService.getLeaveType(id);
      return response.data;
    },
    enabled: enabled && Boolean(id),
  });
};

/**
 * Create leave type (POST /leave-types).
 */
export const useCreateLeaveType = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: LeaveTypeCreateRequest) => {
      const response = await leaveService.createLeaveType(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
};

/**
 * Update leave type (PATCH /leave-types/{id}).
 */
export const useUpdateLeaveType = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: LeaveTypeUpdateRequest }) => {
      const response = await leaveService.updateLeaveType(id, data);
      return response.data;
    },
    onSuccess: (updatedItem) => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      if (updatedItem?.id) {
        queryClient.invalidateQueries({ queryKey: leaveKeys.detail(updatedItem.id) });
      }
    },
  });
};

/**
 * Delete leave type (DELETE /leave-types/{id}).
 */
export const useDeleteLeaveType = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await leaveService.deleteLeaveType(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.all });
    },
  });
};

/**
 * Fetch org leave settings (GET /leave-settings).
 */
export const useLeaveSettings = () => {
  return useQuery({
    queryKey: leaveKeys.settings(),
    queryFn: async () => {
      const response = await leaveService.getLeaveSettings();
      return response.data;
    },
  });
};

/**
 * Update org leave settings (PUT /leave-settings).
 */
export const useUpdateLeaveSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: LeaveSettingsUpdateRequest) => {
      const response = await leaveService.updateLeaveSettings(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leaveKeys.settings() });
    },
  });
};
