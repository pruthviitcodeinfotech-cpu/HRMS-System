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
  LeaveBulkUpdateDrawer,
} from "@/features/leaves";

const LEAVE_BALANCE_EMPLOYEES_DATA: LeaveBalanceEmployee[] = [
  {
    id: "1",
    employeeId: "58",
    name: "Savan Ramani",
    department: "Marketing",
    designation: "marketing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "2",
    employeeId: "57",
    name: "Tulsi Baledhiya",
    department: "Marketing",
    designation: "Graphic Designer",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "3",
    employeeId: "56",
    name: "Hetal Gohil",
    department: "Marketing",
    designation: "marketing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "4",
    employeeId: "55",
    name: "Mansi Boghra",
    department: "Developer",
    designation: "Python",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "5",
    employeeId: "54",
    name: "Divyesh Pipaliya",
    department: "Marketing",
    designation: "marketing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "6",
    employeeId: "53",
    name: "Pratik Raval",
    department: "Marketing",
    designation: "marketing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "7",
    employeeId: "52",
    name: "Krishna Chodvadiya",
    department: "BDM",
    designation: "BDM",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "8",
    employeeId: "51",
    name: "Kunal Kikani",
    department: "video editing",
    designation: "video editing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "9",
    employeeId: "50",
    name: "Vivek Rathod",
    department: "Graphic Designer",
    designation: "Graphic Designer",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  {
    id: "10",
    employeeId: "49",
    name: "Rahi Patel",
    department: "video editing",
    designation: "video editing",
    leaveBalances: { "Comp Off": "Not Assigned" },
  },
  ...Array.from({ length: 48 }).map((_, idx) => ({
    id: String(idx + 11),
    employeeId: String(48 - idx),
    name: `Employee ${idx + 11}`,
    department: idx % 2 === 0 ? "Engineering" : "Marketing",
    designation: idx % 2 === 0 ? "Software Engineer" : "Executive",
    leaveBalances: { "Comp Off": (idx % 4 === 0 ? 2 : "Not Assigned") as number | "Not Assigned" },
  })),
];

export default function LeaveBalancePage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<LeaveBalanceEmployee[]>(LEAVE_BALANCE_EMPLOYEES_DATA);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAdjustOpen, setIsBulkAdjustOpen] = useState<boolean>(false);
  const [isBulkUpdateOpen, setIsBulkUpdateOpen] = useState<boolean>(false);
  const leaveColumns: string[] = ["Comp Off"];

  const handleBulkLeaveUpdate = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee for bulk leave update.");
      return;
    }
    setIsBulkUpdateOpen(true);
  };

  const handleBulkUpdateSuccess = (leaveType: string, balanceCount: number) => {
    setEmployees((prev) =>
      prev.map((emp) => {
        if (selectedIds.includes(emp.id)) {
          return {
            ...emp,
            leaveBalances: {
              ...emp.leaveBalances,
              [leaveType]: balanceCount,
            },
          };
        }
        return emp;
      })
    );
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
          selectedIds={selectedIds}
          onSelectionChange={setSelectedIds}
        />

        {/* Bulk Adjust Leave Balance Drawer */}
        <LeaveBulkAdjustDrawer
          isOpen={isBulkAdjustOpen}
          onClose={() => setIsBulkAdjustOpen(false)}
          selectedCount={selectedIds.length}
        />

        {/* Bulk Leave Update Drawer */}
        <LeaveBulkUpdateDrawer
          isOpen={isBulkUpdateOpen}
          onClose={() => setIsBulkUpdateOpen(false)}
          selectedCount={selectedIds.length}
          leaveOptions={leaveColumns}
          onSuccess={handleBulkUpdateSuccess}
        />
      </div>
    </ProtectedRoute>
  );
}
