import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dashboardService } from "../services/dashboard";

export const useDashboardKPIs = (date?: string) => {
  return useQuery({
    queryKey: ["dashboard", "kpis", date || "today"],
    queryFn: async () => {
      const response = await dashboardService.getKPIs(date);
      return response.data;
    },
  });
};

export const useAttendanceSummary = (date?: string) => {
  return useQuery({
    queryKey: ["dashboard", "attendance-summary", date || "today"],
    queryFn: async () => {
      const response = await dashboardService.getAttendanceSummary(date);
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
  return useQuery({
    queryKey: ["dashboard", "attendance-days", params],
    queryFn: async () => {
      const response = await dashboardService.getAttendanceDays(params);
      return response.data;
    },
    enabled: !!params.date,
  });
};

export const useShiftSummary = (date?: string) => {
  return useQuery({
    queryKey: ["dashboard", "shifts", date || "today"],
    queryFn: async () => {
      const response = await dashboardService.getShiftSummary(date);
      return response.data;
    },
  });
};

export const useDepartmentAttendance = (date?: string) => {
  return useQuery({
    queryKey: ["dashboard", "department-attendance", date || "today"],
    queryFn: async () => {
      const response = await dashboardService.getDepartmentAttendance(date);
      return response.data;
    },
  });
};

export const useDevicesList = (params?: {
  page?: number;
  page_size?: number;
  status?: "online" | "offline";
}) => {
  return useQuery({
    queryKey: ["dashboard", "devices", params || {}],
    queryFn: async () => {
      const response = await dashboardService.getDevices(params);
      return response.data;
    },
  });
};

export const useApprovalsDashboard = () => {
  return useQuery({
    queryKey: ["dashboard", "approvals"],
    queryFn: async () => {
      const response = await dashboardService.getApprovals();
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
      queryClient.invalidateQueries({ queryKey: ["dashboard", "approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "kpis"] });
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
      queryClient.invalidateQueries({ queryKey: ["dashboard", "approvals"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", "kpis"] });
    },
  });
};

export const usePendingBiometrics = (params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) => {
  return useQuery({
    queryKey: ["dashboard", "biometrics-pending", params || {}],
    queryFn: async () => {
      const response = await dashboardService.getPendingBiometrics(params);
      return response.data;
    },
  });
};
