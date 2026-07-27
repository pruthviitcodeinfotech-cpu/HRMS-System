import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { arrearsService } from "../services/arrears";
import {
  ArrearsCreatePayload,
  ArrearsListParams,
  ArrearsLogsParams,
  ArrearsPayPayload,
  ArrearsUpdatePayload,
} from "../types";
import { useBranchContext } from "@/context/branch-context";

export const arrearsKeys = {
  all: ["arrears"] as const,
  lists: () => [...arrearsKeys.all, "list"] as const,
  list: (params: ArrearsListParams) => [...arrearsKeys.lists(), params] as const,
  details: () => [...arrearsKeys.all, "detail"] as const,
  detail: (id: number) => [...arrearsKeys.details(), id] as const,
  logs: () => [...arrearsKeys.all, "logs"] as const,
  logList: (params: ArrearsLogsParams) => [...arrearsKeys.logs(), params] as const,
};

export const useArrears = (params: ArrearsListParams = {}) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: params.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: arrearsKeys.list(effectiveParams),
    queryFn: async () => {
      const res = await arrearsService.getArrears(effectiveParams);
      return (
        res.data || {
          items: [],
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: 0,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        }
      );
    },
    placeholderData: keepPreviousData,
    staleTime: 1000 * 30, // 30 seconds
  });
};

export const useArrearsDetails = (id: number | null) => {
  return useQuery({
    queryKey: arrearsKeys.detail(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      const res = await arrearsService.getArrearsById(id);
      return res.data || null;
    },
    enabled: !!id,
  });
};

export const useArrearsLogs = (params: ArrearsLogsParams = {}, enabled = true) => {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...params,
    branch_id: params.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: arrearsKeys.logList(effectiveParams),
    queryFn: async () => {
      const res = await arrearsService.getArrearsLogs(effectiveParams);
      return (
        res.data || {
          items: [],
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: 0,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        }
      );
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

export const useCreateArrears = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ArrearsCreatePayload) => arrearsService.createArrears(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: arrearsKeys.all });
    },
  });
};

export const useUpdateArrears = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ArrearsUpdatePayload }) =>
      arrearsService.updateArrears(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: arrearsKeys.all });
    },
  });
};

export const usePayArrears = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: ArrearsPayPayload }) =>
      arrearsService.payArrears(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: arrearsKeys.all });
    },
  });
};

export const useDeleteArrears = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => arrearsService.deleteArrears(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: arrearsKeys.all });
    },
  });
};
