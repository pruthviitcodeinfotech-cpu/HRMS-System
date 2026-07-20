"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/features/auth";
import {
  LeaveTypeSchema,
  LeaveCreateTable,
  LeaveCreateDrawer,
  useLeaveTypes,
  useLeaveSettings,
  useDeleteLeaveType,
} from "@/features/leaves";
import { ApiError } from "@/services/api-client/error-handler";

export default function LeaveCreatePage() {
  const router = useRouter();

  // Table state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [sortBy, setSortBy] = useState<string>("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [editingLeave, setEditingLeave] = useState<LeaveTypeSchema | null>(null);

  // Queries & Mutations
  const { data: leaveTypesData, isLoading, isError } = useLeaveTypes({
    page,
    page_size: pageSize,
    search: searchQuery || undefined,
    sort_by: sortBy,
    sort_order: sortOrder,
  });

  const { data: settingsData } = useLeaveSettings();
  const deleteLeaveMutation = useDeleteLeaveType();

  const handleOpenCreateDrawer = () => {
    setEditingLeave(null);
    setIsDrawerOpen(true);
  };

  const handleOpenEditDrawer = (leave: LeaveTypeSchema) => {
    setEditingLeave(leave);
    setIsDrawerOpen(true);
  };

  const handleDeleteLeave = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this leave policy?")) {
      return;
    }
    try {
      await deleteLeaveMutation.mutateAsync(id);
      toast.success("Leave policy deleted successfully");
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        toast.error(err.message || "Failed to delete leave policy.");
      } else {
        toast.error("An error occurred while deleting the leave policy.");
      }
    }
  };

  const handleToggleSort = () => {
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    setSortBy("name");
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_type", action: "read" }}>
      <div className="space-y-6 p-6 max-w-[1400px] mx-auto">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              Leave Create
            </h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <Input
                type="text"
                placeholder="Search leave..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setPage(1);
                }}
                className="h-9 w-48 pl-8 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
              />
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/leaves/assign")}
              className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
            >
              Assign Leaves
            </Button>
            <Button
              size="sm"
              onClick={handleOpenCreateDrawer}
              className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
            >
              Create New Leave
            </Button>
          </div>
        </div>

        {/* Leave Table View */}
        <LeaveCreateTable
          leaves={leaveTypesData?.items || []}
          totalRecords={leaveTypesData?.pagination?.total_records || 0}
          currentPage={page}
          pageSize={pageSize}
          sortOrder={sortOrder}
          isLoading={isLoading}
          isError={isError}
          onPageChange={setPage}
          onPageSizeChange={(newSize) => {
            setPageSize(newSize);
            setPage(1);
          }}
          onToggleSort={handleToggleSort}
          onEditLeave={handleOpenEditDrawer}
          onDeleteLeave={handleDeleteLeave}
        />

        {/* Step 1 & Step 2 Right Side Drawer */}
        <LeaveCreateDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          editingLeave={editingLeave}
          currentSettings={settingsData}
        />
      </div>
    </ProtectedRoute>
  );
}
