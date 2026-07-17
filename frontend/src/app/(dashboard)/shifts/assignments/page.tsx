"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  SlidersHorizontal,
  Plus,
  Edit2,
  Trash2,
  ChevronLeft,
  MoreVertical,
  Calendar,
  X,
  UserCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";

interface AssignmentItem {
  id: number;
  employee_id: string;
  name: string;
  department: string;
  designation: string;
  shift_name: string;
  effective_from: string;
  effective_to: string;
  status: "Active" | "Upcoming" | "Expired";
}

const INITIAL_ASSIGNMENTS: AssignmentItem[] = [
  { id: 1, employee_id: "58", name: "Savan Kamuni", department: "Marketing", designation: "marketing", shift_name: "General Shift", effective_from: "01-01-2026", effective_to: "Ongoing", status: "Active" },
  { id: 2, employee_id: "57", name: "Tulsi baladhiya", department: "Marketing", designation: "Graphic Designer", shift_name: "Morning Shift", effective_from: "10-06-2026", effective_to: "Ongoing", status: "Active" },
  { id: 3, employee_id: "56", name: "Hetal Gohil", department: "Marketing", designation: "marketing", shift_name: "General Shift", effective_from: "01-02-2026", effective_to: "Ongoing", status: "Active" },
  { id: 4, employee_id: "55", name: "Mansi Boghra", department: "Developer", designation: "Python", shift_name: "General Shift", effective_from: "15-03-2026", effective_to: "Ongoing", status: "Active" },
  { id: 5, employee_id: "54", name: "Divyesh Pipaliya", department: "Marketing", designation: "marketing", shift_name: "Night Shift", effective_from: "01-07-2026", effective_to: "31-07-2026", status: "Active" },
  { id: 6, employee_id: "53", name: "Pratik raval", department: "Marketing", designation: "marketing", shift_name: "Morning Shift", effective_from: "01-08-2026", effective_to: "Ongoing", status: "Upcoming" },
  { id: 7, employee_id: "52", name: "Krishna Chodvadiya", department: "BDM", designation: "BDM", shift_name: "General Shift", effective_from: "01-01-2025", effective_to: "31-12-2025", status: "Expired" },
];

export default function ShiftAssignmentsPage() {
  const router = useRouter();
  const [assignments, setAssignments] = useState<AssignmentItem[]>(INITIAL_ASSIGNMENTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBranch, setSelectedBranch] = useState("Itcode Infotech");
  const [selectedDept, setSelectedDept] = useState("All");
  const [selectedShift, setSelectedShift] = useState("All");

  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"assign" | "edit">("assign");
  const [selectedAssignmentId, setSelectedAssignmentId] = useState<number | null>(null);

  // Form Fields State
  const [employeeQuery, setEmployeeQuery] = useState("");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");
  const [selectedEmployeeName, setSelectedEmployeeName] = useState("");
  const [shiftName, setShiftName] = useState("General Shift");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [effectiveTo, setEffectiveTo] = useState("");
  const [isOngoing, setIsOngoing] = useState(true);

  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Filtered list
  const filteredAssignments = useMemo(() => {
    let result = [...assignments];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.name.toLowerCase().includes(q) ||
          a.employee_id.includes(q) ||
          a.department.toLowerCase().includes(q)
      );
    }
    if (selectedDept !== "All") {
      result = result.filter((a) => a.department === selectedDept);
    }
    if (selectedShift !== "All") {
      result = result.filter((a) => a.shift_name === selectedShift);
    }
    return result;
  }, [assignments, searchQuery, selectedDept, selectedShift]);

  const handleOpenAssign = () => {
    setDrawerMode("assign");
    setEmployeeQuery("");
    setSelectedEmployeeId("");
    setSelectedEmployeeName("");
    setShiftName("General Shift");
    setEffectiveFrom("");
    setEffectiveTo("");
    setIsOngoing(true);
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (assign: AssignmentItem) => {
    setDrawerMode("edit");
    setSelectedAssignmentId(assign.id);
    setSelectedEmployeeId(assign.employee_id);
    setSelectedEmployeeName(assign.name);
    setShiftName(assign.shift_name);
    
    // Parse Date for inputs
    const fromParts = assign.effective_from.split("-");
    const formattedFrom = fromParts.length === 3 ? `${fromParts[2]}-${fromParts[1]}-${fromParts[0]}` : "";
    setEffectiveFrom(formattedFrom);
    
    if (assign.effective_to === "Ongoing") {
      setIsOngoing(true);
      setEffectiveTo("");
    } else {
      setIsOngoing(false);
      const toParts = assign.effective_to.split("-");
      const formattedTo = toParts.length === 3 ? `${toParts[2]}-${toParts[1]}-${toParts[0]}` : "";
      setEffectiveTo(formattedTo);
    }
    
    setIsDrawerOpen(true);
    setActiveMenuId(null);
  };

  const handleSaveAssignment = (e: React.FormEvent) => {
    e.preventDefault();

    if (drawerMode === "assign" && !selectedEmployeeId) {
      toast.error("Please enter/select a valid Employee ID");
      return;
    }
    if (!effectiveFrom) {
      toast.error("Effective From date is required");
      return;
    }

    const formatDateString = (dateStr: string) => {
      if (!dateStr) return "";
      const parts = dateStr.split("-");
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    };

    const formattedFrom = formatDateString(effectiveFrom);
    const formattedTo = isOngoing ? "Ongoing" : formatDateString(effectiveTo);

    if (drawerMode === "assign") {
      const newId = assignments.length > 0 ? Math.max(...assignments.map((a) => a.id)) + 1 : 1;
      const newAssignment: AssignmentItem = {
        id: newId,
        employee_id: selectedEmployeeId,
        name: selectedEmployeeName || "New Employee",
        department: "Marketing", // Mock department
        designation: "Associate",
        shift_name: shiftName,
        effective_from: formattedFrom,
        effective_to: formattedTo,
        status: "Active",
      };
      setAssignments((prev) => [newAssignment, ...prev]);
      toast.success("Shift assigned successfully.");
    } else {
      setAssignments((prev) =>
        prev.map((a) =>
          a.id === selectedAssignmentId
            ? {
                ...a,
                shift_name: shiftName,
                effective_from: formattedFrom,
                effective_to: formattedTo,
              }
            : a
        )
      );
      toast.success("Shift assignment updated successfully.");
    }
    setIsDrawerOpen(false);
  };

  const handleDeleteAssignment = (id: number) => {
    setAssignments((prev) => prev.filter((a) => a.id !== id));
    toast.success("Shift assignment removed successfully.");
    setActiveMenuId(null);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "shift", action: "read" }}>
      <div className="p-6 space-y-6 bg-slate-50/40 min-h-screen">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-1 text-sm font-semibold text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Manage Shifts</span>
            </button>
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Employee Shift Assignments</h1>
          </div>
        </div>

        {/* Filters and Search toolbar */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-4 rounded-xl shadow-xs flex flex-wrap items-center gap-6">
          <div className="w-full sm:w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search employee..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 w-full"
            />
          </div>

          <div className="flex flex-wrap items-center gap-4 flex-1">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Branch</span>
              <div className="relative">
                <select
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none w-44"
                >
                  <option value="Itcode Infotech">Itcode Infotech</option>
                  <option value="Mumbai Branch">Mumbai Branch</option>
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Department</span>
              <div className="relative">
                <select
                  value={selectedDept}
                  onChange={(e) => setSelectedDept(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none w-40"
                >
                  <option value="All">All Departments</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Developer">Developer</option>
                  <option value="BDM">BDM</option>
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Shift</span>
              <div className="relative">
                <select
                  value={selectedShift}
                  onChange={(e) => setSelectedShift(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none w-44"
                >
                  <option value="All">All Shifts</option>
                  <option value="General Shift">General Shift</option>
                  <option value="Morning Shift">Morning Shift</option>
                  <option value="Night Shift">Night Shift</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setSelectedDept("All");
                setSelectedShift("All");
              }}
              className="gap-1.5 text-xs text-slate-500 border-slate-200 hover:bg-slate-50"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Reset
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenAssign}
              className="gap-1.5 text-xs shadow-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              Assign Shift
            </Button>
          </div>
        </div>

        {/* Table representation */}
        <div className="w-full overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-[#f0f4f9] dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 font-semibold text-xs text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Employee ID</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Employee Name</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Department</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Active Shift</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Effective From</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Effective To</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Status</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-right w-20">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredAssignments.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    No shift assignments found.
                  </td>
                </tr>
              ) : (
                filteredAssignments.map((assign) => (
                  <tr key={assign.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-850 dark:text-slate-200 whitespace-nowrap">
                      {assign.employee_id}
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="p-1 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-450 shrink-0">
                          <UserCheck className="h-4 w-4" />
                        </div>
                        {assign.name}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {assign.department}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={assign.shift_name.includes("Night") ? "destructive" : assign.shift_name.includes("Morning") ? "warning" : "default"}>
                        {assign.shift_name}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-center font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {assign.effective_from}
                    </td>
                    <td className="px-6 py-4 text-center font-medium text-slate-650 dark:text-slate-400 whitespace-nowrap">
                      {assign.effective_to}
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border border-border/40 ${
                          assign.status === "Active"
                            ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border-emerald-500/10"
                            : assign.status === "Upcoming"
                            ? "bg-blue-500/5 text-blue-700 dark:text-blue-400 border-blue-500/10"
                            : "bg-slate-500/5 text-slate-500 dark:text-slate-450 border-slate-500/10"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            assign.status === "Active"
                              ? "bg-emerald-500"
                              : assign.status === "Upcoming"
                              ? "bg-blue-500"
                              : "bg-slate-550"
                          }`}
                        />
                        {assign.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right relative whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(activeMenuId === assign.id ? null : assign.id);
                        }}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md transition-colors text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer focus:outline-none"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                      {activeMenuId === assign.id && (
                        <div className="absolute right-6 top-10 w-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-100">
                          <button
                            onClick={() => handleOpenEdit(assign)}
                            className="w-full text-left px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-850 cursor-pointer flex items-center gap-2"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteAssignment(assign.id)}
                            className="w-full text-left px-3.5 py-2 text-xs font-semibold text-red-650 hover:bg-red-50 dark:hover:bg-red-950/20 cursor-pointer flex items-center gap-2"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-red-550" />
                            Delete
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Drawer: Assign Shift */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            <div className="relative w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
              <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  {drawerMode === "assign" ? "Assign Employee Shift" : "Modify Shift Assignment"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md text-slate-505 hover:text-slate-850 cursor-pointer focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <form onSubmit={handleSaveAssignment} className="space-y-6">
                  {drawerMode === "assign" ? (
                    <div className="space-y-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          Search Employee / Enter ID <span className="text-red-500">*</span>
                        </label>
                        <div className="flex gap-2">
                          <Input
                            value={employeeQuery}
                            onChange={(e) => {
                              setEmployeeQuery(e.target.value);
                              setSelectedEmployeeId(e.target.value);
                            }}
                            placeholder="e.g. 59 or Saveen"
                            className="h-10 text-xs w-full bg-card"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                              if (!employeeQuery.trim()) return;
                              setSelectedEmployeeId(employeeQuery);
                              setSelectedEmployeeName("Simulated Employee Name");
                              toast.success("Employee verified successfully.");
                            }}
                            className="h-10 text-xs text-slate-700"
                          >
                            Verify
                          </Button>
                        </div>
                      </div>

                      {selectedEmployeeId && (
                        <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl space-y-1.5">
                          <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider block">Selected employee info</span>
                          <div className="text-xs font-semibold text-slate-850 dark:text-slate-200">
                            ID: <span className="text-slate-600 dark:text-slate-400">{selectedEmployeeId}</span>
                          </div>
                          <div className="text-xs font-semibold text-slate-850 dark:text-slate-200">
                            Name: <span className="text-slate-600 dark:text-slate-400">{selectedEmployeeName || "Not verified"}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-1.5">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Employee Details</span>
                      <div className="text-xs font-semibold text-slate-850 dark:text-slate-250">
                        Employee ID: <span className="text-slate-600 dark:text-slate-400">{selectedEmployeeId}</span>
                      </div>
                      <div className="text-xs font-semibold text-slate-850 dark:text-slate-250">
                        Employee Name: <span className="text-slate-600 dark:text-slate-400">{selectedEmployeeName}</span>
                      </div>
                    </div>
                  )}

                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Choose Shift template</label>
                      <select
                        value={shiftName}
                        onChange={(e) => setShiftName(e.target.value)}
                        className="w-full rounded-md border border-input bg-card px-3 h-10 text-xs focus:ring-2 focus:ring-ring"
                      >
                        <option value="General Shift">General Shift (09:00 AM - 06:00 PM)</option>
                        <option value="Morning Shift">Morning Shift (06:00 AM - 02:00 PM)</option>
                        <option value="Night Shift">Night Shift (10:00 PM - 06:00 AM)</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          Effective From <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="date"
                          value={effectiveFrom}
                          onChange={(e) => setEffectiveFrom(e.target.value)}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Effective To</label>
                        <Input
                          type="date"
                          value={effectiveTo}
                          onChange={(e) => {
                            setEffectiveTo(e.target.value);
                            setIsOngoing(false);
                          }}
                          disabled={isOngoing}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-300">
                        <input
                          type="checkbox"
                          checked={isOngoing}
                          onChange={(e) => {
                            setIsOngoing(e.target.checked);
                            if (e.target.checked) setEffectiveTo("");
                          }}
                          className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer"
                        />
                        Mark as ongoing (Indefinite period)
                      </label>
                    </div>
                  </div>

                  <button type="submit" className="hidden" id="drawer-submit-btn" />
                </form>
              </div>

              <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-end gap-2.5">
                <Button variant="outline" size="sm" onClick={() => setIsDrawerOpen(false)} className="text-xs">
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => document.getElementById("drawer-submit-btn")?.click()}
                  className="text-xs shadow-xs"
                >
                  {drawerMode === "assign" ? "Confirm Assignment" : "Update Assignment"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
