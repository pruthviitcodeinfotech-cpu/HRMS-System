"use client";

import { useState, useMemo, useEffect } from "react";
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
} from "@/features/leaves";

const STORAGE_KEY = "hrms_leave_assignments";

const getSavedAssignments = (): Record<string, Record<string, boolean>> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveAssignments = (data: Record<string, Record<string, boolean>>) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.error("Failed to save assignments", err);
  }
};

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

  // Initialize state from localStorage persistence + fallback mock data
  const [employees, setEmployees] = useState<LeaveAssignEmployee[]>(() => {
    const savedMap = getSavedAssignments();
    return LEAVE_ASSIGN_EMPLOYEES_DATA.map((emp) => {
      const savedForEmp = savedMap[emp.id] || savedMap[emp.employeeId] || {};
      return {
        ...emp,
        leaveAssignments: {
          ...emp.leaveAssignments,
          ...savedForEmp,
        },
      };
    });
  });

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [isBulkAssignOpen, setIsBulkAssignOpen] = useState<boolean>(false);

  // Fetch real employees and balances from backend
  const { data: employeeData, isLoading: isEmployeesLoading } = useEmployees({ page: 1, page_size: 100 });
  const { data: leaveTypesResponse, isLoading: isLeavesLoading } = useLeaveTypes({ page_size: 100 });
  const { data: balancesResponse } = useLeaveBalances({ page_size: 500 });

  const leaveTypes = useMemo(() => {
    if (leaveTypesResponse?.items && leaveTypesResponse.items.length > 0) {
      return leaveTypesResponse.items.map((lt) => lt.name);
    }
    return ["Comp Off"];
  }, [leaveTypesResponse]);

  // Sync live backend employees & saved assignments
  useEffect(() => {
    const savedMap = getSavedAssignments();
    const serverBalances = balancesResponse?.items || [];

    if (employeeData?.items && employeeData.items.length > 0) {
      const liveRows: LeaveAssignEmployee[] = employeeData.items.map((emp) => {
        const empIdStr = String(emp.employee_id);
        const empCodeStr = emp.employee_code || empIdStr;
        const savedForEmp = savedMap[empIdStr] || savedMap[empCodeStr] || {};

        // Merge any server balances
        const empBalances = serverBalances.filter((b) => b.employee_id === emp.employee_id);
        const serverAssignMap: Record<string, boolean> = {};
        empBalances.forEach((b) => {
          if (b.leave_type?.name) {
            serverAssignMap[b.leave_type.name] = b.closing_balance > 0 || b.allocated > 0;
          }
        });

        return {
          id: empIdStr,
          employeeId: empCodeStr,
          name: emp.employee_name,
          department: emp.department_name || "-",
          designation: emp.designation_name || "-",
          leaveAssignments: {
            ...serverAssignMap,
            ...savedForEmp,
          },
          employeeSummary: emp,
        };
      });
      setEmployees(liveRows);
    } else {
      // Re-hydrate mock rows with saved localStorage assignments
      setEmployees((prev) =>
        prev.map((emp) => {
          const savedForEmp = savedMap[emp.id] || savedMap[emp.employeeId] || {};
          return {
            ...emp,
            leaveAssignments: {
              ...emp.leaveAssignments,
              ...savedForEmp,
            },
          };
        })
      );
    }
  }, [employeeData, balancesResponse]);

const getSavedBalances = (): Record<string, Record<string, number | "Not Assigned">> => {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem("hrms_leave_balances");
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
};

const saveBalances = (data: Record<string, Record<string, number | "Not Assigned">>) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem("hrms_leave_balances", JSON.stringify(data));
  } catch (err) {
    console.error("Failed to save balances", err);
  }
};

  const handleToggleAssignment = (employeeId: string, leaveType: string) => {
    setEmployees((prev) => {
      const updated = prev.map((emp) => {
        if (emp.id === employeeId || emp.employeeId === employeeId) {
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
      });

      // Persist to localStorage
      const mapToSave: Record<string, Record<string, boolean>> = {};
      updated.forEach((e) => {
        mapToSave[e.id] = e.leaveAssignments;
        mapToSave[e.employeeId] = e.leaveAssignments;
      });
      saveAssignments(mapToSave);

      // Sync leave balances so Leave Balance page reflects assigned leaves
      const currentBalances = getSavedBalances();
      updated.forEach((e) => {
        if (e.id === employeeId || e.employeeId === employeeId) {
          const empKey = e.id;
          const empCodeKey = e.employeeId;
          const currentEmpBal = currentBalances[empKey] || currentBalances[empCodeKey] || {};
          const isAssigned = e.leaveAssignments[leaveType];

          let newBalVal: number | "Not Assigned";
          if (isAssigned) {
            newBalVal = typeof currentEmpBal[leaveType] === "number" ? currentEmpBal[leaveType] : 0;
          } else {
            newBalVal = "Not Assigned";
          }

          currentBalances[empKey] = { ...currentEmpBal, [leaveType]: newBalVal };
          currentBalances[empCodeKey] = { ...currentEmpBal, [leaveType]: newBalVal };
        }
      });
      saveBalances(currentBalances);

      return updated;
    });
  };

  const handleBulkAssign = () => {
    if (selectedIds.length === 0) {
      toast.error("Please select at least one employee to assign leave.");
      return;
    }
    setIsBulkAssignOpen(true);
  };

  const handleBulkAssignSuccess = (leaveType: string, isAssigned: boolean) => {
    setEmployees((prev) => {
      const updated = prev.map((emp) => {
        if (selectedIds.includes(emp.id) || selectedIds.includes(emp.employeeId)) {
          return {
            ...emp,
            leaveAssignments: {
              ...emp.leaveAssignments,
              [leaveType]: isAssigned,
            },
          };
        }
        return emp;
      });

      // Persist to localStorage
      const mapToSave: Record<string, Record<string, boolean>> = {};
      updated.forEach((e) => {
        mapToSave[e.id] = e.leaveAssignments;
        mapToSave[e.employeeId] = e.leaveAssignments;
      });
      saveAssignments(mapToSave);

      // Sync leave balances
      const currentBalances = getSavedBalances();
      updated.forEach((e) => {
        if (selectedIds.includes(e.id) || selectedIds.includes(e.employeeId)) {
          const empKey = e.id;
          const empCodeKey = e.employeeId;
          const currentEmpBal = currentBalances[empKey] || currentBalances[empCodeKey] || {};

          let newBalVal: number | "Not Assigned";
          if (isAssigned) {
            newBalVal = typeof currentEmpBal[leaveType] === "number" ? currentEmpBal[leaveType] : 0;
          } else {
            newBalVal = "Not Assigned";
          }

          currentBalances[empKey] = { ...currentEmpBal, [leaveType]: newBalVal };
          currentBalances[empCodeKey] = { ...currentEmpBal, [leaveType]: newBalVal };
        }
      });
      saveBalances(currentBalances);

      return updated;
    });
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
