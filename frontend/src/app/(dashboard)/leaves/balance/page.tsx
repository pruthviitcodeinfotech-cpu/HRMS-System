"use client";

import { useState, useMemo, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
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
} from "@/features/leaves";

const STORAGE_KEY = "hrms_leave_balances";

const getSavedBalances = (): Record<string, Record<string, number | "Not Assigned">> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveBalances = (data: Record<string, Record<string, number | "Not Assigned">>) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.error("Failed to save balances", err);
  }
};

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

const getSavedAssignments = (): Record<string, Record<string, boolean>> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem("hrms_leave_assignments");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveAssignments = (data: Record<string, Record<string, boolean>>) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem("hrms_leave_assignments", JSON.stringify(data));
  } catch (err) {
    console.error("Failed to save assignments", err);
  }
};

export default function LeaveBalancePage() {
  const router = useRouter();

  // Initialize state with localStorage persistence + mock fallback
  const [employees, setEmployees] = useState<LeaveBalanceEmployee[]>(() => {
    const savedMap = getSavedBalances();
    const savedAssignments = getSavedAssignments();
    return LEAVE_BALANCE_EMPLOYEES_DATA.map((emp) => {
      const savedForEmp = savedMap[emp.id] || savedMap[emp.employeeId] || {};
      const assignmentsForEmp = savedAssignments[emp.id] || savedAssignments[emp.employeeId] || {};
      
      const mergedBalances: Record<string, number | "Not Assigned"> = { ...emp.leaveBalances };
      Object.keys(assignmentsForEmp).forEach((lt) => {
        if (assignmentsForEmp[lt] && (savedForEmp[lt] === undefined || savedForEmp[lt] === "Not Assigned")) {
          mergedBalances[lt] = 0;
        } else if (!assignmentsForEmp[lt] && savedMap[emp.id]?.[lt] === undefined) {
          mergedBalances[lt] = "Not Assigned";
        }
      });

      return {
        ...emp,
        leaveBalances: {
          ...mergedBalances,
          ...savedForEmp,
        },
      };
    });
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAdjustOpen, setIsBulkAdjustOpen] = useState<boolean>(false);
  const [isBulkUpdateOpen, setIsBulkUpdateOpen] = useState<boolean>(false);

  // Fetch real employees and balances from backend
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({ page: 1, page_size: 100 });
  const { data: leaveTypesResponse, isLoading: isLeavesLoading } = useLeaveTypes({ page_size: 100 });
  const { data: balancesResponse } = useLeaveBalances({ page_size: 500 });

  const leaveColumns = useMemo(() => {
    if (leaveTypesResponse?.items && leaveTypesResponse.items.length > 0) {
      return leaveTypesResponse.items.map((lt) => lt.name);
    }
    return ["Comp Off"];
  }, [leaveTypesResponse]);

  // Sync live backend employees & saved balances
  useEffect(() => {
    const savedMap = getSavedBalances();
    const savedAssignments = getSavedAssignments();
    const serverBalances = balancesResponse?.items || [];

    if (employeeData?.items && employeeData.items.length > 0) {
      const liveRows: LeaveBalanceEmployee[] = employeeData.items.map((emp) => {
        const empIdStr = String(emp.employee_id);
        const empCodeStr = emp.employee_code || empIdStr;
        const savedForEmp = savedMap[empIdStr] || savedMap[empCodeStr] || {};
        const assignmentsForEmp = savedAssignments[empIdStr] || savedAssignments[empCodeStr] || {};

        // Merge server balances
        const empBalances = serverBalances.filter((b) => b.employee_id === emp.employee_id);
        const serverBalanceMap: Record<string, number | "Not Assigned"> = {};
        empBalances.forEach((b) => {
          if (b.leave_type?.name) {
            serverBalanceMap[b.leave_type.name] = Number(b.closing_balance);
          }
        });

        // Initialize assigned leave types to 0 if not explicitly defined
        const mergedAssignmentsMap: Record<string, number | "Not Assigned"> = {};
        Object.keys(assignmentsForEmp).forEach((lt) => {
          if (assignmentsForEmp[lt] && savedForEmp[lt] === undefined) {
            mergedAssignmentsMap[lt] = 0;
          }
        });

        return {
          id: empIdStr,
          employeeId: empCodeStr,
          name: emp.employee_name,
          department: emp.department_name || "-",
          designation: emp.designation_name || "-",
          leaveBalances: {
            ...mergedAssignmentsMap,
            ...serverBalanceMap,
            ...savedForEmp,
          },
          employeeSummary: emp,
        };
      });
      setEmployees(liveRows);
    } else {
      setEmployees((prev) =>
        prev.map((emp) => {
          const savedForEmp = savedMap[emp.id] || savedMap[emp.employeeId] || {};
          const assignmentsForEmp = savedAssignments[emp.id] || savedAssignments[emp.employeeId] || {};
          const mergedAssignmentsMap: Record<string, number | "Not Assigned"> = {};
          Object.keys(assignmentsForEmp).forEach((lt) => {
            if (assignmentsForEmp[lt] && savedForEmp[lt] === undefined) {
              mergedAssignmentsMap[lt] = 0;
            }
          });

          return {
            ...emp,
            leaveBalances: {
              ...mergedAssignmentsMap,
              ...emp.leaveBalances,
              ...savedForEmp,
            },
          };
        })
      );
    }
  }, [employeeData, balancesResponse]);

  const handleBulkLeaveUpdate = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee for bulk leave update.");
      return;
    }
    setIsBulkUpdateOpen(true);
  };

  const handleBulkUpdateSuccess = (leaveType: string, balanceCount: number) => {
    setEmployees((prev) => {
      const updated = prev.map((emp) => {
        if (selectedIds.includes(emp.id) || selectedIds.includes(emp.employeeId)) {
          return {
            ...emp,
            leaveBalances: {
              ...emp.leaveBalances,
              [leaveType]: balanceCount,
            },
          };
        }
        return emp;
      });

      // Persist leave balances
      const mapToSave: Record<string, Record<string, number | "Not Assigned">> = {};
      updated.forEach((e) => {
        mapToSave[e.id] = e.leaveBalances;
        mapToSave[e.employeeId] = e.leaveBalances;
      });
      saveBalances(mapToSave);

      // Sync leave assignments so Leave Assign page reflects the updated assignment
      const currentAssignments = getSavedAssignments();
      updated.forEach((e) => {
        if (selectedIds.includes(e.id) || selectedIds.includes(e.employeeId)) {
          const empKey = e.id;
          const empCodeKey = e.employeeId;
          const currentEmpAssign = currentAssignments[empKey] || currentAssignments[empCodeKey] || {};
          const isAssigned = typeof balanceCount === "number" && balanceCount >= 0;

          currentAssignments[empKey] = { ...currentEmpAssign, [leaveType]: isAssigned };
          currentAssignments[empCodeKey] = { ...currentEmpAssign, [leaveType]: isAssigned };
        }
      });
      saveAssignments(currentAssignments);

      return updated;
    });
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
          leaveOptions={leaveColumns}
          onSuccess={handleBulkUpdateSuccess}
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
