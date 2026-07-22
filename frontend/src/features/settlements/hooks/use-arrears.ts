import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { arrearsService } from "../services/arrears";
import {
  ArrearsCreatePayload,
  ArrearsListParams,
  ArrearsLogsParams,
  ArrearsPayPayload,
  ArrearsUpdatePayload,
} from "../types";
import { FALLBACK_MOCK_ARREARS, FALLBACK_MOCK_LOGS } from "../data/mock-arrears-data";

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
  return useQuery({
    queryKey: arrearsKeys.list(params),
    queryFn: async () => {
      try {
        const res = await arrearsService.getArrears(params);
        if (res.data?.items && res.data.items.length > 0) {
          return res.data;
        }
        return {
          items: FALLBACK_MOCK_ARREARS,
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: FALLBACK_MOCK_ARREARS.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        };
      } catch {
        return {
          items: FALLBACK_MOCK_ARREARS,
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: FALLBACK_MOCK_ARREARS.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        };
      }
    },
    staleTime: 1000 * 30, // 30 seconds
  });
};

export const useArrearsDetails = (id: number | null) => {
  return useQuery({
    queryKey: arrearsKeys.detail(id ?? 0),
    queryFn: async () => {
      if (!id) return null;
      try {
        const res = await arrearsService.getArrearsById(id);
        return res.data;
      } catch {
        const found = FALLBACK_MOCK_ARREARS.find((item) => item.id === id);
        return found || null;
      }
    },
    enabled: !!id,
  });
};

export const useArrearsLogs = (params: ArrearsLogsParams = {}, enabled = true) => {
  return useQuery({
    queryKey: arrearsKeys.logList(params),
    queryFn: async () => {
      try {
        const res = await arrearsService.getArrearsLogs(params);
        if (res.data?.items && res.data.items.length > 0) {
          return res.data;
        }
        return {
          items: FALLBACK_MOCK_LOGS,
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: FALLBACK_MOCK_LOGS.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        };
      } catch {
        return {
          items: FALLBACK_MOCK_LOGS,
          pagination: {
            page: params.page || 1,
            page_size: params.page_size || 10,
            total_records: FALLBACK_MOCK_LOGS.length,
            total_pages: 1,
            has_next: false,
            has_previous: false,
          },
        };
      }
    },
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

export const useDeleteArrears = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => arrearsService.deleteArrears(id),
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
