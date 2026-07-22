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
  WorkingHoursReportQueryParams,
  MusterReportQueryParams,
  BranchWisePunchReportQueryParams,
  LeaveTakenReportQueryParams,
  LeaveTakenReportData,
  LeaveTakenReportRow,
  EmployeeDayWiseMasterReportQueryParams,
} from "../services/attendance";

import { leaveService } from "@/features/leaves/services";

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
  workingHoursReport: (params: WorkingHoursReportQueryParams) =>
    [...attendanceKeys.all, "workingHoursReport", params] as const,
  musterReport: (params: MusterReportQueryParams) =>
    [...attendanceKeys.all, "musterReport", params] as const,
  branchWisePunchReport: (params: BranchWisePunchReportQueryParams) =>
    [...attendanceKeys.all, "branchWisePunchReport", params] as const,
  leaveTakenReport: (params: LeaveTakenReportQueryParams) =>
    [...attendanceKeys.all, "leaveTakenReport", params] as const,
  employeeDayWiseMasterReport: (params: EmployeeDayWiseMasterReportQueryParams) =>
    [...attendanceKeys.all, "employeeDayWiseMasterReport", params] as const,
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

/**
 * Fetch Working Hours Matrix Report (GET /reports/attendance/working-hours)
 */
export const useWorkingHoursReport = (params: WorkingHoursReportQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.workingHoursReport(params),
    queryFn: async () => {
      const response = await attendanceService.getWorkingHoursReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

/**
 * Fetch Muster Roll Report (GET /reports/attendance/muster)
 */
export const useMusterReport = (params: MusterReportQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.musterReport(params),
    queryFn: async () => {
      const response = await attendanceService.getMusterReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

/**
 * Fetch Branch Wise Punch Report (GET /reports/attendance/branch-wise-punch)
 */
export const useBranchWisePunchReport = (params: BranchWisePunchReportQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.branchWisePunchReport(params),
    queryFn: async () => {
      const response = await attendanceService.getBranchWisePunchReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

export const USE_MOCK_DATA = true; // Toggle mock data for QA/testing (true/false)

/**
 * Generate realistic mock data for QA/testing of Leave Taken Report based on active leave types
 */
const generateMockLeaveTakenData = (params: LeaveTakenReportQueryParams, leaveTypes: string[]): LeaveTakenReportData => {
  const firstNames = [
    "Hetal", "Divyesh", "Pratik", "Kunal", "Sneha", "Vipul", "Mili", "Harsh", "Sneya", "Khushi",
    "Jignesh", "Ravi", "Amit", "Priya", "Neha", "Rahul", "Sanjay", "Deepak", "Anjali", "Rohan",
    "Karan", "Pooja", "Aarav", "Ishaan", "Vihaan", "Aditya", "Sai", "Arjun", "Kabir", "Reyansh",
    "Aanya", "Diya", "Saanvi", "Ananya", "Prisha", "Meera", "Zara", "Amina", "Fatima", "Mariam",
    "John", "David", "Michael", "Sarah", "Emily", "Jessica", "James", "Robert", "William", "Linda"
  ];
  const lastNames = [
    "Gohil", "Pipaliya", "Raval", "Kikani", "Nadapara", "Rawal", "Chovatiya", "Kumbhani", "Patel", "Bhut",
    "Shah", "Mehta", "Sharma", "Verma", "Gupta", "Singh", "Joshi", "Trivedi", "Mishra", "Patil",
    "Deshmukh", "Kulkarni", "Reddy", "Nair", "Iyer", "Rao", "Menon", "Pillai", "Choudhury", "Bose",
    "Sen", "Roy", "Das", "Mukherjee", "Banerjee", "Chatterjee", "Dutta", "Mitra", "Ghosh", "Som",
    "Smith", "Jones", "Miller", "Davis", "Garcia", "Rodriguez", "Wilson", "Martinez", "Anderson", "Taylor"
  ];
  const departments = ["Development", "Sales", "Marketing", "HR", "Support", "Finance"];
  const designations = ["Senior Engineer", "Sales Executive", "Marketing Manager", "HR Specialist", "Support Agent", "Financial Analyst"];

  const rawItems: LeaveTakenReportRow[] = [];

  for (let i = 1; i <= 60; i++) {
    const firstName = firstNames[(i - 1) % firstNames.length];
    const lastName = lastNames[(i - 1) % lastNames.length];
    const empCode = `EMP${String(100 + i)}`;
    
    // Assign department and branch deterministically
    const deptIdx = (i - 1) % departments.length;
    const deptName = departments[deptIdx];
    const desName = designations[(i - 1) % designations.length];
    
    // Simulate branch_id and department_id
    const branchId = ((i - 1) % 3) + 1; // 1, 2, or 3
    const departmentId = deptIdx + 1;

    const leaves: Record<string, number> = {};
    let total = 0;

    // Every 5th employee has zero leaves
    const hasLeaves = i % 5 !== 0;

    // Initialize all active leave types to 0
    leaveTypes.forEach(lt => {
      leaves[lt] = 0;
    });

    if (hasLeaves) {
      leaveTypes.forEach(lt => {
        const code = lt.toUpperCase();
        if (code === "CL") {
          leaves[lt] = i % 3 === 0 ? 1.5 : i % 2 === 0 ? 0.5 : 0;
        } else if (code === "SL") {
          leaves[lt] = i % 4 === 0 ? 2.0 : i % 3 === 0 ? 1.0 : 0;
        } else if (code === "EL") {
          leaves[lt] = i % 6 === 0 ? 5.0 : i % 4 === 0 ? 2.5 : 0;
        } else if (code === "COMP OFF" || code === "COMP_OFF") {
          leaves[lt] = i % 8 === 0 ? 3.0 : i % 5 === 0 ? 1.0 : 0;
        } else if (code === "LWP") {
          leaves[lt] = i % 7 === 0 ? 4.5 : i % 6 === 0 ? 0.5 : 0;
        } else if (code === "MATERNITY") {
          leaves[lt] = i === 12 || i === 42 ? 90.0 : 0;
        } else if (code === "PATERNITY") {
          leaves[lt] = i === 15 || i === 45 ? 15.0 : 0;
        } else {
          // Dynamic fallback for custom user created leave types
          leaves[lt] = (i % (leaveTypes.indexOf(lt) + 2) === 0) ? 1.0 : 0;
        }
      });
      total = Object.values(leaves).reduce((sum, val) => sum + val, 0);
    }

    rawItems.push({
      employee_id: i,
      employee_code: empCode,
      employee_name: `${firstName} ${lastName}`,
      department_name: deptName,
      designation_name: desName,
      leaves,
      total_leaves: total,
      // Temporarily store ids for mock filtering
      ...({ branch_id: branchId, department_id: departmentId } as any)
    });
  }

  // Filter items
  let filtered = [...rawItems];
  if (params.branch_id) {
    filtered = filtered.filter(item => (item as any).branch_id === params.branch_id);
  }
  if (params.department_id) {
    filtered = filtered.filter(item => (item as any).department_id === params.department_id);
  }

  // Sort items
  const sortField = params.sort_by || "employee_code";
  const sortDir = params.sort_dir || "asc";
  filtered.sort((a, b) => {
    let valA: any = "";
    let valB: any = "";

    if (sortField === "employee_code") {
      valA = a.employee_code;
      valB = b.employee_code;
    } else if (sortField === "employee_name") {
      valA = a.employee_name.toLowerCase();
      valB = b.employee_name.toLowerCase();
    } else if (sortField === "department_name") {
      valA = a.department_name.toLowerCase();
      valB = b.department_name.toLowerCase();
    } else if (sortField === "designation_name") {
      valA = a.designation_name.toLowerCase();
      valB = b.designation_name.toLowerCase();
    } else if (sortField === "total_leaves") {
      valA = a.total_leaves;
      valB = b.total_leaves;
    } else {
      valA = a.leaves[sortField] || 0;
      valB = b.leaves[sortField] || 0;
    }

    if (valA < valB) return sortDir === "asc" ? -1 : 1;
    if (valA > valB) return sortDir === "asc" ? 1 : -1;
    return 0;
  });

  // Paginate items
  const page = params.page || 1;
  const pageSize = params.page_size || 10;
  const startIndex = (page - 1) * pageSize;
  const paginatedItems = filtered.slice(startIndex, startIndex + pageSize);

  // Clean rawItems branch_id / department_id to prevent any leakage
  const cleanedItems = paginatedItems.map(item => {
    const { branch_id, department_id, ...rest } = item as any;
    return rest;
  });

  return {
    leave_types: leaveTypes,
    items: cleanedItems,
    pagination: {
      page,
      page_size: pageSize,
      total_records: filtered.length,
      total_pages: Math.ceil(filtered.length / pageSize) || 1,
    }
  };
};

/**
 * Fetch Leave Taken Report (GET /reports/leave/taken)
 */
export const useLeaveTakenReport = (params: LeaveTakenReportQueryParams, enabled = true) => {
  return useQuery({
    queryKey: attendanceKeys.leaveTakenReport(params),
    queryFn: async () => {
      if (USE_MOCK_DATA) {
        // Fetch active leave types from database (only those created under Leave Create)
        let activeLeaveTypes: string[] = [];
        try {
          const leaveTypesResponse = await leaveService.getLeaveTypes({ page_size: 100 });
          activeLeaveTypes = (leaveTypesResponse?.data?.items || [])
            .filter((lt) => lt.is_active)
            .map((lt) => lt.alias.toUpperCase());
        } catch (err) {
          console.error("Failed to fetch active leave types for mock data", err);
        }
        if (activeLeaveTypes.length === 0) {
          activeLeaveTypes = ["CL", "SL", "EL"];
        }

        // Return realistic mock data simulation with brief delay to mimic network latency
        await new Promise((resolve) => setTimeout(resolve, 200));
        return generateMockLeaveTakenData(params, activeLeaveTypes);
      }
      const response = await attendanceService.getLeaveTakenReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};

/**
 * Fetch Employee Day Wise Master Report (GET /reports/attendance/employee-day-wise-master)
 */
export const useEmployeeDayWiseMasterReport = (
  params: EmployeeDayWiseMasterReportQueryParams,
  enabled = true
) => {
  return useQuery({
    queryKey: attendanceKeys.employeeDayWiseMasterReport(params),
    queryFn: async () => {
      const response = await attendanceService.getEmployeeDayWiseMasterReport(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
    enabled,
  });
};


