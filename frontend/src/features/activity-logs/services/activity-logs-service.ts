import { apiClient } from "@/services/api-client/client";
import {
  ActivityLogQueryParams,
  ActivityLogListResponseData,
  ActivityLogFilterOptions,
} from "../types";

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export const activityLogsService = {
  getLogs: async (params?: ActivityLogQueryParams): Promise<ApiResponse<ActivityLogListResponseData>> => {
    const query = new URLSearchParams();
    if (params?.page) query.append("page", params.page.toString());
    if (params?.page_size) query.append("page_size", params.page_size.toString());
    if (params?.module) query.append("module", params.module);
    if (params?.sub_module) query.append("sub_module", params.sub_module);
    if (params?.action_type) query.append("action_type", params.action_type);
    if (params?.action_from) query.append("action_from", params.action_from);
    if (params?.employee_id) query.append("employee_id", params.employee_id.toString());
    if (params?.performed_by_user_id) query.append("performed_by_user_id", params.performed_by_user_id.toString());
    if (params?.date_from) query.append("date_from", params.date_from);
    if (params?.date_to) query.append("date_to", params.date_to);
    if (params?.search) query.append("search", params.search);
    if (params?.sort_by) query.append("sort_by", params.sort_by);
    if (params?.sort_order) query.append("sort_order", params.sort_order);

    const queryString = query.toString();
    const url = `/activity-logs${queryString ? `?${queryString}` : ""}`;
    return apiClient.get<ApiResponse<ActivityLogListResponseData>>(url);
  },

  getFilters: async (): Promise<ApiResponse<ActivityLogFilterOptions>> => {
    return apiClient.get<ApiResponse<ActivityLogFilterOptions>>("/activity-logs/filters");
  },

  exportLogs: async (format: "excel" | "csv" | "print", params?: ActivityLogQueryParams): Promise<void> => {
    if (format === "print") {
      window.print();
      return;
    }

    // Fetch logs for export matching current query parameters
    const response = await activityLogsService.getLogs({
      ...params,
      page: 1,
      page_size: 100,
    });

    const items = response?.data?.items || [];

    const headers = [
      "Module",
      "Sub Module",
      "Employee Name",
      "Title",
      "Description",
      "Payroll Date",
      "Action",
      "Action By",
      "Log Date",
      "Log Time",
      "Action From",
    ];

    const escapeCsv = (val: string | number | null | undefined) => {
      const str = String(val ?? "");
      return `"${str.replace(/"/g, '""')}"`;
    };

    const rows = items.map((item) => [
      escapeCsv(item.module),
      escapeCsv(item.sub_module || "-"),
      escapeCsv(item.employee_name || "-"),
      escapeCsv(item.title),
      escapeCsv(item.description || "-"),
      escapeCsv(item.payroll_date || "-"),
      escapeCsv(item.action_type),
      escapeCsv(item.performed_by_name),
      escapeCsv(item.log_date),
      escapeCsv(item.log_time),
      escapeCsv(item.action_from),
    ]);

    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\r\n");

    const bom = format === "excel" ? "\uFEFF" : "";
    const blob = new Blob([bom + csvContent], {
      type: format === "excel" ? "application/vnd.ms-excel;charset=utf-8;" : "text/csv;charset=utf-8;",
    });

    const dateStr = new Date().toISOString().split("T")[0];
    const extension = format === "excel" ? "csv" : "csv";
    const filename = `Activity_Logs_${dateStr}.${extension}`;

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },
};
