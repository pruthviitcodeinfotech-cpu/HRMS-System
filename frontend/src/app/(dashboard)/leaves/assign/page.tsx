"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ProtectedRoute } from "@/features/auth";
import { LeaveAssignEmployee, LeaveAssignTable, LeaveBulkAssignDrawer } from "@/features/leaves";

const LEAVE_ASSIGN_EMPLOYEES_DATA: LeaveAssignEmployee[] = [
  {
    id: "1",
    employeeId: "58",
    name: "Savan Ramani",
    department: "Marketing",
    designation: "marketing",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "2",
    employeeId: "57",
    name: "Tulsi Baledhiya",
    department: "Marketing",
    designation: "Graphic Designer",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "3",
    employeeId: "56",
    name: "Hetal Gohil",
    department: "Marketing",
    designation: "marketing",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "4",
    employeeId: "55",
    name: "Mansi Boghra",
    department: "Developer",
    designation: "Python",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "5",
    employeeId: "54",
    name: "Divyesh Pipaliya",
    department: "Marketing",
    designation: "marketing",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "6",
    employeeId: "53",
    name: "Pratik Raval",
    department: "Marketing",
    designation: "marketing",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "7",
    employeeId: "51",
    name: "Kunal Kikani",
    department: "video editing",
    designation: "video editing",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "8",
    employeeId: "52",
    name: "Krishna Chodvadiya",
    department: "BDM",
    designation: "BDM",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "9",
    employeeId: "50",
    name: "Vivek Rathod",
    department: "Graphic Designer",
    designation: "Graphic Designer",
    leaveAssignments: { "Comp Off": false },
  },
  {
    id: "10",
    employeeId: "49",
    name: "Rahi Patel",
    department: "video editing",
    designation: "video editing",
    leaveAssignments: { "Comp Off": false },
  },
  ...Array.from({ length: 30 }).map((_, idx) => ({
    id: String(idx + 11),
    employeeId: String(48 - idx),
    name: `Employee ${idx + 11}`,
    department: idx % 2 === 0 ? "Engineering" : "Support",
    designation: idx % 2 === 0 ? "Software Engineer" : "Support Executive",
    leaveAssignments: { "Comp Off": false },
  })),
];

export default function LeaveAssignPage() {
  const router = useRouter();
  const [employees, setEmployees] = useState<LeaveAssignEmployee[]>(LEAVE_ASSIGN_EMPLOYEES_DATA);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAssignOpen, setIsBulkAssignOpen] = useState<boolean>(false);
  const leaveTypes: string[] = ["Comp Off"];

  const handleToggleAssignment = (employeeId: string, leaveType: string) => {
    setEmployees((prev) =>
      prev.map((emp) => {
        if (emp.id === employeeId) {
          const currentVal = emp.leaveAssignments[leaveType] ?? false;
          const nextVal = !currentVal;
          const empName = emp.employeeSummary?.employee_name || emp.name;
          toast.success(
            `${leaveType} leave ${nextVal ? "assigned to" : "unassigned from"} ${empName}`
          );
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
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee to assign leave.");
      return;
    }
    setIsBulkAssignOpen(true);
  };

  const handleBulkAssignSuccess = (leaveType: string, isAssigned: boolean) => {
    setEmployees((prev) =>
      prev.map((emp) => {
        if (selectedIds.includes(emp.id)) {
          return {
            ...emp,
            leaveAssignments: {
              ...emp.leaveAssignments,
              [leaveType]: isAssigned,
            },
          };
        }
        return emp;
      })
    );
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
