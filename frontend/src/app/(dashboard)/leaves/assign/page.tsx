"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
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
} from "@/features/leaves";

export default function LeaveAssignPage() {
  const router = useRouter();

  const [localAssignments, setLocalAssignments] = useState<Record<string, Record<string, boolean>>>({});
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAssignOpen, setIsBulkAssignOpen] = useState<boolean>(false);

  // Fetch real employees and balances from backend
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({ page: 1, page_size: 100 });
  const { data: leaveTypesResponse, isLoading: isLeavesLoading } = useLeaveTypes({ page_size: 100 });
  const { data: balancesResponse, refetch: refetchBalances } = useLeaveBalances({ page_size: 500 });

  const leaveTypes = useMemo(() => {
    if (leaveTypesResponse?.items && leaveTypesResponse.items.length > 0) {
      return leaveTypesResponse.items.map((lt) => lt.name);
    }
    return [];
  }, [leaveTypesResponse]);

  // Compute live employees and backend leave assignments declaratively
  const employees: LeaveAssignEmployee[] = useMemo(() => {
    const serverBalances = balancesResponse?.items || [];
    if (!employeeData?.items || employeeData.items.length === 0) return [];

    return employeeData.items.map((emp) => {
      const empIdStr = String(emp.employee_id);
      const empCodeStr = emp.employee_code || empIdStr;

      // Extract server balances
      const empBalances = serverBalances.filter((b) => b.employee_id === emp.employee_id);
      const serverAssignMap: Record<string, boolean> = {};
      empBalances.forEach((b) => {
        if (b.leave_type?.name) {
          serverAssignMap[b.leave_type.name] = true;
        }
      });

      const overrideMap = localAssignments[empIdStr] || localAssignments[empCodeStr] || {};

      return {
        id: empIdStr,
        employeeId: empCodeStr,
        name: emp.employee_name,
        department: emp.department_name || "-",
        designation: emp.designation_name || "-",
        leaveAssignments: {
          ...serverAssignMap,
          ...overrideMap,
        },
        employeeSummary: emp,
      };
    });
  }, [employeeData, balancesResponse, localAssignments]);

  const handleToggleAssignment = async (employeeIdStr: string, leaveTypeName: string) => {
    const empIdNum = Number(employeeIdStr);
    const ltObj = leaveTypesResponse?.items.find((lt) => lt.name === leaveTypeName);
    if (!ltObj || !empIdNum) return;

    const empObj = employees.find((e) => e.id === employeeIdStr || e.employeeId === employeeIdStr);
    const currentVal = empObj?.leaveAssignments[leaveTypeName] ?? false;
    const nextVal = !currentVal;

    try {
      await leaveService.assignLeaveTypes({
        employee_ids: [empIdNum],
        leave_type_ids: [ltObj.id],
        is_assigned: nextVal,
      });

      setLocalAssignments((prev) => ({
        ...prev,
        [employeeIdStr]: {
          ...(prev[employeeIdStr] || {}),
          [leaveTypeName]: nextVal,
        },
      }));
      refetchBalances();
      toast.success(`${leaveTypeName} leave ${nextVal ? "assigned to" : "unassigned from"} ${empObj?.name || "employee"}`);
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

  const handleBulkAssignSuccess = async (leaveTypeName: string, isAssigned: boolean) => {
    const ltObj = leaveTypesResponse?.items.find((lt) => lt.name === leaveTypeName);
    if (!ltObj || selectedIds.length === 0) return;

    const targetEmpIds = selectedIds.map((id) => Number(id)).filter((n) => !isNaN(n) && n > 0);
    if (targetEmpIds.length === 0) return;

    try {
      await leaveService.assignLeaveTypes({
        employee_ids: targetEmpIds,
        leave_type_ids: [ltObj.id],
        is_assigned: isAssigned,
      });

      setLocalAssignments((prev) => {
        const nextMap = { ...prev };
        selectedIds.forEach((id) => {
          nextMap[id] = {
            ...(nextMap[id] || {}),
            [leaveTypeName]: isAssigned,
          };
        });
        return nextMap;
      });
      refetchBalances();
      toast.success(`${leaveTypeName} leave ${isAssigned ? "assigned to" : "unassigned from"} ${targetEmpIds.length} employees`);
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
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "read" }}>
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
          leaveTypes={leaveTypes}
          isLoading={isLeavesLoading || isEmployeesLoading}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
          onToggleAssignment={handleToggleAssignment}
        />

        {/* Bulk Assign Leave Drawer */}
        <LeaveBulkAssignDrawer
          isOpen={isBulkAssignOpen}
          onClose={() => setIsBulkAssignOpen(false)}
          selectedCount={selectedIds.length}
          leaveOptions={leaveTypes}
          onSuccess={handleBulkAssignSuccess}
        />
      </div>
    </ProtectedRoute>
  );
}
