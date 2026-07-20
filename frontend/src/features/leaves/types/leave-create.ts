export type AllocationFrequency = "monthly" | "yearly";
export type CarryForwardFrequency = "monthly" | "yearly";
export type EncashmentFrequency = "monthly" | "yearly";
export type LeaveCycle = "calendar_year" | "financial_year";

/** Backend LeaveType schema. */
export interface LeaveTypeSchema {
  id: number;
  org_id: number;
  name: string;
  alias: string;
  description: string | null;
  auto_allocation_count: number;
  allocation_frequency: AllocationFrequency;
  carry_forward_count: number;
  carry_forward_frequency: CarryForwardFrequency;
  encashment_enabled: boolean;
  encashment_limit: number | null;
  encashment_frequency: EncashmentFrequency | null;
  is_active: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface LeaveTypeListResponse {
  items: LeaveTypeSchema[];
  pagination: PaginationMeta;
}

export interface LeaveTypeListParams {
  page?: number;
  page_size?: number;
  search?: string;
  is_active?: boolean;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

export interface LeaveTypeCreateRequest {
  name: string;
  alias: string;
  description?: string | null;
  auto_allocation_count: number;
  allocation_frequency?: AllocationFrequency;
  carry_forward_count?: number;
  carry_forward_frequency?: CarryForwardFrequency;
  encashment_enabled?: boolean;
  encashment_limit?: number | null;
  encashment_frequency?: EncashmentFrequency | null;
  is_active?: boolean;
}

export interface LeaveTypeUpdateRequest {
  name?: string | null;
  alias?: string | null;
  description?: string | null;
  auto_allocation_count?: number | null;
  allocation_frequency?: AllocationFrequency | null;
  carry_forward_count?: number | null;
  carry_forward_frequency?: CarryForwardFrequency | null;
  encashment_enabled?: boolean | null;
  encashment_limit?: number | null;
  encashment_frequency?: EncashmentFrequency | null;
  is_active?: boolean | null;
}

export interface LeaveSettingsSchema {
  id: number;
  org_id: number;
  leave_cycle: LeaveCycle;
  cycle_start_month: number;
  created_at: string;
  updated_at: string;
  created_by: number | null;
  updated_by: number | null;
}

export interface LeaveSettingsUpdateRequest {
  leave_cycle: LeaveCycle;
  cycle_start_month: number;
}
