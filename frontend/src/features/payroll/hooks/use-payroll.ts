import { useQuery } from "@tanstack/react-query";
import { payrollService } from "../services/payroll";

export const payrollKeys = {
  all: ["payroll"] as const,
  groups: (params?: Record<string, unknown>) => [...payrollKeys.all, "groups", params || {}] as const,
  cycles: (params?: Record<string, unknown>) => [...payrollKeys.all, "cycles", params || {}] as const,
  adjustments: (params?: Record<string, unknown>) => [...payrollKeys.all, "adjustments", params || {}] as const,
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
