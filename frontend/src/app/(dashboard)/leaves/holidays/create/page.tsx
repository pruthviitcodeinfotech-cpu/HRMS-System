"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { ApiError } from "@/services/api-client/error-handler";
import {
  HolidayTemplate,
  HolidayTable,
  HolidayViewDrawer,
  HolidayDeleteDialog,
  HolidayTemplateEditor,
  HolidayItem,
  HolidayTemplateSchema,
  useHolidayTemplates,
  useCreateHolidayTemplate,
  useUpdateHolidayTemplate,
  useDeleteHolidayTemplate,
  useCreateHolidayItem,
  useDeleteHolidayItem,
} from "@/features/holidays";

const getErrorMessage = (err: unknown): string => {
  if (err instanceof ApiError) {
    return err.message;
  }
  if (isAxiosError(err)) {
    const data = err.response?.data;
    if (data && typeof data === "object") {
      const msg = data.message || data.detail;
      if (typeof msg === "string") return msg;
      if (Array.isArray(data.detail)) {
        return data.detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join("; ");
      }
    }
    return err.message || "An unexpected error occurred.";
  }
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred.";
};

const mapBackendTemplateToUI = (tmpl: HolidayTemplateSchema): HolidayTemplate => ({
  id: String(tmpl.id),
  name: tmpl.name,
  holidayCount: tmpl.holiday_count || 0,
  assignedEmployeesCount: 0,
  createdOn: tmpl.created_at
    ? new Date(tmpl.created_at).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "-",
  createdBy: tmpl.created_by ? `User ${tmpl.created_by}` : "System",
  lastModified: tmpl.updated_at
    ? new Date(tmpl.updated_at).toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "long",
        year: "numeric",
      })
    : "-",
  lastModifiedBy: tmpl.updated_by ? `User ${tmpl.updated_by}` : "System",
  items: (tmpl.items || []).map((item) => ({
    id: String(item.id),
    name: item.name,
    startDate: item.start_date,
    endDate: item.end_date,
    durationDays: item.duration_days,
    dayOfWeek: item.day_of_week ?? undefined,
  })),
});

export default function HolidayCreatePage() {
  const router = useRouter();

  // Server Pagination State
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Fetch Templates via React Query for table
  const { data: templateResponse, isLoading } = useHolidayTemplates({
    page,
    page_size: pageSize,
  });

  // Fetch all templates (up to 500) for real-time duplicate template name validation
  const { data: allTemplatesResponse } = useHolidayTemplates({
    page: 1,
    page_size: 500,
  });

  // Mutations
  const createTemplateMutation = useCreateHolidayTemplate();
  const updateTemplateMutation = useUpdateHolidayTemplate();
  const deleteTemplateMutation = useDeleteHolidayTemplate();
  const createItemMutation = useCreateHolidayItem();
  const deleteItemMutation = useDeleteHolidayItem();

  // View Mode: 'list' | 'editor'
  const [viewMode, setViewMode] = useState<"list" | "editor">("list");
  const [templateToEdit, setTemplateToEdit] = useState<HolidayTemplate | null>(null);

  // View & Delete Modal States
  const [isViewDrawerOpen, setIsViewDrawerOpen] = useState<boolean>(false);
  const [templateToView, setTemplateToView] = useState<HolidayTemplate | null>(null);

  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState<boolean>(false);
  const [templateToDelete, setTemplateToDelete] = useState<HolidayTemplate | null>(null);

  // Map server response items
  const templates: HolidayTemplate[] = (templateResponse?.items || []).map(mapBackendTemplateToUI);
  const allTemplateNames: string[] = (allTemplatesResponse?.items || []).map((t) => t.name);
  const totalRecords = templateResponse?.pagination?.total_records || 0;

  // Local search filter (server-side search not yet wired)
  const filteredTemplates = searchQuery.trim()
    ? templates.filter((t) => t.name.toLowerCase().includes(searchQuery.toLowerCase()))
    : templates;

  // ── Navigation ──────────────────────────────────────────────────────────────

  const handleOpenCreateTemplate = () => {
    setTemplateToEdit(null);
    setViewMode("editor");
  };

  const handleOpenEditTemplate = (template: HolidayTemplate) => {
    setTemplateToEdit(template);
    setViewMode("editor");
  };

  const handleBackToList = () => {
    setTemplateToEdit(null);
    setViewMode("list");
  };

  const handleOpenViewDrawer = (template: HolidayTemplate) => {
    setTemplateToView(template);
    setIsViewDrawerOpen(true);
  };

  const handleOpenDeleteDialog = (template: HolidayTemplate) => {
    setTemplateToDelete(template);
    setIsDeleteDialogOpen(true);
  };

  // ── Save (atomic single-request create OR incremental edit) ─────────────────

  const handleSaveTemplateDetails = async (templateName: string, items: HolidayItem[]) => {
    try {
      if (templateToEdit) {
        // ── EDIT MODE ───────────────────────────────────────────────────────
        // Update template name via PATCH
        await updateTemplateMutation.mutateAsync({
          templateId: Number(templateToEdit.id),
          data: { name: templateName },
        });

        // 1. Delete items removed by the user in the editor
        const remainingItemIds = new Set(items.map((item) => String(item.id)));
        const removedItems = (templateToEdit.items || []).filter(
          (origItem) =>
            origItem.id &&
            !origItem.id.startsWith("h_") &&
            !remainingItemIds.has(String(origItem.id))
        );

        for (const item of removedItems) {
          await deleteItemMutation.mutateAsync({
            templateId: Number(templateToEdit.id),
            itemId: Number(item.id),
          });
        }

        // 2. Add only genuinely new items (those without a server-assigned numeric ID)
        const newItems = items.filter((item) => !item.id || item.id.startsWith("h_"));
        for (const item of newItems) {
          await createItemMutation.mutateAsync({
            templateId: Number(templateToEdit.id),
            data: {
              name: item.name,
              start_date: item.startDate,
              end_date: item.endDate,
              duration_days: item.durationDays ?? 1,
              day_of_week: item.dayOfWeek ?? undefined,
            },
          });
        }

        toast.success(`Holiday template "${templateName}" updated successfully!`);
      } else {
        // ── CREATE MODE — single atomic request ─────────────────────────────
        // Template + all items are created in ONE API call / ONE DB transaction.
        // If the backend fails for any reason, nothing is persisted.
        await createTemplateMutation.mutateAsync({
          name: templateName,
          items: items.map((item) => ({
            name: item.name,
            start_date: item.startDate,
            end_date: item.endDate,
            duration_days: item.durationDays ?? 1,
            day_of_week: item.dayOfWeek ?? null,
          })),
        });

        toast.success(`Holiday template "${templateName}" created successfully!`);
      }

      setViewMode("list");
      setTemplateToEdit(null);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error));
    }
  };

  // ── Delete ───────────────────────────────────────────────────────────────────

  const handleDeleteTemplate = async (templateId: string): Promise<void> => {
    await deleteTemplateMutation.mutateAsync(Number(templateId));
    toast.success("Holiday template deleted successfully.");
    setIsDeleteDialogOpen(false);
    setTemplateToDelete(null);
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <ProtectedRoute requiredPermission={{ feature: "holiday", action: "create" }}>
      <div className="space-y-6 p-6 max-w-[1400px] mx-auto">
        {viewMode === "editor" ? (
          <HolidayTemplateEditor
            onBack={handleBackToList}
            onSave={handleSaveTemplateDetails}
            initialTemplate={templateToEdit}
            existingTemplateNames={
              templateToEdit
                ? allTemplateNames.filter((name) => name.toLowerCase() !== templateToEdit.name.toLowerCase())
                : allTemplateNames
            }
          />
        ) : (
          <>
            {/* Top Header Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
                  Holiday Create
                </h1>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => router.push("/leaves/holidays/assign")}
                  className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
                >
                  Assign Holiday
                </Button>
                <Button
                  size="sm"
                  onClick={handleOpenCreateTemplate}
                  className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
                >
                  Create Template
                </Button>
              </div>
            </div>

            {/* Holiday Table */}
            <HolidayTable
              templates={filteredTemplates}
              isLoading={isLoading}
              totalRecords={totalRecords}
              currentPage={page}
              pageSize={pageSize}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
              onViewTemplate={handleOpenViewDrawer}
              onEditTemplate={handleOpenEditTemplate}
              onDeleteTemplate={handleOpenDeleteDialog}
            />
          </>
        )}

        {/* View Template Details Drawer */}
        <HolidayViewDrawer
          isOpen={isViewDrawerOpen}
          onClose={() => setIsViewDrawerOpen(false)}
          template={templateToView}
        />

        {/* Delete Confirmation Dialog */}
        <HolidayDeleteDialog
          isOpen={isDeleteDialogOpen}
          onClose={() => setIsDeleteDialogOpen(false)}
          template={templateToDelete}
          onConfirmDelete={handleDeleteTemplate}
        />
      </div>
    </ProtectedRoute>
  );
}
