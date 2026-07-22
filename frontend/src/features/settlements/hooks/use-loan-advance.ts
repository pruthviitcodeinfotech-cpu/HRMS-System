import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loanAdvanceService } from "../services/loan-advance";
import {
  LoanAdvanceCreatePayload,
  LoanAdvanceListParams,
  LoanAdvanceLogsParams,
  LoanAdvanceUpdatePayload,
} from "../types";

export const loanAdvanceKeys = {
  all: ["loan-advance"] as const,
  lists: () => [...loanAdvanceKeys.all, "list"] as const,
  list: (params: LoanAdvanceListParams) => [...loanAdvanceKeys.lists(), params] as const,
  details: () => [...loanAdvanceKeys.all, "detail"] as const,
  detail: (id: number) => [...loanAdvanceKeys.details(), id] as const,
  logs: () => [...loanAdvanceKeys.all, "logs"] as const,
  logList: (params: LoanAdvanceLogsParams) => [...loanAdvanceKeys.logs(), params] as const,
};

export const useLoansAdvances = (params: LoanAdvanceListParams = {}) => {
  return useQuery({
    queryKey: loanAdvanceKeys.list(params),
    queryFn: async () => {
      const res = await loanAdvanceService.getLoansAdvances(params);
      return res.data;
    },
    staleTime: 1000 * 30, // 30 seconds
  });
};

export const useLoanAdvanceDetails = (id: number | null) => {
  return useQuery({
    queryKey: loanAdvanceKeys.detail(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await loanAdvanceService.getLoanAdvanceById(id);
      return res.data;
    },
    enabled: !!id,
  });
};

export const useLoanAdvanceLogs = (params: LoanAdvanceLogsParams = {}, enabled = true) => {
  return useQuery({
    queryKey: loanAdvanceKeys.logList(params),
    queryFn: async () => {
      const res = await loanAdvanceService.getLoanAdvanceLogs(params);
      return res.data;
    },
    enabled,
  });
};

export const useCreateLoanAdvance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: LoanAdvanceCreatePayload) =>
      loanAdvanceService.createLoanAdvance(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
    },
  });
};

export const useUpdateLoanAdvance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: LoanAdvanceUpdatePayload }) =>
      loanAdvanceService.updateLoanAdvance(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
    },
  });
};

export const useCloseLoanAdvance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => loanAdvanceService.closeLoanAdvance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
    },
  });
};

export const useDeleteLoanAdvance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => loanAdvanceService.deleteLoanAdvance(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
    },
  });
};
