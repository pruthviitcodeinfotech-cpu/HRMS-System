"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { LeaveAssignEmployee, LeaveAssignTable } from "@/features/leaves";

export default function LeaveAssignPage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<LeaveAssignEmployee[]>([]);
  const leaveTypes: string[] = [];

  const handleToggleAssignment = (employeeId: string, leaveType: string) => {
    setEmployees((prev) =>
      prev.map((emp) => {
        if (emp.id === employeeId) {
          const currentVal = emp.leaveAssignments[leaveType] ?? false;
          const nextVal = !currentVal;
          return {
            ...emp,
            leaveAssignments: {
              ...emp.leaveAssignments,
              [leaveType]: nextVal,
            },
          };
        }
        return emp;
      })
    );
  };

  const handleBulkAssign = () => {
    toast.info("Bulk Leave Assign action triggered");
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
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              Leave Assign
            </h1>
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
          onToggleAssignment={handleToggleAssignment}
        />
      </div>
    </ProtectedRoute>
  );
}
