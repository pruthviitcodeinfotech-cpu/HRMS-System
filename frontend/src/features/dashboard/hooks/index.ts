import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardService } from "../services/dashboard";
import { useBranchContext } from "@/context/branch-context";

export const useDashboardKPIs = (date?: string, branch_id?: number | null) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveBranchId = branch_id !== undefined ? branch_id : selectedBranchId;
  return useQuery({
    queryKey: ["dashboard", "kpis", date || "today", effectiveBranchId ?? "all"],
    queryFn: async () => {
      const response = await dashboardService.getKPIs(date, effectiveBranchId);
      return response.data;
    },
  });
};

export const useAttendanceSummary = (date?: string, branch_id?: number | null) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveBranchId = branch_id !== undefined ? branch_id : selectedBranchId;
  return useQuery({
    queryKey: ["dashboard", "attendance-summary", date || "today", effectiveBranchId ?? "all"],
    queryFn: async () => {
      const response = await dashboardService.getAttendanceSummary(date, effectiveBranchId);
      return response.data;
    },
  });
};

export const useAttendanceDays = (params: {
  date: string;
  branch_id?: number | null;
  department_id?: number | null;
  page?: number;
  page_size?: number;
}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: params.branch_id !== undefined ? params.branch_id : selectedBranchId,
  };
  return useQuery({
    queryKey: ["dashboard", "attendance-days", effectiveParams],
    queryFn: async () => {
      const response = await dashboardService.getAttendanceDays(effectiveParams);
      return response.data;
    },
    enabled: !!params.date,
  });
};

export const useShiftSummary = (date?: string, branch_id?: number | null) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveBranchId = branch_id !== undefined ? branch_id : selectedBranchId;
  return useQuery({
    queryKey: ["dashboard", "shifts", date || "today", effectiveBranchId ?? "all"],
    queryFn: async () => {
      const response = await dashboardService.getShiftSummary(date, effectiveBranchId);
      return response.data;
    },
  });
};

export const useDepartmentAttendance = (date?: string, branch_id?: number | null) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveBranchId = branch_id !== undefined ? branch_id : selectedBranchId;
  return useQuery({
    queryKey: ["dashboard", "department-attendance", date || "today", effectiveBranchId ?? "all"],
    queryFn: async () => {
      const response = await dashboardService.getDepartmentAttendance(date, effectiveBranchId);
      return response.data;
    },
  });
};

export const useDevicesList = (params?: {
  page?: number;
  page_size?: number;
  status?: "online" | "offline";
  branch_id?: number | null;
}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id !== undefined ? params.branch_id : selectedBranchId,
  };
  return useQuery({
    queryKey: ["dashboard", "devices", effectiveParams],
    queryFn: async () => {
      const response = await dashboardService.getDevices(effectiveParams);
      return response.data;
    },
  });
};

export const useApprovalsDashboard = (branch_id?: number | null) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveBranchId = branch_id !== undefined ? branch_id : selectedBranchId;
  return useQuery({
    queryKey: ["dashboard", "approvals", effectiveBranchId ?? "all"],
    queryFn: async () => {
      const response = await dashboardService.getApprovals(effectiveBranchId);
      return response.data;
    },
  });
};

export const useApproveApproval = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const response = await dashboardService.approveRequest(id, remarks);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["approval-requests"] });
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["approval-requests"] });
    },
  });
};

export const useRejectApproval = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, remarks }: { id: number; remarks?: string }) => {
      const response = await dashboardService.rejectRequest(id, remarks);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["approval-requests"] });
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
      queryClient.invalidateQueries({ queryKey: ["approval-requests"] });
    },
  });
};

export const usePendingBiometrics = (params?: {
  page?: number;
  page_size?: number;
  search?: string;
  branch_id?: number | null;
}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id !== undefined ? params.branch_id : selectedBranchId,
  };
  return useQuery({
    queryKey: ["dashboard", "biometrics-pending", effectiveParams],
    queryFn: async () => {
      const response = await dashboardService.getPendingBiometrics(effectiveParams);
      return response.data;
    },
  });
};
