import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { userService, UserQueryParams, CreateUserInput, UpdateUserInput } from "../services/user-service";
import { RIGHTS_TEMPLATES_QUERY_KEY } from "./use-rights-templates";
import { toast } from "sonner";

export const USERS_QUERY_KEY = ["users"];

export function useUsers(params?: UserQueryParams) {
  return useQuery({
    queryKey: [...USERS_QUERY_KEY, params],
    queryFn: async () => {
      const res = await userService.getUsers(params);
      return res.data;
    },
  });
}

export function useUserDetail(id?: number) {
  return useQuery({
    queryKey: [...USERS_QUERY_KEY, "detail", id],
    queryFn: async () => {
      if (!id) return null;
      const res = await userService.getUserById(id);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateUserInput) => userService.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      toast.success("User created successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to create user");
    },
  });
}

export function useUpdateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateUserInput }) =>
      userService.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      toast.success("User updated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to update user");
    },
  });
}

export function useActivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => userService.activateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      toast.success("User account activated");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to activate user account");
    },
  });
}

export function useDeactivateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => userService.deactivateUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      toast.success("User account deactivated");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to deactivate user account");
    },
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => userService.deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      toast.success("User deleted successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to delete user");
    },
  });
}

export function useAssignUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, templateId }: { userId: number; templateId: number }) =>
      userService.assignUserRole(userId, templateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template assigned successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to assign rights template");
    },
  });
}

export function useRemoveUserRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => userService.removeUserRole(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template assignment removed");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to remove rights template assignment");
    },
  });
}

export function useBulkAssignRole() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userIds, templateId }: { userIds: number[]; templateId: number }) =>
      userService.bulkAssignRole(userIds, templateId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: USERS_QUERY_KEY });
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success(`Rights template assigned to ${data?.data?.assigned_count || "selected"} users`);
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to bulk assign rights template");
    },
  });
}
