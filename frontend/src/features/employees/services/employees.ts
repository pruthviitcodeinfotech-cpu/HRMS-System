import { apiClient } from "@/services/api-client/client";
import { ApiResponse } from "@/features/auth/services";
import {
  BranchOption,
  DepartmentOption,
  DesignationOption,
  EmployeeListParams,
  EmployeeListResponse,
  LookupListResponse,
  DepartmentListParams,
  DepartmentListResponse,
  DepartmentSchema,
  DesignationListParams,
  DesignationListResponse,
  DesignationSchema,
  BranchListParams,
  BranchListResponse,
  BranchSchema,
  BranchCreatePayload,
  BranchUpdatePayload,
} from "../types";

const buildListQuery = (params: EmployeeListParams): string => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", String(params.page));
  if (params.page_size) query.append("page_size", String(params.page_size));
  if (params.q) query.append("q", params.q);
  if (params.branch_id) query.append("branch_id", String(params.branch_id));
  if (params.department_id) query.append("department_id", String(params.department_id));
  if (params.designation_id) query.append("designation_id", String(params.designation_id));
  if (params.status) query.append("status", params.status);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return query.toString();
};

export const employeeService = {
  getEmployees: async (
    params: EmployeeListParams = {}
  ): Promise<ApiResponse<EmployeeListResponse>> => {
    const queryString = buildListQuery(params);
    const url = queryString ? `/employees?${queryString}` : "/employees";
    return apiClient.get<ApiResponse<EmployeeListResponse>>(url);
  },

  // Filter dropdown sources (organization module). Active entries only, sorted
  // by name; page_size=200 matches the backend's maximum for these endpoints.
  getBranchOptions: async (): Promise<ApiResponse<LookupListResponse<BranchOption>>> => {
    return apiClient.get<ApiResponse<LookupListResponse<BranchOption>>>(
      "/branches?page_size=200&is_active=true&sort_by=branch_name&sort_order=asc"
    );
  },

  getDepartmentOptions: async (): Promise<ApiResponse<LookupListResponse<DepartmentOption>>> => {
    return apiClient.get<ApiResponse<LookupListResponse<DepartmentOption>>>(
      "/departments?page_size=200&is_active=true&sort_by=dept_name&sort_order=asc"
    );
  },

  getDesignationOptions: async (): Promise<ApiResponse<LookupListResponse<DesignationOption>>> => {
    return apiClient.get<ApiResponse<LookupListResponse<DesignationOption>>>(
      "/designations?page_size=200&is_active=true&sort_by=designation_name&sort_order=asc"
    );
  },

  getDepartments: async (
    params: DepartmentListParams = {}
  ): Promise<ApiResponse<DepartmentListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.search) query.append("search", params.search);
    if (params.is_active !== undefined) query.append("is_active", String(params.is_active));
    if (params.include_deleted !== undefined) query.append("include_deleted", String(params.include_deleted));
    if (params.sort_by) query.append("sort_by", params.sort_by);
    if (params.sort_order) query.append("sort_order", params.sort_order);

    const queryString = query.toString();
    const url = queryString ? `/departments?${queryString}` : "/departments";
    return apiClient.get<ApiResponse<DepartmentListResponse>>(url);
  },

  createDepartment: async (data: { dept_name: string }): Promise<ApiResponse<DepartmentSchema>> => {
    return apiClient.post<ApiResponse<DepartmentSchema>>("/departments", data);
  },

  updateDepartment: async (
    deptId: number,
    data: { dept_name: string }
  ): Promise<ApiResponse<DepartmentSchema>> => {
    return apiClient.patch<ApiResponse<DepartmentSchema>>(`/departments/${deptId}`, data);
  },

  activateDepartment: async (deptId: number): Promise<ApiResponse<DepartmentSchema>> => {
    return apiClient.post<ApiResponse<DepartmentSchema>>(`/departments/${deptId}/activate`, {});
  },

  deactivateDepartment: async (deptId: number): Promise<ApiResponse<DepartmentSchema>> => {
    return apiClient.post<ApiResponse<DepartmentSchema>>(`/departments/${deptId}/deactivate`, {});
  },

  deleteDepartment: async (deptId: number): Promise<ApiResponse<DepartmentSchema>> => {
    return apiClient.delete<ApiResponse<DepartmentSchema>>(`/departments/${deptId}`);
  },

  getDesignations: async (
    params: DesignationListParams = {}
  ): Promise<ApiResponse<DesignationListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.search) query.append("search", params.search);
    if (params.is_active !== undefined) query.append("is_active", String(params.is_active));
    if (params.include_deleted !== undefined)
      query.append("include_deleted", String(params.include_deleted));
    if (params.sort_by) query.append("sort_by", params.sort_by);
    if (params.sort_order) query.append("sort_order", params.sort_order);

    const queryString = query.toString();
    const url = queryString ? `/designations?${queryString}` : "/designations";
    return apiClient.get<ApiResponse<DesignationListResponse>>(url);
  },

  createDesignation: async (data: {
    designation_name: string;
  }): Promise<ApiResponse<DesignationSchema>> => {
    return apiClient.post<ApiResponse<DesignationSchema>>("/designations", data);
  },

  updateDesignation: async (
    designationId: number,
    data: { designation_name: string }
  ): Promise<ApiResponse<DesignationSchema>> => {
    return apiClient.patch<ApiResponse<DesignationSchema>>(
      `/designations/${designationId}`,
      data
    );
  },

  activateDesignation: async (designationId: number): Promise<ApiResponse<DesignationSchema>> => {
    return apiClient.post<ApiResponse<DesignationSchema>>(
      `/designations/${designationId}/activate`,
      {}
    );
  },

  deactivateDesignation: async (
    designationId: number
  ): Promise<ApiResponse<DesignationSchema>> => {
    return apiClient.post<ApiResponse<DesignationSchema>>(
      `/designations/${designationId}/deactivate`,
      {}
    );
  },

  deleteDesignation: async (designationId: number): Promise<ApiResponse<DesignationSchema>> => {
    return apiClient.delete<ApiResponse<DesignationSchema>>(`/designations/${designationId}`);
  },

  getBranches: async (
    params: BranchListParams = {}
  ): Promise<ApiResponse<BranchListResponse>> => {
    const query = new URLSearchParams();
    if (params.page) query.append("page", String(params.page));
    if (params.page_size) query.append("page_size", String(params.page_size));
    if (params.search) query.append("search", params.search);
    if (params.is_active !== undefined) query.append("is_active", String(params.is_active));
    if (params.include_deleted !== undefined)
      query.append("include_deleted", String(params.include_deleted));
    if (params.sort_by) query.append("sort_by", params.sort_by);
    if (params.sort_order) query.append("sort_order", params.sort_order);

    const queryString = query.toString();
    const url = queryString ? `/branches?${queryString}` : "/branches";
    return apiClient.get<ApiResponse<BranchListResponse>>(url);
  },

  getBranch: async (branchId: number): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.get<ApiResponse<BranchSchema>>(`/branches/${branchId}`);
  },

  createBranch: async (data: BranchCreatePayload): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.post<ApiResponse<BranchSchema>>("/branches", data);
  },

  updateBranch: async (
    branchId: number,
    data: BranchUpdatePayload
  ): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.patch<ApiResponse<BranchSchema>>(`/branches/${branchId}`, data);
  },

  activateBranch: async (branchId: number): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.post<ApiResponse<BranchSchema>>(`/branches/${branchId}/activate`, {});
  },

  deactivateBranch: async (branchId: number): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.post<ApiResponse<BranchSchema>>(`/branches/${branchId}/deactivate`, {});
  },

  deleteBranch: async (branchId: number): Promise<ApiResponse<BranchSchema>> => {
    return apiClient.delete<ApiResponse<BranchSchema>>(`/branches/${branchId}`);
  },
};
