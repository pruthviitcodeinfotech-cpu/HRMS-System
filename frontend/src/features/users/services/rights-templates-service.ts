import { axiosClient } from "@/lib/axios-client";
import {
  RightsTemplate,
  RightsTemplateDetail,
  TemplatePermission,
  TemplatePermissionInput,
  CreateRightsTemplateInput,
  UpdateRightsTemplateInput,
  RightsTemplateLogsItem,
  PermissionCatalogItem,
} from "../types";

export interface RightsTemplatesQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  include_deleted?: boolean;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  request_id?: string;
}

export interface PaginatedData<T> {
  items: T[];
  page: number;
  page_size: number;
  total_records: number;
  total_pages: number;
}

export const rightsTemplatesService = {
  getPermissionCatalog: async () => {
    const response = await axiosClient.get<ApiResponse<PermissionCatalogItem[]>>(
      "/permissions"
    );
    return response.data;
  },

  getRightsTemplates: async (params?: RightsTemplatesQueryParams) => {
    const response = await axiosClient.get<ApiResponse<PaginatedData<RightsTemplate>>>(
      "/rights-templates",
      { params }
    );
    return response.data;
  },

  getRightsTemplateById: async (id: number) => {
    const response = await axiosClient.get<ApiResponse<RightsTemplateDetail>>(
      `/rights-templates/${id}`
    );
    return response.data;
  },

  createRightsTemplate: async (data: CreateRightsTemplateInput) => {
    const response = await axiosClient.post<ApiResponse<RightsTemplateDetail>>(
      "/rights-templates",
      data
    );
    return response.data;
  },

  updateRightsTemplate: async (id: number, data: UpdateRightsTemplateInput) => {
    const response = await axiosClient.put<ApiResponse<RightsTemplate>>(
      `/rights-templates/${id}`,
      data
    );
    return response.data;
  },

  deleteRightsTemplate: async (id: number) => {
    const response = await axiosClient.delete(`/rights-templates/${id}`);
    return response.data;
  },

  duplicateRightsTemplate: async (id: number, name: string) => {
    const response = await axiosClient.post<ApiResponse<RightsTemplateDetail>>(
      `/rights-templates/${id}/duplicate`,
      { name }
    );
    return response.data;
  },

  activateRightsTemplate: async (id: number) => {
    const response = await axiosClient.post<ApiResponse<RightsTemplate>>(
      `/rights-templates/${id}/activate`
    );
    return response.data;
  },

  deactivateRightsTemplate: async (id: number) => {
    const response = await axiosClient.post<ApiResponse<RightsTemplate>>(
      `/rights-templates/${id}/deactivate`
    );
    return response.data;
  },

  getTemplatePermissions: async (id: number) => {
    const response = await axiosClient.get<ApiResponse<TemplatePermission[]>>(
      `/rights-templates/${id}/permissions`
    );
    return response.data;
  },

  replaceTemplatePermissions: async (
    id: number,
    permissions: TemplatePermissionInput[]
  ) => {
    const response = await axiosClient.put<ApiResponse<TemplatePermission[]>>(
      `/rights-templates/${id}/permissions`,
      { permissions }
    );
    return response.data;
  },

  getRightsTemplatesLogs: async () => {
    const response = await axiosClient.get<ApiResponse<RightsTemplateLogsItem[]>>(
      "/rights-templates/logs"
    );
    return response.data;
  },
};
