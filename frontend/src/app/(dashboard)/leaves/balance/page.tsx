"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import {
  LeaveBalanceEmployee,
  LeaveBalanceTable,
  LeaveBulkAdjustDrawer,
} from "@/features/leaves";

export default function LeaveBalancePage() {
  const router = useRouter();
  const [employees] = useState<LeaveBalanceEmployee[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAdjustOpen, setIsBulkAdjustOpen] = useState<boolean>(false);
  const leaveColumns: string[] = [];

  const handleBulkLeaveUpdate = () => {
    toast.info("Bulk Leave Update action opened");
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
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              Leave Balance
            </h1>
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
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />

        {/* Bulk Adjust Leave Balance Drawer */}
        <LeaveBulkAdjustDrawer
          isOpen={isBulkAdjustOpen}
          onClose={() => setIsBulkAdjustOpen(false)}
          selectedCount={selectedIds.length}
        />
      </div>
    </ProtectedRoute>
  );
}
