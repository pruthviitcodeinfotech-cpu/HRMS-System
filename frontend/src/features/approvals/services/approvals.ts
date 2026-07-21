import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  ApprovalQueryParams,
  ApprovalListResponse,
  ApprovalDetailsSchema,
  ApprovalStatusSchema,
  ApprovalTimelineEventSchema,
  ApprovalPendingCountSchema,
  ApprovalRequestSchema,
  ApproveRequestPayload,
  RejectRequestPayload,
  BulkApprovePayload,
  BulkRejectPayload,
  BulkActionResponse,
  BackendRequestType,
  ApprovalStatus,
} from "../types";

const buildQueryString = (params?: Record<string, unknown>): string => {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.append(key, String(value));
    }
  });
  return query.toString();
};

export const approvalService = {
  getApprovals: async (
    params: ApprovalQueryParams = {}
  ): Promise<ApiResponse<ApprovalListResponse>> => {
    const q = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<ApprovalListResponse>>(q ? `/approvals?${q}` : "/approvals");
  },

  getPendingApprovals: async (params?: {
    branch_id?: number;
    dept_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<ApprovalListResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<ApprovalListResponse>>(
      q ? `/approvals/pending?${q}` : "/approvals/pending"
    );
  },

  getApprovalHistory: async (params?: {
    request_type?: BackendRequestType;
    employee_id?: number;
    date_from?: string;
    date_to?: string;
    branch_id?: number;
    dept_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<ApprovalListResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<ApprovalListResponse>>(
      q ? `/approvals/history?${q}` : "/approvals/history"
    );
  },

  getMyPendingApprovals: async (params?: {
    branch_id?: number;
    dept_id?: number;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<ApprovalListResponse>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<ApprovalListResponse>>(
      q ? `/approvals/my-pending?${q}` : "/approvals/my-pending"
    );
  },

  getRecentDecisions: async (params: {
    decision: ApprovalStatus;
    request_type?: BackendRequestType;
    branch_id?: number;
    dept_id?: number;
    limit?: number;
  }): Promise<ApiResponse<ApprovalRequestSchema[]>> => {
    const q = buildQueryString(params as Record<string, unknown>);
    return apiClient.get<ApiResponse<ApprovalRequestSchema[]>>(`/approvals/recent?${q}`);
  },

  getApprovalDetails: async (id: number): Promise<ApiResponse<ApprovalDetailsSchema>> => {
    return apiClient.get<ApiResponse<ApprovalDetailsSchema>>(`/approvals/${id}`);
  },

  getApprovalStatus: async (id: number): Promise<ApiResponse<ApprovalStatusSchema>> => {
    return apiClient.get<ApiResponse<ApprovalStatusSchema>>(`/approvals/${id}/status`);
  },

  getApprovalTimeline: async (
    id: number
  ): Promise<ApiResponse<ApprovalTimelineEventSchema[]>> => {
    return apiClient.get<ApiResponse<ApprovalTimelineEventSchema[]>>(`/approvals/${id}/timeline`);
  },

  getPendingCount: async (params?: {
    branch_id?: number;
    dept_id?: number;
  }): Promise<ApiResponse<ApprovalPendingCountSchema>> => {
    const q = buildQueryString(params);
    return apiClient.get<ApiResponse<ApprovalPendingCountSchema>>(
      q ? `/approvals/summary/pending-count?${q}` : "/approvals/summary/pending-count"
    );
  },

  approveRequest: async (
    id: number,
    payload: ApproveRequestPayload = {}
  ): Promise<ApiResponse<ApprovalRequestSchema>> => {
    return apiClient.post<ApiResponse<ApprovalRequestSchema>>(`/approvals/${id}/approve`, payload);
  },

  rejectRequest: async (
    id: number,
    payload: RejectRequestPayload
  ): Promise<ApiResponse<ApprovalRequestSchema>> => {
    return apiClient.post<ApiResponse<ApprovalRequestSchema>>(`/approvals/${id}/reject`, payload);
  },

  bulkApprove: async (payload: BulkApprovePayload): Promise<ApiResponse<BulkActionResponse>> => {
    return apiClient.post<ApiResponse<BulkActionResponse>>("/approvals/bulk-approve", payload);
  },

  bulkReject: async (payload: BulkRejectPayload): Promise<ApiResponse<BulkActionResponse>> => {
    return apiClient.post<ApiResponse<BulkActionResponse>>("/approvals/bulk-reject", payload);
  },
};
