"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";
import {
  LeaveAssignEmployee,
  LeaveAssignTable,
  LeaveBulkAssignDrawer,
  useLeaveTypes,
  useLeaveBalances,
  leaveService,
  leaveKeys,
} from "@/features/leaves";

export default function LeaveAssignPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAssignOpen, setIsBulkAssignOpen] = useState<boolean>(false);

  // Fetch real employees and balances from backend
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({ page: 1, page_size: 100 });
  const { data: leaveTypesResponse, isLoading: isLeavesLoading } = useLeaveTypes({ page_size: 100 });
  const { data: balancesResponse, isLoading: isBalancesLoading, refetch: refetchBalances } = useLeaveBalances({ page_size: 100 });

  const leaveTypeColumns = useMemo(() => {
    if (leaveTypesResponse?.items && leaveTypesResponse.items.length > 0) {
      return leaveTypesResponse.items.map((lt) => ({ id: lt.id, name: lt.name }));
    }
    return [];
  }, [leaveTypesResponse]);

  // Compute live employees and backend leave assignments declaratively directly from database state
  const employees: LeaveAssignEmployee[] = useMemo(() => {
    const serverBalances = balancesResponse?.items || [];
    if (!employeeData?.items || employeeData.items.length === 0) return [];

    return employeeData.items.map((emp) => {
      const empIdStr = String(emp.employee_id);
      const empCodeStr = emp.employee_code || empIdStr;

      // Extract server balances matching employee ID
      const empBalances = serverBalances.filter(
        (b) => String(b.employee_id) === String(emp.employee_id)
      );
      const serverAssignMap: Record<string, boolean> = {};

      empBalances.forEach((b) => {
        const key = String(b.leave_type_id);
        const isAssigned = Number(b.allocated || 0) > 0 || Number(b.closing_balance || 0) > 0;
        serverAssignMap[key] = isAssigned;
      });

      return {
        id: empIdStr,
        employeeId: empCodeStr,
        name: emp.employee_name,
        department: emp.department_name || "-",
        designation: emp.designation_name || "-",
        leaveAssignments: serverAssignMap,
        employeeSummary: emp,
      };
    });
  }, [employeeData, balancesResponse]);

  const handleToggleAssignment = async (employeeIdStr: string, leaveTypeId: number) => {
    const empIdNum = Number(employeeIdStr);
    if (!leaveTypeId || !empIdNum) return;

    const empObj = employees.find((e) => e.id === employeeIdStr || e.employeeId === employeeIdStr);
    const ltObj = leaveTypesResponse?.items.find((lt) => lt.id === leaveTypeId);
    const currentVal = empObj?.leaveAssignments[String(leaveTypeId)] ?? false;
    const nextVal = !currentVal;

    try {
      await leaveService.assignLeaveTypes({
        employee_ids: [empIdNum],
        leave_type_ids: [leaveTypeId],
        is_assigned: nextVal,
      });

      await queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      await queryClient.refetchQueries({ queryKey: leaveKeys.all, type: "active" });
      await refetchBalances();
      toast.success(
        `${ltObj?.name || "Leave"} ${nextVal ? "assigned to" : "unassigned from"} ${empObj?.name || "employee"}`
      );
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: unknown }).message)
          : "Failed to update leave assignment";
      toast.error(message);
    }
  };

  const handleBulkAssign = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee to assign leave.");
      return;
    }
    setIsBulkAssignOpen(true);
  };

  const handleBulkAssignSuccess = async (leaveTypeId: number, isAssigned: boolean) => {
    if (!leaveTypeId || selectedIds.length === 0) return;

    const ltObj = leaveTypesResponse?.items.find((lt) => lt.id === leaveTypeId);
    const targetEmpIds = selectedIds.map((id) => Number(id)).filter((n) => !isNaN(n) && n > 0);
    if (targetEmpIds.length === 0) return;

    try {
      await leaveService.assignLeaveTypes({
        employee_ids: targetEmpIds,
        leave_type_ids: [leaveTypeId],
        is_assigned: isAssigned,
      });

      await queryClient.invalidateQueries({ queryKey: leaveKeys.all });
      await queryClient.refetchQueries({ queryKey: leaveKeys.all, type: "active" });
      await refetchBalances();
      toast.success(`${ltObj?.name || "Leave"} ${isAssigned ? "assigned to" : "unassigned from"} ${targetEmpIds.length} employees`);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "message" in err
          ? String((err as { message: unknown }).message)
          : "Failed to bulk assign leave types";
      toast.error(message);
    }
  };

  const handleManageBalance = () => {
    router.push("/leaves/balance");
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_type", action: "read" }}>
      <div className="space-y-6 p-6 max-w-[1400px] mx-auto">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Leave Assign</h1>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleManageBalance}
              className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
            >
              Manage Leave Balance
            </Button>
            <Button
              size="sm"
              onClick={handleBulkAssign}
              className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
            >
              Bulk Assign
            </Button>
          </div>
        </div>

        {/* Leave Assign Table */}
        <LeaveAssignTable
          employees={employees}
          leaveTypes={leaveTypeColumns}
          isLoading={isLeavesLoading || isEmployeesLoading || isBalancesLoading}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onToggleAssignment={handleToggleAssignment}
        />

        {/* Bulk Assign Leave Drawer */}
        <LeaveBulkAssignDrawer
          isOpen={isBulkAssignOpen}
          onClose={() => setIsBulkAssignOpen(false)}
          selectedCount={selectedIds.length}
          leaveOptions={leaveTypeColumns}
          onSuccess={handleBulkAssignSuccess}
        />
      </div>
    </ProtectedRoute>
  );
}
