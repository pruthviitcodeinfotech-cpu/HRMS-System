import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { shiftService } from "../services";
import { CreateShiftRequest, ShiftListParams, UpdateShiftRequest } from "../types";

// ---------------------------------------------------------------------------
// Query-key factory
// ---------------------------------------------------------------------------
export const shiftKeys = {
  all: ["shifts"] as const,
  lists: () => [...shiftKeys.all, "list"] as const,
  list: (params: ShiftListParams) => [...shiftKeys.lists(), params] as const,
  detail: (id: number) => [...shiftKeys.all, "detail", id] as const,
};

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

/**
 * Paginated / filtered / sorted shift list (GET /shifts).
 * keepPreviousData keeps the last page visible during navigation.
 */
export const useShifts = (params: ShiftListParams) => {
  return useQuery({
    queryKey: shiftKeys.list(params),
    queryFn: async () => {
      const response = await shiftService.getShifts(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/** Shift detail with day_timings (GET /shifts/{id}). */
export const useShift = (shiftId: number, enabled = true) => {
  return useQuery({
    queryKey: shiftKeys.detail(shiftId),
    queryFn: async () => {
      const response = await shiftService.getShift(shiftId);
      return response.data;
    },
    enabled: enabled && !!shiftId,
  });
};

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export const useCreateShift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateShiftRequest) => {
      const response = await shiftService.createShift(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.all });
    },
  });
};

export const useUpdateShift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: UpdateShiftRequest }) => {
      const response = await shiftService.updateShift(id, data);
      return response.data;
    },
    onSuccess: (updatedShift) => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.all });
      queryClient.invalidateQueries({
        queryKey: shiftKeys.detail(updatedShift.shift_id),
      });
    },
  });
};

/**
 * Restore a soft-deleted shift.
 * The backend has no separate "activate" endpoint for shifts;
 * POST /shifts/{id}/restore is the only way to un-delete.
 */
export const useRestoreShift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (shiftId: number) => {
      const response = await shiftService.restoreShift(shiftId);
      return response.data;
    },
    onSuccess: (restoredShift) => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.all });
      queryClient.invalidateQueries({
        queryKey: shiftKeys.detail(restoredShift.shift_id),
      });
    },
  });
};

/**
 * Soft-delete a shift (DELETE /shifts/{id}).
 * Blocked by backend when active assignments or upcoming roster entries reference it.
 */
export const useDeleteShift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (shiftId: number) => {
      await shiftService.deleteShift(shiftId);
      return shiftId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.all });
    },
  });
};
