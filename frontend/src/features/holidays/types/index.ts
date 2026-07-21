import { z } from "zod";

// ===========================================================================
// 1. Backend Pydantic Schema Interfaces
// ===========================================================================

export interface HolidayItemSchema {
  id: number;
  template_id: number;
  name: string;
  start_date: string;
  end_date: string;
  day_of_week?: string | null;
  duration_days: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by?: number | null;
}

export interface HolidayTemplateSchema {
  id: number;
  org_id: number;
  name: string;
  holiday_count: number;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  created_by?: number | null;
  updated_by?: number | null;
  items?: HolidayItemSchema[] | null;
}

export interface HolidayTemplateListParams {
  page?: number;
  page_size?: number;
}

export interface HolidayTemplateListResponse {
  items: HolidayTemplateSchema[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
    total_pages: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

export interface HolidayTemplateCreateRequest {
  name: string;
  items: HolidayItemCreateRequest[];
}

export interface HolidayTemplateUpdateRequest {
  name: string;
}

export interface HolidayItemCreateRequest {
  name: string;
  start_date: string;
  end_date: string;
  day_of_week?: string | null;
  duration_days?: number;
}

export interface HolidayItemUpdateRequest {
  name?: string;
  start_date?: string;
  end_date?: string;
  day_of_week?: string | null;
  duration_days?: number;
}

export interface EmployeeHolidayAssignmentSchema {
  id: number;
  employee_id: number;
  template_id?: number | null;
  assigned_at: string;
  assigned_by: number;
  previous_template_id?: number | null;
  template?: HolidayTemplateSchema | null;
}

export interface HolidayTemplateAssignRequest {
  template_id: number;
}

export interface EmployeeHolidayCalendarSchema {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  day_of_week?: string | null;
  duration_days: number;
}

// ===========================================================================
// 2. Legacy UI Component Helper Interfaces
// ===========================================================================

export interface HolidayItem {
  id?: string;
  name: string;
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  durationDays?: number;
  dayOfWeek?: string;
}

export interface HolidayTemplate {
  id: string;
  name: string;
  holidayCount: number;
  assignedEmployeesCount: number;
  createdOn: string;
  createdBy: string;
  lastModified: string;
  lastModifiedBy: string;
  items: HolidayItem[];
}

export interface HolidayAssignEmployee {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  designation: string;
  assignedTemplate?: string;
}

// ===========================================================================
// 3. Zod Form Validation Schemas
// ===========================================================================

export const holidayItemSchema = z.object({
  name: z.string().min(1, "Holiday name is required"),
  startDate: z.string().min(1, "Start date is required"),
  endDate: z.string().min(1, "End date is required"),
});

export const holidayTemplateSchema = z.object({
  name: z.string().min(1, "Template name is required"),
  items: z.array(holidayItemSchema).min(1, "At least one holiday item is required"),
});

export type HolidayTemplateFormValues = z.infer<typeof holidayTemplateSchema>;
