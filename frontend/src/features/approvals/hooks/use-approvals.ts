import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { approvalService } from "../services/approvals";
import {
  ApprovalQueryParams,
  ApproveRequestPayload,
  RejectRequestPayload,
  BulkApprovePayload,
  BulkRejectPayload,
  BackendRequestType,
  ApprovalStatus,
} from "../types";

export const useApprovalsList = (params: ApprovalQueryParams = {}) => {
  return useQuery({
    queryKey: ["approvals", "list", params],
    queryFn: async () => {
      const response = await approvalService.getApprovals(params);
      return response.data;
    },
  });
};

export const usePendingApprovals = (params?: {
  branch_id?: number;
  dept_id?: number;
  page?: number;
  page_size?: number;
}) => {
  return useQuery({
    queryKey: ["approvals", "pending", params || {}],
    queryFn: async () => {
      const response = await approvalService.getPendingApprovals(params);
      return response.data;
    },
  });
};

export const useApprovalHistory = (params?: {
  request_type?: BackendRequestType;
  employee_id?: number;
  date_from?: string;
  date_to?: string;
  branch_id?: number;
  dept_id?: number;
  page?: number;
  page_size?: number;
}) => {
  return useQuery({
    queryKey: ["approvals", "history", params || {}],
    queryFn: async () => {
      const response = await approvalService.getApprovalHistory(params);
      return response.data;
    },
  });
};

export const useMyPendingApprovals = (params?: {
  branch_id?: number;
  dept_id?: number;
  page?: number;
  page_size?: number;
}) => {
  return useQuery({
    queryKey: ["approvals", "my-pending", params || {}],
    queryFn: async () => {
      const response = await approvalService.getMyPendingApprovals(params);
      return response.data;
    },
  });
};

export const useRecentDecisions = (params: {
  decision: ApprovalStatus;
  request_type?: BackendRequestType;
  branch_id?: number;
  dept_id?: number;
  limit?: number;
}) => {
  return useQuery({
    queryKey: ["approvals", "recent", params],
    queryFn: async () => {
      const response = await approvalService.getRecentDecisions(params);
      return response.data;
    },
  });
};

export const useApprovalDetails = (id: number | null) => {
  return useQuery({
    queryKey: ["approvals", "details", id],
    queryFn: async () => {
      if (!id) return null;
      const response = await approvalService.getApprovalDetails(id);
      return response.data;
    },
    enabled: !!id,
  });
};

export const useApprovalStatus = (id: number | null) => {
  return useQuery({
    queryKey: ["approvals", "status", id],
    queryFn: async () => {
      if (!id) return null;
      const response = await approvalService.getApprovalStatus(id);
      return response.data;
    },
    enabled: !!id,
  });
};

export const useApprovalTimeline = (id: number | null) => {
  return useQuery({
    queryKey: ["approvals", "timeline", id],
    queryFn: async () => {
      if (!id) return null;
      const response = await approvalService.getApprovalTimeline(id);
      return response.data;
    },
    enabled: !!id,
  });
};

export const usePendingApprovalCount = (params?: { branch_id?: number; dept_id?: number }) => {
  return useQuery({
    queryKey: ["approvals", "pending-count", params || {}],
    queryFn: async () => {
      const response = await approvalService.getPendingCount(params);
      return response.data;
    },
  });
};

export const useApproveRequest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload?: ApproveRequestPayload }) => {
      const response = await approvalService.approveRequest(id, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

export const useRejectRequest = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: RejectRequestPayload }) => {
      const response = await approvalService.rejectRequest(id, payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

export const useBulkApproveRequests = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BulkApprovePayload) => {
      const response = await approvalService.bulkApprove(payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

export const useBulkRejectRequests = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BulkRejectPayload) => {
      const response = await approvalService.bulkReject(payload);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};
