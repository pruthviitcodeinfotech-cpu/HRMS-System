import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { loanAdvanceService } from "../services/loan-advance";
import {
  LoanAdvanceCreatePayload,
  LoanAdvanceListParams,
  LoanAdvanceLogsParams,
  LoanAdvanceTransactionCreatePayload,
  LoanAdvanceUpdatePayload,
  LoanAdvanceSchema,
} from "../types";

export const loanAdvanceKeys = {
  all: ["loan-advance"] as const,
  lists: () => [...loanAdvanceKeys.all, "list"] as const,
  list: (params: LoanAdvanceListParams) => [...loanAdvanceKeys.lists(), params] as const,
  details: () => [...loanAdvanceKeys.all, "detail"] as const,
  detail: (id: number) => [...loanAdvanceKeys.details(), id] as const,
  logs: () => [...loanAdvanceKeys.all, "logs"] as const,
  logList: (params: LoanAdvanceLogsParams) => [...loanAdvanceKeys.logs(), params] as const,
  transactions: (params: LoanAdvanceLogsParams) => [...loanAdvanceKeys.logs(), "transactions", params] as const,
  activeForEmployee: (empId: number | null) => [...loanAdvanceKeys.all, "activeForEmployee", empId] as const,
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

export const useAddLoanAdvanceTransaction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: LoanAdvanceTransactionCreatePayload;
    }) => loanAdvanceService.addTransaction(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
    },
  });
};

export const useActiveLoansForEmployee = (employeeId: number | null, enabled = true) => {
  return useQuery({
    queryKey: loanAdvanceKeys.activeForEmployee(employeeId),
    queryFn: async () => {
      if (!employeeId) return [];
      const res = await loanAdvanceService.getActiveLoansForEmployee(employeeId);
      return res.data;
    },
    staleTime: 1000 * 30, // 30 seconds
    enabled: enabled && !!employeeId,
  });
};

export const useSubmitLoanTransaction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      loan_id: number;
      transaction_type: string;
      amount: number;
      comment: string;
      transaction_date: string;
    }) => loanAdvanceService.submitLoanTransaction(payload),
    onSuccess: (_data, variables) => {
      // Invalidate all related loan advance queries (List, Details, Logs, Summary, Active Employee Loans)
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.details() });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.logs() });
      if (variables?.loan_id) {
        queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.detail(variables.loan_id) });
      }
    },
  });
};

export const useLoanTransactions = (params: LoanAdvanceLogsParams = {}, enabled = true) => {
  return useQuery({
    queryKey: loanAdvanceKeys.transactions(params),
    queryFn: async () => {
      const res = await loanAdvanceService.getLoanTransactions(params);
      return res.data;
    },
    staleTime: 1000 * 30, // 30 seconds
    enabled,
  });
};

export const useUpdateInstallment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ loanId, installmentAmount }: { loanId: number; installmentAmount: number }) =>
      loanAdvanceService.updateInstallment(loanId, { installment_amount: installmentAmount }),
    onMutate: async (newInstallment) => {
      // 1. Cancel any outgoing refetches so they don't overwrite optimistic update
      await queryClient.cancelQueries({ queryKey: loanAdvanceKeys.all });

      // 2. Snapshot previous values for rollback
      const previousLoansData = queryClient.getQueryData(loanAdvanceKeys.all);

      // 3. Optimistically update loan lists in cache
      queryClient.setQueriesData({ queryKey: loanAdvanceKeys.lists() }, (old: any) => {
        if (!old || !old.items) return old;
        return {
          ...old,
          items: old.items.map((item: LoanAdvanceSchema) =>
            item.id === newInstallment.loanId
              ? { ...item, monthly_installment: newInstallment.installmentAmount }
              : item
          ),
        };
      });

      // 4. Return context with snapshot
      return { previousLoansData };
    },
    onError: (_err, _newInstallment, context) => {
      // Rollback to snapshot on error
      if (context?.previousLoansData) {
        queryClient.setQueryData(loanAdvanceKeys.all, context.previousLoansData);
      }
    },
    onSettled: (_data, _error, variables) => {
      // Invalidate all related query keys to ensure fresh server state
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.all });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.lists() });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.details() });
      queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.logs() });
      if (variables?.loanId) {
        queryClient.invalidateQueries({ queryKey: loanAdvanceKeys.detail(variables.loanId) });
      }
    },
  });
};


