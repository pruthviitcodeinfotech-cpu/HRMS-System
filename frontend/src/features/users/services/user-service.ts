import { axiosClient } from "@/lib/axios-client";
import { ApiResponse, PaginatedData } from "./rights-templates-service";

export interface UserSummary {
  id: number;
  name: string;
  email: string;
  mobile_country_code: string;
  mobile_number: string;
  is_active: boolean;
  is_super_admin: boolean;
  employee_id?: number | null;
  last_login_at?: string | null;
  created_at: string;
  template?: {
    id: number;
    name: string;
  } | null;
}

export interface UserDetail extends UserSummary {
  org_id: number;
  updated_at: string;
  is_deleted?: boolean;
  data_scope?: {
    branch_ids: number[];
    department_ids: number[];
  };
}

export interface UserQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  is_active?: boolean;
  is_super_admin?: boolean;
  has_employee?: boolean;
  include_deleted?: boolean;
}

export interface CreateUserInput {
  name: string;
  email: string;
  mobile_country_code?: string;
  mobile_number: string;
  employee_id?: number | null;
  is_super_admin?: boolean;
  password?: string;
}

export interface UpdateUserInput {
  name?: string;
  email?: string;
  mobile_country_code?: string;
  mobile_number?: string;
  is_super_admin?: boolean;
}

export const userService = {
  getUsers: async (params?: UserQueryParams) => {
    const response = await axiosClient.get<ApiResponse<PaginatedData<UserSummary>>>(
      "/users",
      { params }
    );
    return response.data;
  },

  getUserById: async (id: number) => {
    const response = await axiosClient.get<ApiResponse<UserDetail>>(`/users/${id}`);
    return response.data;
  },

  createUser: async (data: CreateUserInput) => {
    const response = await axiosClient.post<ApiResponse<UserSummary>>("/users", data);
    return response.data;
  },

  updateUser: async (id: number, data: UpdateUserInput) => {
    const response = await axiosClient.patch<ApiResponse<UserSummary>>(
      `/users/${id}`,
      data
    );
    return response.data;
  },

  activateUser: async (id: number) => {
    const response = await axiosClient.post<ApiResponse<UserSummary>>(
      `/users/${id}/activate`
    );
    return response.data;
  },

  deactivateUser: async (id: number) => {
    const response = await axiosClient.post<ApiResponse<UserSummary>>(
      `/users/${id}/deactivate`
    );
    return response.data;
  },

  deleteUser: async (id: number) => {
    const response = await axiosClient.delete(`/users/${id}`);
    return response.data;
  },

  getUserRole: async (userId: number) => {
    const response = await axiosClient.get<ApiResponse<{ template: { id: number; name: string } | null }>>(
      `/users/${userId}/template`
    );
    return response.data;
  },

  assignUserRole: async (userId: number, templateId: number) => {
    const response = await axiosClient.put<ApiResponse<{ template: { id: number; name: string } | null }>>(
      `/users/${userId}/template`,
      { template_id: templateId }
    );
    return response.data;
  },

  removeUserRole: async (userId: number) => {
    const response = await axiosClient.delete(`/users/${userId}/template`);
    return response.data;
  },

  bulkAssignRole: async (userIds: number[], templateId: number) => {
    const response = await axiosClient.post<ApiResponse<{ assigned_count: number }>>(
      "/users/bulk-template",
      { user_ids: userIds, template_id: templateId }
    );
    return response.data;
  },
};
