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
  Settings,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";

interface WeekOffItem {
  id: number;
  employee_id: string;
  name: string;
  department: string;
  designation: string;
  days: string[];
  effective_date: string;
  rules_summary: string;
}

const INITIAL_WEEKOFFS: WeekOffItem[] = [
  { id: 1, employee_id: "58", name: "Savan Kamuni", department: "Marketing", designation: "marketing", days: ["Sunday"], effective_date: "01-01-2026", rules_summary: "Every Sunday" },
  { id: 2, employee_id: "57", name: "Tulsi baladhiya", department: "Marketing", designation: "Graphic Designer", days: ["Sunday"], effective_date: "10-06-2026", rules_summary: "Every Sunday" },
  { id: 3, employee_id: "56", name: "Hetal Gohil", department: "Marketing", designation: "marketing", days: ["Sunday", "Saturday"], effective_date: "01-02-2026", rules_summary: "Every Sunday & 2nd/4th Saturday" },
  { id: 4, employee_id: "55", name: "Mansi Boghra", department: "Developer", designation: "Python", days: ["Sunday", "Saturday"], effective_date: "15-03-2026", rules_summary: "Every Saturday & Sunday" },
  { id: 5, employee_id: "54", name: "Divyesh Pipaliya", department: "Marketing", designation: "marketing", days: ["Sunday"], effective_date: "01-07-2026", rules_summary: "Every Sunday" },
  { id: 6, employee_id: "53", name: "Pratik raval", department: "Marketing", designation: "marketing", days: ["Sunday"], effective_date: "01-08-2026", rules_summary: "Every Sunday" },
];

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export default function WeekOffPage() {
  const router = useRouter();
  const [weekoffs, setWeekoffs] = useState<WeekOffItem[]>(INITIAL_WEEKOFFS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedBranch, setSelectedBranch] = useState("Itcode Infotech");
  const [selectedDept, setSelectedDept] = useState("All");

  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"configure" | "edit">("configure");
  const [selectedWeekoffId, setSelectedWeekoffId] = useState<number | null>(null);

  // Form Fields State
  const [employeeQuery, setEmployeeQuery] = useState("");
  const [selectedEmployeeId, setSelectedEmployeeId] = useState("");
  const [selectedEmployeeName, setSelectedEmployeeName] = useState("");
  const [selectedDays, setSelectedDays] = useState<string[]>(["Sunday"]);
  const [ruleType, setRuleType] = useState("All Weeks");
  const [effectiveDate, setEffectiveDate] = useState("");

  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Filtered list
  const filteredWeekoffs = useMemo(() => {
    let result = [...weekoffs];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (w) =>
          w.name.toLowerCase().includes(q) ||
          w.employee_id.includes(q) ||
          w.department.toLowerCase().includes(q)
      );
    }
    if (selectedDept !== "All") {
      result = result.filter((w) => w.department === selectedDept);
    }
    return result;
  }, [weekoffs, searchQuery, selectedDept]);

  const handleOpenConfigure = () => {
    setDrawerMode("configure");
    setEmployeeQuery("");
    setSelectedEmployeeId("");
    setSelectedEmployeeName("");
    setSelectedDays(["Sunday"]);
    setRuleType("All Weeks");
    setEffectiveDate("");
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (w: WeekOffItem) => {
    setDrawerMode("edit");
    setSelectedWeekoffId(w.id);
    setSelectedEmployeeId(w.employee_id);
    setSelectedEmployeeName(w.name);
    setSelectedDays([...w.days]);
    
    if (w.rules_summary.includes("2nd/4th")) {
      setRuleType("2nd & 4th Weeks");
    } else {
      setRuleType("All Weeks");
    }

    const parts = w.effective_date.split("-");
    const formattedDate = parts.length === 3 ? `${parts[2]}-${parts[1]}-${parts[0]}` : "";
    setEffectiveDate(formattedDate);
    
    setIsDrawerOpen(true);
    setActiveMenuId(null);
  };

  const handleToggleDay = (day: string) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  const handleSaveWeekoff = (e: React.FormEvent) => {
    e.preventDefault();

    if (drawerMode === "configure" && !selectedEmployeeId) {
      toast.error("Please enter/select a valid Employee ID");
      return;
    }
    if (selectedDays.length === 0) {
      toast.error("Please select at least one weekly off day");
      return;
    }
    if (!effectiveDate) {
      toast.error("Effective Date is required");
      return;
    }

    const formatDateString = (dateStr: string) => {
      if (!dateStr) return "";
      const parts = dateStr.split("-");
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    };

    const formattedDate = formatDateString(effectiveDate);
    const summary = ruleType === "All Weeks" ? `Every ${selectedDays.join(" & ")}` : `Every Sunday & 2nd/4th ${selectedDays.filter((d) => d !== "Sunday").join(" & ")}`;

    if (drawerMode === "configure") {
      const newId = weekoffs.length > 0 ? Math.max(...weekoffs.map((w) => w.id)) + 1 : 1;
      const newWeekoff: WeekOffItem = {
        id: newId,
        employee_id: selectedEmployeeId,
        name: selectedEmployeeName || "New Employee",
        department: "Marketing", // Mock department
        designation: "Associate",
        days: selectedDays,
        effective_date: formattedDate,
        rules_summary: summary,
      };
      setWeekoffs((prev) => [newWeekoff, ...prev]);
      toast.success("Week Off configured successfully.");
    } else {
      setWeekoffs((prev) =>
        prev.map((w) =>
          w.id === selectedWeekoffId
            ? {
                ...w,
                days: selectedDays,
                effective_date: formattedDate,
                rules_summary: summary,
              }
            : w
        )
      );
      toast.success("Week Off configuration updated successfully.");
    }
    setIsDrawerOpen(false);
  };

  const handleDeleteWeekoff = (id: number) => {
    setWeekoffs((prev) => prev.filter((w) => w.id !== id));
    toast.success("Week Off configuration removed.");
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
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Weekly Off Configurations</h1>
          </div>
        </div>

        {/* Filters and Search toolbar */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-4 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-[280px]">
            <div className="relative w-full sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search employee..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 w-full"
              />
            </div>

            <div className="flex items-center gap-4">
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
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery("");
                setSelectedDept("All");
              }}
              className="gap-1.5 text-xs text-slate-500 border-slate-200 hover:bg-slate-50"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Reset
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenConfigure}
              className="gap-1.5 text-xs shadow-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              Configure Week Off
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
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Designation</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Weekly Off Days</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Effective Date</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Rule Summary</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-right w-20">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredWeekoffs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    No weekly off configurations found.
                  </td>
                </tr>
              ) : (
                filteredWeekoffs.map((w) => (
                  <tr key={w.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-850 dark:text-slate-200 whitespace-nowrap">
                      {w.employee_id}
                    </td>
                    <td className="px-6 py-4 font-semibold text-slate-850 dark:text-slate-200 whitespace-nowrap">
                      {w.name}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {w.department}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {w.designation}
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <div className="flex justify-center gap-1">
                        {w.days.map((d) => (
                          <Badge key={d} variant="warning">
                            {d}
                          </Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center font-medium text-slate-650 dark:text-slate-400 whitespace-nowrap">
                      {w.effective_date}
                    </td>
                    <td className="px-6 py-4 text-slate-600 dark:text-slate-450 font-medium">
                      {w.rules_summary}
                    </td>
                    <td className="px-6 py-4 text-right relative whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(activeMenuId === w.id ? null : w.id);
                        }}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md transition-colors text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer focus:outline-none"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                      {activeMenuId === w.id && (
                        <div className="absolute right-6 top-10 w-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-100">
                          <button
                            onClick={() => handleOpenEdit(w)}
                            className="w-full text-left px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-850 cursor-pointer flex items-center gap-2"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteWeekoff(w.id)}
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

        {/* Drawer: Configure Week Off */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            <div className="relative w-full max-w-xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
              <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  {drawerMode === "configure" ? "Configure Weekly Off" : "Modify Week Off Configuration"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md text-slate-505 hover:text-slate-850 cursor-pointer focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <form onSubmit={handleSaveWeekoff} className="space-y-6">
                  {drawerMode === "configure" ? (
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
                            placeholder="e.g. 58 or Savan"
                            className="h-10 text-xs w-full bg-card"
                          />
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => {
                              if (!employeeQuery.trim()) return;
                              setSelectedEmployeeId(employeeQuery);
                              setSelectedEmployeeName("Simulated Employee Name");
                              toast.success("Employee verified.");
                            }}
                            className="h-10 text-xs text-slate-700"
                          >
                            Verify
                          </Button>
                        </div>
                      </div>

                      {selectedEmployeeId && (
                        <div className="p-3 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl space-y-1.5">
                          <span className="text-[10px] font-bold text-blue-500 uppercase tracking-wider block">Verified employee</span>
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
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Employee</span>
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
                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 block mb-1">
                        Select Off Day(s) <span className="text-red-500">*</span>
                      </label>
                      <div className="flex flex-wrap gap-2">
                        {WEEKDAYS.map((day) => {
                          const isChecked = selectedDays.includes(day);
                          return (
                            <button
                              key={day}
                              type="button"
                              onClick={() => handleToggleDay(day)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-semibold cursor-pointer border transition-colors ${
                                isChecked
                                  ? "bg-amber-500/10 text-amber-700 border-amber-500/30"
                                  : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                              }`}
                            >
                              {day}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Rule Pattern</label>
                        <select
                          value={ruleType}
                          onChange={(e) => setRuleType(e.target.value)}
                          className="w-full rounded-md border border-input bg-card px-3 h-10 text-xs focus:ring-2 focus:ring-ring"
                        >
                          <option value="All Weeks">Every Week (All Weeks)</option>
                          <option value="2nd & 4th Weeks">Alternate Weeks (2nd & 4th)</option>
                          <option value="1st, 3rd & 5th Weeks">Odd Weeks (1st, 3rd, 5th)</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                          Effective From <span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="date"
                          value={effectiveDate}
                          onChange={(e) => setEffectiveDate(e.target.value)}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>
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
                  {drawerMode === "configure" ? "Save Configuration" : "Update Configuration"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
