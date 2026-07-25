import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { activityLogsService } from "../services/activity-logs-service";
import { ActivityLogQueryParams } from "../types";
import { toast } from "sonner";
import { useBranchContext } from "@/context/branch-context";

export const ACTIVITY_LOGS_QUERY_KEY = ["activity-logs"];

export function useActivityLogs(params?: ActivityLogQueryParams) {
  const { selectedBranchId } = useBranchContext();
  const effectiveParams = {
    ...(params || {}),
    branch_id: params?.branch_id || selectedBranchId || undefined,
  };
  return useQuery({
    queryKey: [...ACTIVITY_LOGS_QUERY_KEY, effectiveParams],
    queryFn: async () => {
      const res = await activityLogsService.getLogs(effectiveParams);
      return res.data;
    },
  });
}

export function useActivityLogFilters() {
  return useQuery({
    queryKey: [...ACTIVITY_LOGS_QUERY_KEY, "filters"],
    queryFn: async () => {
      try {
        const res = await activityLogsService.getFilters();
        return res.data;
      } catch {
        return {
          modules: [
            "Approvals Requests",
            "User Management",
            "Payroll",
            "Employee Management",
            "Shift Management",
            "Holiday Management",
            "Settlements",
          ],
          sub_modules: [
            "Attendance Request",
            "Leave Request",
            "User List",
            "Rights Template",
            "Payroll Summary",
            "Employee Details",
          ],
          action_types: ["Create", "Update", "Delete", "Assign", "Finalize", "Approve", "Process"],
          action_sources: ["Web App", "Mobile App"],
        };
      }
    },
  });
}

export function useExportActivityLogs() {
  const queryClient = useQueryClient();
  const { selectedBranchId } = useBranchContext();

  return useMutation({
    mutationFn: ({ format, params }: { format: "excel" | "csv" | "print"; params?: ActivityLogQueryParams }) => {
      const effectiveParams = {
        ...(params || {}),
        branch_id: params?.branch_id || selectedBranchId || undefined,
      };
      return activityLogsService.exportLogs(format, effectiveParams);
    },
    onSuccess: (_, { format }) => {
      queryClient.invalidateQueries({ queryKey: ACTIVITY_LOGS_QUERY_KEY });
      if (format !== "print") {
        toast.success(`Activity logs exported as ${format.toUpperCase()}`);
      }
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to export activity logs");
    },
  });
}
