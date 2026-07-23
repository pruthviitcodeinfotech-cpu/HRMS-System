import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { payrollService } from "../services/payroll";

export const payrollKeys = {
  all: ["payroll"] as const,
  groups: (params?: Record<string, unknown>) => [...payrollKeys.all, "groups", params || {}] as const,
  cycles: (params?: Record<string, unknown>) => [...payrollKeys.all, "cycles", params || {}] as const,
  adjustments: (params?: Record<string, unknown>) => [...payrollKeys.all, "adjustments", params || {}] as const,
  bulkMatrix: (params?: Record<string, unknown>) => [...payrollKeys.all, "bulk-matrix", params || {}] as const,
  finalizedRuns: (params?: Record<string, unknown>) => [...payrollKeys.all, "finalized-runs", params || {}] as const,
};

export const usePayrollGroups = (params?: { page?: number; page_size?: number }) => {
  return useQuery({
    queryKey: payrollKeys.groups(params),
    queryFn: async () => {
      const res = await payrollService.getGroups(params);
      return res.data;
    },
  });
};

export const usePayrollCycles = (params?: { group_id?: number; is_finalized?: boolean; page?: number; page_size?: number }) => {
  return useQuery({
    queryKey: payrollKeys.cycles(params),
    queryFn: async () => {
      const res = await payrollService.getCycles(params);
      return res.data;
    },
  });
};

export const useFinalizedPayrollRuns = (params?: { page?: number; page_size?: number; payroll_group_id?: number }) => {
  return useQuery({
    queryKey: payrollKeys.finalizedRuns(params),
    queryFn: async () => {
      const res = await payrollService.getFinalizedRuns(params);
      return res.data;
    },
  });
};

export const useAttendanceAdjustments = (params?: { employee_id?: number; page?: number; page_size?: number }) => {
  return useQuery({
    queryKey: payrollKeys.adjustments(params),
    queryFn: async () => {
      const res = await payrollService.getAdjustments(params);
      return res.data;
    },
  });
};

export const useBulkAttendanceMatrix = (params: {
  date_from: string;
  date_to: string;
  branch_id?: number;
  dept_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
}) => {
  return useQuery({
    queryKey: payrollKeys.bulkMatrix(params),
    queryFn: async () => {
      const res = await payrollService.getBulkAttendanceMatrix(params);
      return res.data;
    },
  });
};

export const useBatchUpdateBulkAttendanceAdjustments = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      date_from?: string;
      date_to?: string;
      updates: {
        employee_id: number;
        attendance_date: string;
        adjusted_status: string;
        original_status?: string | null;
        reason?: string | null;
      }[];
    }) => {
      const res = await payrollService.batchUpdateBulkAttendanceAdjustments(data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useResetBulkAttendanceAdjustments = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      date_from: string;
      date_to: string;
      branch_id?: number;
      employee_ids?: number[];
    }) => {
      const res = await payrollService.resetBulkAttendanceAdjustments(data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

// Process Payroll React Query Hooks (Phase 3)
export const useProcessPayrollMatrix = (params: {
  date_from: string;
  date_to: string;
  payroll_group_id?: number;
  branch_id?: number;
  dept_id?: number;
  search?: string;
  page?: number;
  page_size?: number;
  enabled?: boolean;
}) => {
  const { enabled = true, ...queryParams } = params;
  return useQuery({
    queryKey: [...payrollKeys.all, "process-matrix", queryParams],
    queryFn: async () => {
      const res = await payrollService.getProcessPayrollMatrix(queryParams);
      return res.data;
    },
    enabled: enabled && Boolean(params.date_from) && Boolean(params.date_to),
  });
};

export const useCalculateProcessPayroll = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      payroll_group_id: number;
      cycle_from: string;
      cycle_to: string;
      employee_ids?: number[];
    }) => {
      const res = await payrollService.calculateProcessPayroll(data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useFinalizeProcessPayroll = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      payroll_group_id: number;
      cycle_from: string;
      cycle_to: string;
    }) => {
      const res = await payrollService.finalizeProcessPayroll(data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useProcessPayrollEmployeeDetail = (
  employeeId: number,
  params: { date_from: string; date_to: string },
  enabled = true
) => {
  return useQuery({
    queryKey: [...payrollKeys.all, "process-employee-detail", employeeId, params],
    queryFn: async () => {
      const res = await payrollService.getProcessPayrollEmployeeDetail(employeeId, params);
      return res.data;
    },
    enabled: enabled && Boolean(employeeId) && Boolean(params.date_from) && Boolean(params.date_to),
  });
};

