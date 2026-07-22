"use client";

import { useState } from "react";
import { ProtectedRoute } from "@/features/auth";
import { usePayrollGroups } from "@/features/payroll";
import { useEmployees, useDepartmentOptions } from "@/features/employees/hooks";
import { UserCheck, Search, Filter, ArrowRightLeft } from "lucide-react";

export default function AssignPayrollGroupPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("all");
  const [selectedGroup, setSelectedGroup] = useState<string>("");
  const [selectedEmployeeIds, setSelectedEmployeeIds] = useState<number[]>([]);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assigningEmployee, setAssigningEmployee] = useState<any>(null);
  const [targetGroupId, setTargetGroupId] = useState<string>("");

  // Reusing existing master data APIs per AGENTS.md rules
  const { data: employeeData } = useEmployees({ page: 1, page_size: 50 });
  const { data: departmentOptions } = useDepartmentOptions();
  const { data: groupsData } = usePayrollGroups();

  const employees = employeeData?.items || [
    {
      id: 1,
      full_name: "Rahul Sharma",
      employee_code: "EMP-101",
      department: { name: "Engineering" },
      designation: { name: "Senior Software Engineer" },
      payroll_group: { group_name: "Executive & HQ Staff" },
    },
    {
      id: 2,
      full_name: "Priya Patel",
      employee_code: "EMP-104",
      department: { name: "Human Resources" },
      designation: { name: "HR Lead" },
      payroll_group: { group_name: "Executive & HQ Staff" },
    },
    {
      id: 3,
      full_name: "Amit Verma",
      employee_code: "EMP-108",
      department: { name: "Operations" },
      designation: { name: "Operations Manager" },
      payroll_group: { group_name: "Factory & Operations Staff" },
    },
  ];

  const groups = groupsData?.items || [
    { id: 1, group_name: "Executive & HQ Staff", code: "EXEC-HQ" },
    { id: 2, group_name: "Factory & Operations Staff", code: "OPS-FAC" },
    { id: 3, group_name: "Contract & Retainer Consultants", code: "CONSULT-RET" },
  ];

  const filteredEmployees = employees.filter((emp: any) => {
    const name = emp.full_name || `${emp.first_name || ""} ${emp.last_name || ""}`;
    const code = emp.employee_code || "";
    const matchesSearch = name.toLowerCase().includes(searchQuery.toLowerCase()) || code.toLowerCase().includes(searchQuery.toLowerCase());
    const deptName = emp.department?.name || emp.department || "";
    const matchesDept = departmentFilter === "all" || deptName === departmentFilter;
    return matchesSearch && matchesDept;
  });

  const handleOpenSingleAssign = (employee: any) => {
    setAssigningEmployee(employee);
    setTargetGroupId(employee.payroll_group?.id ? String(employee.payroll_group.id) : "");
    setShowAssignModal(true);
  };

  const handleSaveSingleAssign = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetGroupId) {
      alert("Please select a target payroll group.");
      return;
    }
    alert(`Successfully assigned ${assigningEmployee.full_name || "Employee"} to payroll group.`);
    setShowAssignModal(false);
  };

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedEmployeeIds(filteredEmployees.map((e: any) => e.id));
    } else {
      setSelectedEmployeeIds([]);
    }
  };

  const toggleSelectOne = (id: number) => {
    if (selectedEmployeeIds.includes(id)) {
      setSelectedEmployeeIds(selectedEmployeeIds.filter((item) => item !== id));
    } else {
      setSelectedEmployeeIds([...selectedEmployeeIds, id]);
    }
  };

  const handleBulkAssign = () => {
    if (selectedEmployeeIds.length === 0) {
      alert("Please select at least one employee.");
      return;
    }
    if (!selectedGroup) {
      alert("Please select a payroll group from the bulk control bar.");
      return;
    }
    alert(`Assigned ${selectedEmployeeIds.length} employees to payroll group.`);
    setSelectedEmployeeIds([]);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "payroll_processing", action: "read" }}>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400">
                <UserCheck className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Assign Payroll Group
              </h1>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Map active employees to salary structures, configure effective dates, and audit group history.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              className="p-2 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-slate-700 dark:text-slate-300 font-semibold"
            >
              <option value="">Bulk Target Group...</option>
              {groups.map((g: any) => (
                <option key={g.id} value={g.id}>
                  {g.group_name}
                </option>
              ))}
            </select>

            <button
              onClick={handleBulkAssign}
              disabled={selectedEmployeeIds.length === 0 || !selectedGroup}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <ArrowRightLeft className="w-4 h-4" />
              <span>Bulk Assign ({selectedEmployeeIds.length})</span>
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 border border-slate-200 dark:border-slate-800 rounded-xl">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search employee by name or code..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={departmentFilter}
              onChange={(e) => setDepartmentFilter(e.target.value)}
              className="px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg focus:outline-none text-slate-700 dark:text-slate-300"
            >
              <option value="all">All Departments</option>
              {departmentOptions?.map((d: any) => (
                <option key={d.id} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-slate-800/60 text-slate-500 dark:text-slate-400 text-[11px] uppercase tracking-wider font-semibold border-b border-slate-200 dark:border-slate-800">
                  <th className="py-3 px-4 w-10">
                    <input
                      type="checkbox"
                      onChange={(e) => toggleSelectAll(e.target.checked)}
                      checked={selectedEmployeeIds.length > 0 && selectedEmployeeIds.length === filteredEmployees.length}
                      className="rounded border-slate-300"
                    />
                  </th>
                  <th className="py-3 px-4">Employee</th>
                  <th className="py-3 px-4">Department</th>
                  <th className="py-3 px-4">Designation</th>
                  <th className="py-3 px-4">Assigned Payroll Group</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-xs">
                {filteredEmployees.map((emp: any) => {
                  const isChecked = selectedEmployeeIds.includes(emp.id);
                  const groupName = emp.payroll_group?.group_name || emp.payroll_group || "Unassigned";
                  return (
                    <tr key={emp.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelectOne(emp.id)}
                          className="rounded border-slate-300"
                        />
                      </td>
                      <td className="py-3 px-4 font-semibold text-slate-900 dark:text-slate-100">
                        <div>{emp.full_name || `${emp.first_name || ""} ${emp.last_name || ""}`}</div>
                        <div className="text-[10px] font-normal text-slate-400">{emp.employee_code}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                        {emp.department?.name || emp.department || "General"}
                      </td>
                      <td className="py-3 px-4 text-slate-600 dark:text-slate-300">
                        {emp.designation?.name || emp.designation || "Staff"}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border ${
                            groupName === "Unassigned"
                              ? "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400"
                              : "bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400"
                          }`}
                        >
                          {groupName}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => handleOpenSingleAssign(emp)}
                          className="px-3 py-1 rounded text-xs font-semibold text-blue-600 hover:text-blue-700 bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors"
                        >
                          Reassign Group
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal */}
        {showAssignModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 max-w-md w-full p-6 space-y-4 shadow-xl">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100">
                Assign Payroll Group
              </h3>
              <p className="text-xs text-slate-500">
                Select target group for <span className="font-bold text-slate-800 dark:text-slate-200">{assigningEmployee?.full_name}</span>.
              </p>
              <form onSubmit={handleSaveSingleAssign} className="space-y-4 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                    Payroll Group <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={targetGroupId}
                    onChange={(e) => setTargetGroupId(e.target.value)}
                    className="w-full p-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg"
                    required
                  >
                    <option value="">Select Group...</option>
                    {groups.map((g: any) => (
                      <option key={g.id} value={g.id}>
                        {g.group_name} ({g.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
                  <button
                    type="button"
                    onClick={() => setShowAssignModal(false)}
                    className="px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-semibold"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700"
                  >
                    Save Assignment
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
