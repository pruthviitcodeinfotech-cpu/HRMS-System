import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { payrollService } from "../services/payroll";

export const payrollKeys = {
  all: ["payroll"] as const,
  groups: (params?: Record<string, unknown>) => [...payrollKeys.all, "groups", params || {}] as const,
  groupDetails: (id: number) => [...payrollKeys.all, "group-details", id] as const,
  groupEmployees: (groupId: number, params?: Record<string, unknown>) => [...payrollKeys.all, "group-employees", groupId, params || {}] as const,
  cycles: (params?: Record<string, unknown>) => [...payrollKeys.all, "cycles", params || {}] as const,
  adjustments: (params?: Record<string, unknown>) => [...payrollKeys.all, "adjustments", params || {}] as const,
  bulkMatrix: (params?: Record<string, unknown>) => [...payrollKeys.all, "bulk-matrix", params || {}] as const,
  finalizedRuns: (params?: Record<string, unknown>) => [...payrollKeys.all, "finalized-runs", params || {}] as const,
  finalizedPayroll: (params?: Record<string, unknown>) => [...payrollKeys.all, "finalized-payroll", params || {}] as const,
  finalizedPayrollDetail: (id: number) => [...payrollKeys.all, "finalized-payroll-detail", id] as const,
};

export const usePayrollGroups = (params?: {
  search?: string;
  payroll_type?: string;
  is_default?: boolean;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
}) => {
  return useQuery({
    queryKey: payrollKeys.groups(params),
    queryFn: async () => {
      const res = await payrollService.getGroups(params);
      return res.data;
    },
  });
};

export const usePayrollGroupDetails = (id: number) => {
  return useQuery({
    queryKey: payrollKeys.groupDetails(id),
    queryFn: async () => {
      const res = await payrollService.getGroupDetails(id);
      return res.data;
    },
    enabled: !!id,
  });
};

export const useCreatePayrollGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; payroll_type: string; is_default?: boolean }) => {
      const res = await payrollService.createGroup(data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useUpdatePayrollGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: { name?: string; payroll_type?: string; is_default?: boolean } }) => {
      const res = await payrollService.updateGroup(id, data);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useDeletePayrollGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await payrollService.deleteGroup(id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useAssignEmployeesToGroup = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ groupId, payload }: { groupId: number; payload: { employee_ids: number[]; salary_type?: "monthly" | "hourly" } }) => {
      const res = await payrollService.assignEmployeesToGroup(groupId, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.all });
    },
  });
};

export const useGroupEmployees = (groupId: number, params?: { page?: number; page_size?: number; search?: string }) => {
  return useQuery({
    queryKey: payrollKeys.groupEmployees(groupId, params),
    queryFn: async () => {
      const res = await payrollService.getGroupEmployees(groupId, params);
      return res.data;
    },
    enabled: !!groupId,
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

// ============================================================
// Finalized Payroll History Hooks
// ============================================================

export const useFinalizedPayroll = (params?: {
  page?: number;
  page_size?: number;
  payroll_group_id?: number;
  from_date?: string;
  to_date?: string;
  status?: string;
}) => {
  return useQuery({
    queryKey: payrollKeys.finalizedPayroll(params),
    queryFn: async () => {
      const res = await payrollService.getFinalizedPayroll(params);
      return res.data;
    },
    retry: 2,
    staleTime: 30_000,
  });
};

export const useFinalizedPayrollDetails = (id: number | null) => {
  return useQuery({
    queryKey: payrollKeys.finalizedPayrollDetail(id ?? 0),
    queryFn: async () => {
      const res = await payrollService.getFinalizedPayrollDetails(id!);
      return res.data;
    },
    enabled: !!id,
    retry: 2,
  });
};

export const usePayPayroll = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload?: { paid_amount?: number; paid_on?: string; payment_method?: string; remarks?: string };
    }) => {
      const res = await payrollService.payFinalizedPayroll(id, payload);
      return res.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: payrollKeys.finalizedPayroll() });
    },
  });
};
