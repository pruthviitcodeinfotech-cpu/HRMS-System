import { keepPreviousData, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import { useBranchContext } from "@/context/branch-context";

export const useApprovalsList = (params: ApprovalQueryParams = {}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: params.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "list", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getApprovals(effectiveParams);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

export const usePendingApprovals = (
  params?: {
    branch_id?: number;
    dept_id?: number;
    page?: number;
    page_size?: number;
  },
  options?: { enabled?: boolean }
) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "pending", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getPendingApprovals(effectiveParams);
      return response.data;
    },
    ...options,
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
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "history", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getApprovalHistory(effectiveParams);
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
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "my-pending", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getMyPendingApprovals(effectiveParams);
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
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: params.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "recent", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getRecentDecisions(effectiveParams);
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
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: ["approvals", "pending-count", effectiveParams],
    queryFn: async () => {
      const response = await approvalService.getPendingCount(effectiveParams);
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
