import { useEffect, useState } from "react";
import { keepPreviousData, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { employeeService } from "../services/employees";
import { EmployeeListParams, DepartmentListParams, DesignationListParams, BranchListParams, BranchCreatePayload, BranchUpdatePayload } from "../types";

// Query-key factory: every employee cache entry lives under ["employees", ...]
export const employeeKeys = {
  all: ["employees"] as const,
  lists: () => [...employeeKeys.all, "list"] as const,
  list: (params: EmployeeListParams) => [...employeeKeys.lists(), params] as const,
  activeCount: () => [...employeeKeys.all, "active-count"] as const,
  lookup: (name: "branches" | "departments" | "designations") =>
    [...employeeKeys.all, "lookups", name] as const,
};

export const departmentKeys = {
  all: ["departments"] as const,
  lists: () => [...departmentKeys.all, "list"] as const,
  list: (params: DepartmentListParams) => [...departmentKeys.lists(), params] as const,
};

/**
 * Paginated / filtered / sorted employee list (GET /employees).
 * keepPreviousData holds the last page on screen while the next one loads,
 * so pagination and filter changes do not flash the loading skeleton.
 */
export const useEmployees = (params: EmployeeListParams) => {
  return useQuery({
    queryKey: employeeKeys.list(params),
    queryFn: async () => {
      const response = await employeeService.getEmployees(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

/** Org-wide active-employee total for the page heading (1-row page, count only). */
export const useActiveEmployeeCount = () => {
  return useQuery({
    queryKey: employeeKeys.activeCount(),
    queryFn: async () => {
      const response = await employeeService.getEmployees({
        status: "active",
        page: 1,
        page_size: 1,
      });
      return response.data.pagination.total_records;
    },
  });
};

export const useBranchOptions = () => {
  return useQuery({
    queryKey: employeeKeys.lookup("branches"),
    queryFn: async () => {
      const response = await employeeService.getBranchOptions();
      return response.data.items;
    },
  });
};

export const useDepartmentOptions = () => {
  return useQuery({
    queryKey: employeeKeys.lookup("departments"),
    queryFn: async () => {
      const response = await employeeService.getDepartmentOptions();
      return response.data.items;
    },
  });
};

export const useDesignationOptions = () => {
  return useQuery({
    queryKey: employeeKeys.lookup("designations"),
    queryFn: async () => {
      const response = await employeeService.getDesignationOptions();
      return response.data.items;
    },
  });
};

/** Debounce a fast-changing value (search input → q param) to avoid request spam. */
export const useDebouncedValue = <T>(value: T, delayMs = 400): T => {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
};

export const useDepartments = (params: DepartmentListParams) => {
  return useQuery({
    queryKey: departmentKeys.list(params),
    queryFn: async () => {
      const response = await employeeService.getDepartments(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

export const useCreateDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { dept_name: string }) => {
      const response = await employeeService.createDepartment(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.all });
    },
  });
};

export const useUpdateDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: { dept_name: string } }) => {
      const response = await employeeService.updateDepartment(id, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.all });
    },
  });
};

export const useActivateDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.activateDepartment(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.all });
    },
  });
};

export const useDeactivateDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deactivateDepartment(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.all });
    },
  });
};

export const useDeleteDepartment = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deleteDepartment(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: departmentKeys.all });
    },
  });
};

// ---------------------------------------------------------------------------
// Designation hooks
// ---------------------------------------------------------------------------

export const designationKeys = {
  all: ["designations"] as const,
  lists: () => [...designationKeys.all, "list"] as const,
  list: (params: DesignationListParams) => [...designationKeys.lists(), params] as const,
};

export const useDesignations = (params: DesignationListParams) => {
  return useQuery({
    queryKey: designationKeys.list(params),
    queryFn: async () => {
      const response = await employeeService.getDesignations(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

export const useCreateDesignation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { designation_name: string }) => {
      const response = await employeeService.createDesignation(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: designationKeys.all });
      // Also invalidate the designation lookup cache used by employee filter dropdowns
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "designations"] });
    },
  });
};

export const useUpdateDesignation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: { designation_name: string };
    }) => {
      const response = await employeeService.updateDesignation(id, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: designationKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "designations"] });
    },
  });
};

export const useActivateDesignation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.activateDesignation(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: designationKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "designations"] });
    },
  });
};

export const useDeactivateDesignation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deactivateDesignation(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: designationKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "designations"] });
    },
  });
};

export const useDeleteDesignation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deleteDesignation(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: designationKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "designations"] });
    },
  });
};

// ---------------------------------------------------------------------------
// Branch hooks
// ---------------------------------------------------------------------------

export const branchKeys = {
  all: ["branches"] as const,
  lists: () => [...branchKeys.all, "list"] as const,
  list: (params: BranchListParams) => [...branchKeys.lists(), params] as const,
  detail: (id: number) => [...branchKeys.all, "detail", id] as const,
};

export const useBranches = (params: BranchListParams) => {
  return useQuery({
    queryKey: branchKeys.list(params),
    queryFn: async () => {
      const response = await employeeService.getBranches(params);
      return response.data;
    },
    placeholderData: keepPreviousData,
  });
};

export const useBranch = (id: number, enabled = true) => {
  return useQuery({
    queryKey: branchKeys.detail(id),
    queryFn: async () => {
      const response = await employeeService.getBranch(id);
      return response.data;
    },
    enabled: enabled && !!id,
  });
};

export const useCreateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: BranchCreatePayload) => {
      const response = await employeeService.createBranch(data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: branchKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "branches"] });
    },
  });
};

export const useUpdateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, data }: { id: number; data: BranchUpdatePayload }) => {
      const response = await employeeService.updateBranch(id, data);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: branchKeys.all });
      queryClient.invalidateQueries({ queryKey: branchKeys.detail(data.branch_id) });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "branches"] });
    },
  });
};

export const useActivateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.activateBranch(id);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: branchKeys.all });
      queryClient.invalidateQueries({ queryKey: branchKeys.detail(data.branch_id) });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "branches"] });
    },
  });
};

export const useDeactivateBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deactivateBranch(id);
      return response.data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: branchKeys.all });
      queryClient.invalidateQueries({ queryKey: branchKeys.detail(data.branch_id) });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "branches"] });
    },
  });
};

export const useDeleteBranch = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const response = await employeeService.deleteBranch(id);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: branchKeys.all });
      queryClient.invalidateQueries({ queryKey: ["employees", "lookups", "branches"] });
    },
  });
};
