"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees } from "@/features/employees/hooks";
import {
  LeaveBalanceEmployee,
  LeaveBalanceTable,
  LeaveBulkAdjustDrawer,
  LeaveBulkUpdateDrawer,
  useLeaveTypes,
  useLeaveBalances,
  leaveKeys,
} from "@/features/leaves";

export default function LeaveBalancePage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAdjustOpen, setIsBulkAdjustOpen] = useState<boolean>(false);
  const [isBulkUpdateOpen, setIsBulkUpdateOpen] = useState<boolean>(false);

  // Fetch real data from backend — page_size capped at 200 by FastAPI
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({ page: 1, page_size: 100 });
  const { data: leaveTypesResponse, isLoading: isLeavesLoading } = useLeaveTypes({ page_size: 100 });
  const { data: balancesResponse } = useLeaveBalances({ page_size: 100 });

  // Leave columns: display names for the table header
  const leaveColumns = useMemo(() => {
    return leaveTypesResponse?.items?.map((lt) => lt.name) ?? [];
  }, [leaveTypesResponse]);

  // Build a map: leaveTypeId -> leaveTypeName for reverse lookup
  const leaveTypeIdToName = useMemo(() => {
    const map: Record<number, string> = {};
    leaveTypesResponse?.items?.forEach((lt) => { map[lt.id] = lt.name; });
    return map;
  }, [leaveTypesResponse]);

  // Derive employees declaratively from server state — zero localStorage
  const employees = useMemo<LeaveBalanceEmployee[]>(() => {
    if (!employeeData?.items?.length) return [];

    const serverBalances = balancesResponse?.items ?? [];

    return employeeData.items.map((emp) => {
      const empIdStr = String(emp.employee_id);

      // Build balance map keyed by leave type NAME (what the table column uses)
      // Only include leave types that are actually assigned (allocated > 0)
      const leaveBalances: Record<string, number | "Not Assigned"> = {};

      serverBalances
        .filter((b) => b.employee_id === emp.employee_id && Number(b.allocated) > 0)
        .forEach((b) => {
          // Prefer leave_type_id → name lookup; fallback to b.leave_type.name
          const ltName =
            (b.leave_type_id != null ? leaveTypeIdToName[b.leave_type_id] : null) ??
            b.leave_type?.name;
          if (ltName) {
            leaveBalances[ltName] = Number(b.closing_balance);
          }
        });

      return {
        id: empIdStr,
        employeeId: emp.employee_code || empIdStr,
        name: emp.employee_name,
        department: emp.department_name || "-",
        designation: emp.designation_name || "-",
        leaveBalances,
        employeeSummary: emp,
      };
    });
  }, [employeeData, balancesResponse, leaveTypeIdToName]);

  const handleBulkLeaveUpdate = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee for bulk leave update.");
      return;
    }
    setIsBulkUpdateOpen(true);
  };

  const handleBulkUpdateSuccess = (_leaveType: string, _balanceCount: number) => {
    // Invalidate and refetch so the table always reflects server state
    queryClient.invalidateQueries({ queryKey: leaveKeys.all });
  };

  const handleAssignLeaves = () => {
    router.push("/leaves/assign");
  };

  const handleBulkAdjust = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee to adjust leave balance.");
      return;
    }
    setIsBulkAdjustOpen(true);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "leave_request", action: "read" }}>
      <div className="space-y-6 p-6 max-w-[1400px] mx-auto">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Leave Balance</h1>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={handleBulkLeaveUpdate}
              className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
            >
              Bulk Leave Update
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleAssignLeaves}
              className="h-9 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
            >
              Assign Leaves
            </Button>
            <Button
              size="sm"
              onClick={handleBulkAdjust}
              className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
            >
              Bulk Adjust
            </Button>
          </div>
        </div>

        {/* Leave Balance Table */}
        <LeaveBalanceTable
          employees={employees}
          leaveColumns={leaveColumns}
          isLoading={isLeavesLoading || isEmployeesLoading}
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />

        {/* Bulk Adjust Leave Balance Drawer */}
        <LeaveBulkAdjustDrawer
          isOpen={isBulkAdjustOpen}
          onClose={() => setIsBulkAdjustOpen(false)}
          selectedCount={selectedIds.length}
          selectedEmployeeIds={selectedIds.map(Number)}
          leaveTypes={leaveTypesResponse?.items ?? []}
          leaveOptions={leaveColumns}
          onSuccess={handleBulkUpdateSuccess}
        />

        {/* Bulk Leave Update Drawer */}
        <LeaveBulkUpdateDrawer
          isOpen={isBulkUpdateOpen}
          onClose={() => setIsBulkUpdateOpen(false)}
          selectedCount={selectedIds.length}
          selectedEmployeeIds={selectedIds.map(Number)}
          leaveTypes={leaveTypesResponse?.items ?? []}
          leaveOptions={leaveColumns}
          onSuccess={handleBulkUpdateSuccess}
        />
      </div>
    </ProtectedRoute>
  );
}
