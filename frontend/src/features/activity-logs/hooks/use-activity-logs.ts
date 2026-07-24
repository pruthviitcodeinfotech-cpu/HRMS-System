import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { activityLogsService } from "../services/activity-logs-service";
import { ActivityLogQueryParams } from "../types";
import { toast } from "sonner";

export const ACTIVITY_LOGS_QUERY_KEY = ["activity-logs"];

export function useActivityLogs(params?: ActivityLogQueryParams) {
  return useQuery({
    queryKey: [...ACTIVITY_LOGS_QUERY_KEY, params],
    queryFn: async () => {
      const res = await activityLogsService.getLogs(params);
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

  return useMutation({
    mutationFn: ({ format, params }: { format: "excel" | "csv" | "print"; params?: ActivityLogQueryParams }) =>
      activityLogsService.exportLogs(format, params),
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
