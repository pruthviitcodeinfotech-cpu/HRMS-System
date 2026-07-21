import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  HolidayTemplateCreateRequest,
  HolidayTemplateListParams,
  HolidayTemplateListResponse,
  HolidayTemplateSchema,
  HolidayTemplateUpdateRequest,
  HolidayItemCreateRequest,
  HolidayItemSchema,
  HolidayItemUpdateRequest,
  HolidayTemplateAssignRequest,
  EmployeeHolidayAssignmentSchema,
  EmployeeHolidayCalendarSchema,
} from "../types";

const buildHolidayTemplateQuery = (params: HolidayTemplateListParams): string => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", String(params.page));
  if (params.page_size) query.append("page_size", String(params.page_size));
  return query.toString();
};

export const holidayService = {
  /** GET /holiday-templates — List & paginate holiday templates */
  getHolidayTemplates: async (
    params: HolidayTemplateListParams = {}
  ): Promise<ApiResponse<HolidayTemplateListResponse>> => {
    const queryString = buildHolidayTemplateQuery(params);
    const url = queryString ? `/holiday-templates?${queryString}` : "/holiday-templates";
    return apiClient.get<ApiResponse<HolidayTemplateListResponse>>(url);
  },

  /** GET /holiday-templates/{template_id} — Retrieve details of a template with items */
  getHolidayTemplate: async (templateId: number): Promise<ApiResponse<HolidayTemplateSchema>> => {
    return apiClient.get<ApiResponse<HolidayTemplateSchema>>(`/holiday-templates/${templateId}`);
  },

  /** POST /holiday-templates — Create a new holiday template */
  createHolidayTemplate: async (
    data: HolidayTemplateCreateRequest
  ): Promise<ApiResponse<HolidayTemplateSchema>> => {
    return apiClient.post<ApiResponse<HolidayTemplateSchema>>("/holiday-templates", data);
  },

  /** PATCH /holiday-templates/{template_id} — Update holiday template name */
  updateHolidayTemplate: async (
    templateId: number,
    data: HolidayTemplateUpdateRequest
  ): Promise<ApiResponse<HolidayTemplateSchema>> => {
    return apiClient.patch<ApiResponse<HolidayTemplateSchema>>(
      `/holiday-templates/${templateId}`,
      data
    );
  },

  /** DELETE /holiday-templates/{template_id} — Soft-delete a holiday template */
  deleteHolidayTemplate: async (templateId: number): Promise<void> => {
    await apiClient.delete<void>(`/holiday-templates/${templateId}`);
  },

  /** GET /holiday-templates/{template_id}/holidays — List non-deleted holiday items */
  getHolidayItems: async (templateId: number): Promise<ApiResponse<HolidayItemSchema[]>> => {
    return apiClient.get<ApiResponse<HolidayItemSchema[]>>(
      `/holiday-templates/${templateId}/holidays`
    );
  },

  /** POST /holiday-templates/{template_id}/holidays — Add a holiday item to template */
  createHolidayItem: async (
    templateId: number,
    data: HolidayItemCreateRequest
  ): Promise<ApiResponse<HolidayItemSchema>> => {
    return apiClient.post<ApiResponse<HolidayItemSchema>>(
      `/holiday-templates/${templateId}/holidays`,
      data
    );
  },

  /** PATCH /holiday-templates/{template_id}/holidays/{item_id} — Update holiday item */
  updateHolidayItem: async (
    templateId: number,
    itemId: number,
    data: HolidayItemUpdateRequest
  ): Promise<ApiResponse<HolidayItemSchema>> => {
    return apiClient.patch<ApiResponse<HolidayItemSchema>>(
      `/holiday-templates/${templateId}/holidays/${itemId}`,
      data
    );
  },

  /** DELETE /holiday-templates/{template_id}/holidays/{item_id} — Soft-delete holiday item */
  deleteHolidayItem: async (templateId: number, itemId: number): Promise<void> => {
    await apiClient.delete<void>(`/holiday-templates/${templateId}/holidays/${itemId}`);
  },

  /** PUT /employees/{employee_id}/holiday-template — Assign template to employee */
  assignHolidayTemplate: async (
    employeeId: number,
    data: HolidayTemplateAssignRequest
  ): Promise<ApiResponse<EmployeeHolidayAssignmentSchema>> => {
    return apiClient.put<ApiResponse<EmployeeHolidayAssignmentSchema>>(
      `/employees/${employeeId}/holiday-template`,
      data
    );
  },

  /** GET /employees/{employee_id}/holiday-template — View current assignment */
  getEmployeeHolidayTemplate: async (
    employeeId: number
  ): Promise<ApiResponse<EmployeeHolidayAssignmentSchema>> => {
    return apiClient.get<ApiResponse<EmployeeHolidayAssignmentSchema>>(
      `/employees/${employeeId}/holiday-template`
    );
  },

  /** GET /holiday-assignments — List all employee holiday assignments */
  getHolidayAssignments: async (): Promise<ApiResponse<EmployeeHolidayAssignmentSchema[]>> => {
    return apiClient.get<ApiResponse<EmployeeHolidayAssignmentSchema[]>>("/holiday-assignments");
  },

  /** GET /employees/{employee_id}/holidays — Get employee holiday calendar */
  getEmployeeHolidayCalendar: async (
    employeeId: number,
    params: { year?: number; date_from?: string; date_to?: string } = {}
  ): Promise<ApiResponse<EmployeeHolidayCalendarSchema[]>> => {
    const query = new URLSearchParams();
    if (params.year) query.append("year", String(params.year));
    if (params.date_from) query.append("date_from", params.date_from);
    if (params.date_to) query.append("date_to", params.date_to);
    const queryString = query.toString();
    const url = queryString
      ? `/employees/${employeeId}/holidays?${queryString}`
      : `/employees/${employeeId}/holidays`;
    return apiClient.get<ApiResponse<EmployeeHolidayCalendarSchema[]>>(url);
  },
};
