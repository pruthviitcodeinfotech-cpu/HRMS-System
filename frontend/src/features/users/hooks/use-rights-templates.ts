import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  rightsTemplatesService,
  RightsTemplatesQueryParams,
} from "../services/rights-templates-service";
import {
  CreateRightsTemplateInput,
  UpdateRightsTemplateInput,
  TemplatePermissionInput,
} from "../types";
import { toast } from "sonner";

export const RIGHTS_TEMPLATES_QUERY_KEY = ["rights-templates"];
export const PERMISSION_CATALOG_QUERY_KEY = ["permission-catalog"];

export function usePermissionCatalog() {
  return useQuery({
    queryKey: PERMISSION_CATALOG_QUERY_KEY,
    queryFn: async () => {
      const res = await rightsTemplatesService.getPermissionCatalog();
      return res.data || [];
    },
    staleTime: 1000 * 60 * 10, // Cache catalog for 10 mins
  });
}

export function useRightsTemplates(params?: RightsTemplatesQueryParams) {
  return useQuery({
    queryKey: [...RIGHTS_TEMPLATES_QUERY_KEY, params],
    queryFn: async () => {
      const res = await rightsTemplatesService.getRightsTemplates(params);
      return res.data;
    },
  });
}

export function useRightsTemplateDetail(id?: number) {
  return useQuery({
    queryKey: [...RIGHTS_TEMPLATES_QUERY_KEY, id],
    queryFn: async () => {
      if (!id) return null;
      const res = await rightsTemplatesService.getRightsTemplateById(id);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useCreateRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateRightsTemplateInput) =>
      rightsTemplatesService.createRightsTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template created successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to create rights template");
    },
  });
}

export function useUpdateRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateRightsTemplateInput }) =>
      rightsTemplatesService.updateRightsTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template updated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to update rights template");
    },
  });
}

export function useDeleteRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => rightsTemplatesService.deleteRightsTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template deleted successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to delete rights template");
    },
  });
}

export function useDuplicateRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      rightsTemplatesService.duplicateRightsTemplate(id, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template duplicated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to duplicate rights template");
    },
  });
}

export function useActivateRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => rightsTemplatesService.activateRightsTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template activated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to activate rights template");
    },
  });
}

export function useDeactivateRightsTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => rightsTemplatesService.deactivateRightsTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Rights template deactivated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to deactivate rights template");
    },
  });
}

export function useTemplatePermissions(id?: number) {
  return useQuery({
    queryKey: [...RIGHTS_TEMPLATES_QUERY_KEY, "permissions", id],
    queryFn: async () => {
      if (!id) return [];
      const res = await rightsTemplatesService.getTemplatePermissions(id);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useReplaceTemplatePermissions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      permissions,
    }: {
      id: number;
      permissions: TemplatePermissionInput[];
    }) => rightsTemplatesService.replaceTemplatePermissions(id, permissions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: RIGHTS_TEMPLATES_QUERY_KEY });
      toast.success("Template permissions updated successfully");
    },
    onError: (err: any) => {
      toast.error(err?.message || err?.detail || "Failed to save template permissions");
    },
  });
}

export function useRightsTemplatesLogs() {
  return useQuery({
    queryKey: [...RIGHTS_TEMPLATES_QUERY_KEY, "logs"],
    queryFn: async () => {
      const res = await rightsTemplatesService.getRightsTemplatesLogs();
      return res.data;
    },
  });
}
