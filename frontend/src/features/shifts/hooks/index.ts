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
  weekoffs: (employeeId: number) => [...shiftKeys.all, "weekoffs", employeeId] as const,
  allWeekoffs: () => [...shiftKeys.all, "weekoffs"] as const,
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

/**
 * Bulk assign a shift to multiple employees (POST /shift-assignments/bulk).
 * Invalidates shifts and employee queries on success.
 */
export const useBulkAssignShift = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: import("../types").ShiftAssignmentBulkRequest) => {
      const response = await shiftService.bulkAssignShift(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees"] });
    },
  });
};

/**
 * List shift assignments (GET /shift-assignments).
 */
export const useShiftAssignments = (params: import("../types").ShiftAssignmentQuery) => {
  return useQuery({
    queryKey: [...shiftKeys.all, "assignments", params] as const,
    queryFn: async () => {
      const response = await shiftService.listAssignments(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/**
 * Fetch employee week-off configuration (GET /employees/{employee_id}/weekoffs).
 */
export const useEmployeeWeekoffs = (
  employeeId: number,
  includeHistory = false,
  enabled = true
) => {
  return useQuery({
    queryKey: [...shiftKeys.weekoffs(employeeId), { includeHistory }] as const,
    queryFn: async () => {
      const response = await shiftService.getEmployeeWeekoffs(employeeId, includeHistory);
      return response.data;
    },
    enabled: !!employeeId && enabled,
    placeholderData: keepPreviousData,
  });
};

/**
 * Configure employee week-off (PUT /employees/{employee_id}/weekoffs).
 */
export const useConfigureWeekoffs = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      employeeId,
      data,
    }: {
      employeeId: number;
      data: import("../types").WeekoffConfigureRequest;
    }) => {
      const response = await shiftService.configureEmployeeWeekoffs(employeeId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.weekoffs(variables.employeeId) });
      queryClient.invalidateQueries({ queryKey: shiftKeys.allWeekoffs() });
    },
  });
};

/**
 * Patch single week-off rule (PATCH /employees/{employee_id}/weekoffs/{weekoff_id}).
 */
export const useUpdateWeekoff = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      employeeId,
      weekoffId,
      data,
    }: {
      employeeId: number;
      weekoffId: number;
      data: import("../types").WeekoffPatchRequest;
    }) => {
      const response = await shiftService.updateEmployeeWeekoff(employeeId, weekoffId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.weekoffs(variables.employeeId) });
      queryClient.invalidateQueries({ queryKey: shiftKeys.allWeekoffs() });
    },
  });
};

/**
 * Bulk configure week offs for multiple employees.
 */
export const useBulkWeekoffUpdate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      employeeIds,
      weekoffs,
    }: {
      employeeIds: number[];
      weekoffs: import("../types").WeekoffItemInput[];
    }) => {
      const results = await Promise.all(
        employeeIds.map((empId) =>
          shiftService.configureEmployeeWeekoffs(empId, { weekoffs })
        )
      );
      return results.map((r) => r.data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: shiftKeys.allWeekoffs() });
    },
  });
};

// ---------------------------------------------------------------------------
// Roster hooks
// ---------------------------------------------------------------------------

export const rosterKeys = {
  all: ["roster"] as const,
  lists: () => [...rosterKeys.all, "list"] as const,
  list: (params: import("../types").RosterQuery) => [...rosterKeys.lists(), params] as const,
  employee: (employeeId: number, params: { date_from?: string; date_to?: string; month?: string }) =>
    [...rosterKeys.all, "employee", employeeId, params] as const,
  resolve: (params: import("../types").ShiftResolveQuery) =>
    [...rosterKeys.all, "resolve", params] as const,
};

/**
 * Fetch roster entries (GET /roster).
 */
export const useRoster = (params: import("../types").RosterQuery, enabled = true) => {
  return useQuery({
    queryKey: rosterKeys.list(params),
    queryFn: async () => {
      const response = await shiftService.getRoster(params);
      return response.data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });
};

/**
 * Fetch employee shift calendar (GET /employees/{employee_id}/roster).
 */
export const useEmployeeRoster = (
  employeeId: number,
  params: { date_from?: string; date_to?: string; month?: string } = {},
  enabled = true
) => {
  return useQuery({
    queryKey: rosterKeys.employee(employeeId, params),
    queryFn: async () => {
      const response = await shiftService.getEmployeeRoster(employeeId, params);
      return response.data;
    },
    enabled: enabled && !!employeeId,
    placeholderData: keepPreviousData,
  });
};

/**
 * Upsert single roster entry (PUT /roster).
 */
export const useUpsertRosterEntry = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: import("../types").RosterUpsertRequest) => {
      const response = await shiftService.upsertRosterEntry(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
  });
};

/**
 * Bulk set roster entries (POST /roster/bulk).
 */
export const useBulkSetRoster = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: import("../types").RosterBulkRequest) => {
      const response = await shiftService.bulkSetRoster(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
  });
};

/**
 * Patch existing roster entry (PATCH /roster/{roster_id}).
 */
export const useUpdateRosterEntry = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      rosterId,
      data,
    }: {
      rosterId: number;
      data: import("../types").RosterUpdateRequest;
    }) => {
      const response = await shiftService.updateRosterEntry(rosterId, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
  });
};

/**
 * Hard delete roster entry (DELETE /roster/{roster_id}).
 */
export const useDeleteRosterEntry = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (rosterId: number) => {
      await shiftService.deleteRosterEntry(rosterId);
      return rosterId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: rosterKeys.all });
    },
  });
};

/**
 * Resolve effective shift for an employee on a date (GET /shifts/resolve).
 */
export const useResolveShift = (params: import("../types").ShiftResolveQuery, enabled = true) => {
  return useQuery({
    queryKey: rosterKeys.resolve(params),
    queryFn: async () => {
      const response = await shiftService.resolveShift(params);
      return response.data;
    },
    enabled: enabled && !!params.employee_id && !!params.date,
  });
};


