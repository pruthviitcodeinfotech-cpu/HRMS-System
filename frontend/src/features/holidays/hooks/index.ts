import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { holidayService } from "../services";
import {
  HolidayTemplateCreateRequest,
  HolidayTemplateListParams,
  HolidayTemplateUpdateRequest,
  HolidayItemCreateRequest,
  HolidayItemUpdateRequest,
  HolidayTemplateAssignRequest,
} from "../types";

// Query-key factory
export const holidayKeys = {
  all: ["holidays"] as const,
  templates: () => [...holidayKeys.all, "templates"] as const,
  templateList: (params: HolidayTemplateListParams) =>
    [...holidayKeys.templates(), "list", params] as const,
  templateDetail: (id: number) => [...holidayKeys.templates(), "detail", id] as const,
  items: (templateId: number) => [...holidayKeys.all, "items", templateId] as const,
  assignment: (employeeId: number) => [...holidayKeys.all, "assignment", employeeId] as const,
  calendar: (employeeId: number, params: Record<string, unknown> = {}) =>
    [...holidayKeys.all, "calendar", employeeId, params] as const,
};

/**
 * Paginated holiday templates list (GET /leave/holiday-templates).
 */
export const useHolidayTemplates = (params: HolidayTemplateListParams = {}) => {
  return useQuery({
    queryKey: holidayKeys.templateList(params),
    queryFn: async () => {
      const response = await holidayService.getHolidayTemplates(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/**
 * Single holiday template detail (GET /leave/holiday-templates/{template_id}).
 */
export const useHolidayTemplate = (templateId: number, enabled = true) => {
  return useQuery({
    queryKey: holidayKeys.templateDetail(templateId),
    queryFn: async () => {
      const response = await holidayService.getHolidayTemplate(templateId);
      return response.data;
    },
    enabled: enabled && Boolean(templateId),
  });
};

/**
 * Create holiday template (POST /leave/holiday-templates).
 */
export const useCreateHolidayTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: HolidayTemplateCreateRequest) => {
      const response = await holidayService.createHolidayTemplate(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
    },
  });
};

/**
 * Update holiday template name (PATCH /leave/holiday-templates/{template_id}).
 */
export const useUpdateHolidayTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      templateId,
      data,
    }: {
      templateId: number;
      data: HolidayTemplateUpdateRequest;
    }) => {
      const response = await holidayService.updateHolidayTemplate(templateId, data);
      return response.data;
    },
    onSuccess: (updatedTemplate) => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
      if (updatedTemplate?.id) {
        queryClient.invalidateQueries({ queryKey: holidayKeys.templateDetail(updatedTemplate.id) });
      }
    },
  });
};

/**
 * Soft-delete holiday template (DELETE /leave/holiday-templates/{template_id}).
 */
export const useDeleteHolidayTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (templateId: number) => {
      await holidayService.deleteHolidayTemplate(templateId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
    },
  });
};

/**
 * List holiday items in template (GET /leave/holiday-templates/{template_id}/holidays).
 */
export const useHolidayItems = (templateId: number, enabled = true) => {
  return useQuery({
    queryKey: holidayKeys.items(templateId),
    queryFn: async () => {
      const response = await holidayService.getHolidayItems(templateId);
      return response.data;
    },
    enabled: enabled && Boolean(templateId),
  });
};

/**
 * Create holiday item in template (POST /leave/holiday-templates/{template_id}/holidays).
 */
export const useCreateHolidayItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      templateId,
      data,
    }: {
      templateId: number;
      data: HolidayItemCreateRequest;
    }) => {
      const response = await holidayService.createHolidayItem(templateId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
      queryClient.invalidateQueries({ queryKey: holidayKeys.items(variables.templateId) });
    },
  });
};

/**
 * Update holiday item in template (PATCH /leave/holiday-templates/{template_id}/holidays/{item_id}).
 */
export const useUpdateHolidayItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      templateId,
      itemId,
      data,
    }: {
      templateId: number;
      itemId: number;
      data: HolidayItemUpdateRequest;
    }) => {
      const response = await holidayService.updateHolidayItem(templateId, itemId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
      queryClient.invalidateQueries({ queryKey: holidayKeys.items(variables.templateId) });
    },
  });
};

/**
 * Soft-delete holiday item (DELETE /leave/holiday-templates/{template_id}/holidays/{item_id}).
 */
export const useDeleteHolidayItem = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ templateId, itemId }: { templateId: number; itemId: number }) => {
      await holidayService.deleteHolidayItem(templateId, itemId);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
      queryClient.invalidateQueries({ queryKey: holidayKeys.items(variables.templateId) });
    },
  });
};

/**
 * Assign template to employee (PUT /leave/employees/{employee_id}/holiday-template).
 */
export const useAssignHolidayTemplate = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      employeeId,
      data,
    }: {
      employeeId: number;
      data: HolidayTemplateAssignRequest;
    }) => {
      const response = await holidayService.assignHolidayTemplate(employeeId, data);
      return response.data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: holidayKeys.all });
      queryClient.invalidateQueries({ queryKey: holidayKeys.assignment(variables.employeeId) });
    },
  });
};

/**
 * View employee template assignment (GET /leave/employees/{employee_id}/holiday-template).
 */
export const useEmployeeHolidayTemplate = (employeeId: number, enabled = true) => {
  return useQuery({
    queryKey: holidayKeys.assignment(employeeId),
    queryFn: async () => {
      const response = await holidayService.getEmployeeHolidayTemplate(employeeId);
      return response.data;
    },
    enabled: enabled && Boolean(employeeId),
  });
};

/**
 * List all employee holiday assignments (GET /leave/holiday-assignments).
 */
export const useHolidayAssignments = () => {
  return useQuery({
    queryKey: [...holidayKeys.all, "all-assignments"] as const,
    queryFn: async () => {
      const response = await holidayService.getHolidayAssignments();
      return response.data;
    },
  });
};

/**
 * Employee holiday calendar (GET /leave/employees/{employee_id}/holidays).
 */
export const useEmployeeHolidayCalendar = (
  employeeId: number,
  params: { year?: number; date_from?: string; date_to?: string } = {},
  enabled = true
) => {
  return useQuery({
    queryKey: holidayKeys.calendar(employeeId, params),
    queryFn: async () => {
      const response = await holidayService.getEmployeeHolidayCalendar(employeeId, params);
      return response.data;
    },
    enabled: enabled && Boolean(employeeId),
  });
};
