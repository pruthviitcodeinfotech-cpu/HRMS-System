export interface ActivityLogItem {
  id: number;
  module: string;
  sub_module?: string | null;
  title: string;
  action_type: string;
  employee_id?: number | null;
  employee_name?: string | null;
  performed_by_user_id?: number | null;
  performed_by_name: string;
  log_date: string;
  log_time: string;
  logged_at: string;
  action_from: string;
  description?: string | null;
  payroll_date?: string | null;
}

export interface ActivityLogPagination {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  total?: number;
  has_next?: boolean;
  has_previous?: boolean;
}

export interface ActivityLogListResponseData {
  items: ActivityLogItem[];
  pagination: ActivityLogPagination;
}

export interface ActivityLogQueryParams {
  page?: number;
  page_size?: number;
  module?: string;
  sub_module?: string;
  action_type?: string;
  action_from?: string;
  employee_id?: number;
  performed_by_user_id?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface ActivityLogFilterOptions {
  modules: string[];
  sub_modules: string[];
  action_types: string[];
  action_sources: string[];
}
