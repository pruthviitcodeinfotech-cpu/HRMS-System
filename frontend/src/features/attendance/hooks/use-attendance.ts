import { keepPreviousData, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AxiosError } from "axios";
import {
  attendanceService,
  AttendanceDailyQueryParams,
  AttendanceDailySummaryParams,
  AttendanceMonthlySummaryParams,
  AttendancePunchesQueryParams,
  ManualPunchPayload,
  ManualAttendancePayload,
  AttendanceCorrectionPayload,
  AttendanceCorrectionApprovePayload,
  AttendanceLockPayload,
  AttendanceUnlockPayload,
  DailyPunchReportQueryParams,
} from "../services/attendance";

export const attendanceKeys = {
  all: ["attendance"] as const,
  days: () => [...attendanceKeys.all, "days"] as const,
  dayList: (params: AttendanceDailyQueryParams) => [...attendanceKeys.days(), params] as const,
  dailySummary: (params: AttendanceDailySummaryParams) =>
    [...attendanceKeys.all, "summary", "daily", params] as const,
  monthlySummary: (params: AttendanceMonthlySummaryParams) =>
    [...attendanceKeys.all, "summary", "monthly", params] as const,
  punches: () => [...attendanceKeys.all, "punches"] as const,
  punchList: (params: AttendancePunchesQueryParams) =>
    [...attendanceKeys.punches(), params] as const,
  locks: () => [...attendanceKeys.all, "locks"] as const,
  dailyPunchReport: (params: DailyPunchReportQueryParams) =>
    [...attendanceKeys.all, "dailyPunchReport", params] as const,
};

// Helper for extracting clean error message from Axios errors
const getErrorMessage = (error: unknown, fallback: string): string => {
  if (error instanceof AxiosError && error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return fallback;
};

/**
 * Fetch daily attendance records (GET /attendance/days)
 */
export const useAttendanceDays = (params: AttendanceDailyQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.dayList(params),
    queryFn: async () => {
      const response = await attendanceService.getAttendanceDays(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

/**
 * Fetch daily summary metrics (GET /attendance/summary/daily)
 */
export const useDailySummary = (params: AttendanceDailySummaryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.dailySummary(params),
    queryFn: async () => {
      const response = await attendanceService.getDailySummary(params);
      return response.data;
    },
    enabled: enabled && !!params.date,
  });
};

/**
 * Fetch monthly attendance summary (GET /attendance/summary/monthly)
 */
export const useMonthlySummary = (params: AttendanceMonthlySummaryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.monthlySummary(params),
    queryFn: async () => {
      const response = await attendanceService.getMonthlySummary(params);
      return response.data;
    },
    enabled: enabled && !!params.month && !!params.year,
  });
};

/**
 * Fetch raw attendance punches (GET /attendance/punches)
 */
export const useAttendancePunches = (params: AttendancePunchesQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.punchList(params),
    queryFn: async () => {
      const response = await attendanceService.getAttendancePunches(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled: enabled && !!params.from && !!params.to,
  });
};

/**
 * Add manual punch log (POST /attendance/punches)
 */
export const useAddManualPunch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ManualPunchPayload) => {
      const response = await attendanceService.addManualPunch(payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Manual punch log added successfully.");
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to add manual punch log."));
    },
  });
};

/**
 * Create manual check-in/out attendance (POST /attendance/manual)
 */
export const useCreateManualAttendance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ManualAttendancePayload) => {
      const response = await attendanceService.createManualAttendance(payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Manual attendance record created.");
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to create manual attendance."));
    },
  });
};

/**
 * Request attendance correction / regularization (POST /attendance/corrections)
 */
export const useRequestCorrection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AttendanceCorrectionPayload) => {
      const response = await attendanceService.requestCorrection(payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Attendance correction request submitted.");
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to submit correction request."));
    },
  });
};

/**
 * Approve or reject attendance correction (PUT /attendance/corrections/{id}/approve)
 */
export const useApproveCorrection = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      requestId,
      payload,
    }: {
      requestId: number;
      payload: AttendanceCorrectionApprovePayload;
    }) => {
      const response = await attendanceService.approveCorrection(requestId, payload);
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`Correction request status updated to ${data.status}.`);
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to process correction decision."));
    },
  });
};

/**
 * Freeze attendance period (POST /attendance/lock)
 */
export const useLockAttendance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AttendanceLockPayload) => {
      const response = await attendanceService.lockAttendance(payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Attendance period locked successfully.");
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to lock attendance period."));
    },
  });
};

/**
 * Unfreeze attendance period (POST /attendance/unlock)
 */
export const useUnlockAttendance = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AttendanceUnlockPayload) => {
      const response = await attendanceService.unlockAttendance(payload);
      return response.data;
    },
    onSuccess: () => {
      toast.success("Attendance period unlocked successfully.");
      queryClient.invalidateQueries({ queryKey: attendanceKeys.all });
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, "Failed to unlock attendance period."));
    },
  });
};

/**
 * Fetch all locked attendance periods (GET /attendance/locks)
 */
export const useAttendanceLocks = () => {
  return useQuery({
    queryKey: attendanceKeys.locks(),
    queryFn: async () => {
      const response = await attendanceService.getAttendanceLocks();
      return response.data;
    },
  });
};

/**
 * Fetch Daily Punch Matrix Report (GET /reports/attendance/daily-punch)
 */
export const useDailyPunchReport = (params: DailyPunchReportQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.dailyPunchReport(params),
    queryFn: async () => {
      const response = await attendanceService.getDailyPunchReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};
