"use client";

import { useMemo, useState } from "react";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";
import { EmployeeSummary } from "@/features/employees/types";
import {
  HolidayAssignEmployee,
  HolidayAssignTable,
  HolidayAssignDrawer,
  useHolidayTemplates,
  useHolidayAssignments,
  useAssignHolidayTemplate,
} from "@/features/holidays";

const getErrorMessage = (err: unknown): string => {
  if (isAxiosError(err)) {
    return (
      err.response?.data?.message || err.response?.data?.detail || "An unexpected error occurred."
    );
  }
  if (err instanceof Error) return err.message;
  return "An unexpected error occurred.";
};

const mapEmployeeToAssignRow = (
  emp: EmployeeSummary,
  assignmentMap: Record<number, string>
): HolidayAssignEmployee => ({
  id: String(emp.employee_id),
  employeeId: emp.employee_code || String(emp.employee_id),
  name: emp.employee_name,
  department: emp.department_name || "-",
  designation: emp.designation_name || "-",
  assignedTemplate: assignmentMap[emp.employee_id] || "-",
});

export default function HolidayAssignPage() {
  // Server-side employee search and pagination state
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Fetch employees from existing Employee Module
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({
    page,
    page_size: pageSize,
    q: searchQuery,
  });

  // Fetch holiday templates for assignment selection drawer
  const { data: templatesResponse } = useHolidayTemplates({
    page: 1,
    page_size: 100,
  });

  // Fetch all employee holiday assignments
  const { data: holidayAssignments } = useHolidayAssignments();

  const assignTemplateMutation = useAssignHolidayTemplate();

  const assignmentMap = useMemo(() => {
    const map: Record<number, string> = {};
    (holidayAssignments || []).forEach((assignment) => {
      if (assignment.employee_id && assignment.template?.name) {
        map[assignment.employee_id] = assignment.template.name;
      }
    });
    return map;
  }, [holidayAssignments]);

  const employees: HolidayAssignEmployee[] = (employeeData?.items || []).map((emp) =>
    mapEmployeeToAssignRow(emp, assignmentMap)
  );
  const totalRecords = employeeData?.pagination.total_records || 0;

  const availableTemplates = (templatesResponse?.items || []).map((t) => ({
    id: t.id,
    name: t.name,
  }));

  const handleAssignTemplateClick = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee to assign a holiday template.");
      return;
    }
    setIsDrawerOpen(true);
  };

  const handleAssignSubmit = async (templateId: number) => {
    try {
      // Loop over selected employee IDs and invoke assignment API
      for (const strId of selectedIds) {
        const empId = Number(strId);
        await assignTemplateMutation.mutateAsync({
          employeeId: empId,
          data: { template_id: templateId },
        });
      }

      toast.success(`Holiday template assigned to ${selectedIds.length} employee(s) successfully!`);
      setSelectedIds([]);
    } catch (error: unknown) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "holiday", action: "edit" }}>
      <div className="space-y-6 p-6 max-w-[1400px] mx-auto">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Holiday Assign</h1>
          </div>

          <div className="flex items-center gap-3">
            <Button
              size="sm"
              onClick={handleAssignTemplateClick}
              className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
            >
              Assign Template
            </Button>
          </div>
        </div>

        {/* Holiday Assign Table */}
        <HolidayAssignTable
          employees={employees}
          isLoading={isEmployeesLoading}
          totalRecords={totalRecords}
          currentPage={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />

        {/* Assign Holiday Template Drawer */}
        <HolidayAssignDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          selectedCount={selectedIds.length}
          templates={availableTemplates}
          onAssignSubmit={handleAssignSubmit}
          isSubmitting={assignTemplateMutation.isPending}
        />
      </div>
    </ProtectedRoute>
  );
}
