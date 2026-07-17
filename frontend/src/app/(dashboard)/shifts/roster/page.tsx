"use client";

import React, { useState, useMemo } from "react";
import {
  Search,
  ChevronLeft,
  ChevronRight,
  Calendar as CalendarIcon,
  Sparkles,
  X,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";

interface RosterRow {
  employee_id: string;
  name: string;
  department: string;
  schedule: Record<string, string>; // date string (YYYY-MM-DD) -> shift code (GS, MS, NS, WO)
}

const SHIFT_MAP: Record<string, { label: string; color: string; timing: string }> = {
  GS: { label: "General Shift", color: "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200/50", timing: "09:00 - 18:00" },
  MS: { label: "Morning Shift", color: "bg-amber-500/10 text-amber-700 dark:text-amber-450 border-amber-200/50", timing: "06:00 - 14:00" },
  NS: { label: "Night Shift", color: "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-200/50", timing: "22:00 - 06:00" },
  WO: { label: "Week Off", color: "bg-slate-100 text-slate-650 dark:bg-slate-800 dark:text-slate-400 border-slate-200/40", timing: "Rest Day" },
};

const INITIAL_ROSTER_ROWS: RosterRow[] = [
  {
    employee_id: "58",
    name: "Savan Kamuni",
    department: "Marketing",
    schedule: {
      "2026-07-13": "GS",
      "2026-07-14": "GS",
      "2026-07-15": "GS",
      "2026-07-16": "GS",
      "2026-07-17": "GS",
      "2026-07-18": "MS",
      "2026-07-19": "WO",
    },
  },
  {
    employee_id: "57",
    name: "Tulsi baladhiya",
    department: "Marketing",
    schedule: {
      "2026-07-13": "MS",
      "2026-07-14": "MS",
      "2026-07-15": "MS",
      "2026-07-16": "MS",
      "2026-07-17": "MS",
      "2026-07-18": "WO",
      "2026-07-19": "WO",
    },
  },
  {
    employee_id: "56",
    name: "Hetal Gohil",
    department: "Marketing",
    schedule: {
      "2026-07-13": "GS",
      "2026-07-14": "GS",
      "2026-07-15": "WO",
      "2026-07-16": "GS",
      "2026-07-17": "GS",
      "2026-07-18": "GS",
      "2026-07-19": "WO",
    },
  },
  {
    employee_id: "55",
    name: "Mansi Boghra",
    department: "Developer",
    schedule: {
      "2026-07-13": "GS",
      "2026-07-14": "GS",
      "2026-07-15": "GS",
      "2026-07-16": "GS",
      "2026-07-17": "GS",
      "2026-07-18": "GS",
      "2026-07-19": "WO",
    },
  },
  {
    employee_id: "54",
    name: "Divyesh Pipaliya",
    department: "Marketing",
    schedule: {
      "2026-07-13": "NS",
      "2026-07-14": "NS",
      "2026-07-15": "NS",
      "2026-07-16": "NS",
      "2026-07-17": "NS",
      "2026-07-18": "WO",
      "2026-07-19": "WO",
    },
  },
];

const WEEK_DATES = [
  { label: "Mon 13", dateStr: "2026-07-13" },
  { label: "Tue 14", dateStr: "2026-07-14" },
  { label: "Wed 15", dateStr: "2026-07-15" },
  { label: "Thu 16", dateStr: "2026-07-16" },
  { label: "Fri 17", dateStr: "2026-07-17" },
  { label: "Sat 18", dateStr: "2026-07-18" },
  { label: "Sun 19", dateStr: "2026-07-19" },
];

export default function RosterPage() {
  const router = useRouter();
  const [rows, setRows] = useState<RosterRow[]>(INITIAL_ROSTER_ROWS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedDept, setSelectedDept] = useState("All");

  // Selection cell modal/popover state
  const [activeCell, setActiveCell] = useState<{ empId: string; dateStr: string } | null>(null);

  // Rotation generator drawer state
  const [isGeneratorOpen, setIsGeneratorOpen] = useState(false);
  const [rotationShift, setRotationShift] = useState("GS");
  const [rotationEmployees, setRotationEmployees] = useState("All");
  const [startDate, setStartDate] = useState("2026-07-13");
  const [endDate, setEndDate] = useState("2026-07-19");

  // Filtered rows
  const filteredRows = useMemo(() => {
    let result = [...rows];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          r.employee_id.includes(q) ||
          r.department.toLowerCase().includes(q)
      );
    }
    if (selectedDept !== "All") {
      result = result.filter((r) => r.department === selectedDept);
    }
    return result;
  }, [rows, searchQuery, selectedDept]);

  const handleCellClick = (empId: string, dateStr: string) => {
    setActiveCell({ empId, dateStr });
  };

  const handleShiftSelect = (code: string) => {
    if (!activeCell) return;
    const { empId, dateStr } = activeCell;
    setRows((prev) =>
      prev.map((r) => {
        if (r.employee_id === empId) {
          return {
            ...r,
            schedule: {
              ...r.schedule,
              [dateStr]: code,
            },
          };
        }
        return r;
      })
    );
    toast.success("Roster entry updated.");
    setActiveCell(null);
  };

  const handleGenerateRotation = (e: React.FormEvent) => {
    e.preventDefault();
    // Simulate generation
    setRows((prev) =>
      prev.map((r) => {
        const schedule = { ...r.schedule };
        WEEK_DATES.forEach((wd) => {
          // Keep Sundays as Week Off
          if (wd.label.includes("Sun")) {
            schedule[wd.dateStr] = "WO";
          } else {
            schedule[wd.dateStr] = rotationShift;
          }
        });
        return { ...r, schedule };
      })
    );
    toast.success(`Generated rotation shift ${rotationShift} over the specified horizon.`);
    setIsGeneratorOpen(false);
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
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Weekly Shift Roster</h1>
          </div>
        </div>

        {/* Filters toolbar */}
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
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
              <button className="p-1.5 bg-slate-50 hover:bg-slate-100 border-r border-slate-200 dark:border-slate-800 text-slate-600">
                <ChevronLeft className="h-4 w-4" />
              </button>
              <div className="px-3 py-1.5 text-xs font-bold text-slate-700 bg-white flex items-center gap-1">
                <CalendarIcon className="h-3.5 w-3.5 text-slate-400" />
                <span>13-Jul-2026 to 19-Jul-2026</span>
              </div>
              <button className="p-1.5 bg-slate-50 hover:bg-slate-100 border-l border-slate-200 dark:border-slate-800 text-slate-600">
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsGeneratorOpen(true)}
              className="gap-1.5 text-xs text-blue-600 border-blue-100 hover:bg-blue-50/50 bg-blue-50/20"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Auto Rotation
            </Button>
          </div>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap gap-4 items-center px-2 py-1 bg-white/50 dark:bg-slate-900/50 rounded-lg text-xs font-semibold text-slate-600 dark:text-slate-400 border border-slate-100 dark:border-slate-850">
          <span>Shift Legend:</span>
          {Object.entries(SHIFT_MAP).map(([code, info]) => (
            <div key={code} className="flex items-center gap-1.5">
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold border ${info.color}`}>{code}</span>
              <span className="text-slate-500 text-[11px]">{info.label} ({info.timing})</span>
            </div>
          ))}
        </div>

        {/* Grid Roster Table */}
        <div className="w-full overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs relative">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-[#f0f4f9] dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 font-semibold text-xs text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 w-16">ID</th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 w-44">Employee Name</th>
                {WEEK_DATES.map((wd) => (
                  <th key={wd.dateStr} className="px-3 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center w-28 border-l border-slate-200 dark:border-slate-800">
                    {wd.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredRows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-6 py-12 text-center text-slate-500">
                    No employee rows found.
                  </td>
                </tr>
              ) : (
                filteredRows.map((row) => (
                  <tr key={row.employee_id} className="hover:bg-slate-50/30 dark:hover:bg-slate-800/10 transition-colors">
                    <td className="px-4 py-4 font-semibold text-slate-650 dark:text-slate-400">
                      {row.employee_id}
                    </td>
                    <td className="px-4 py-4 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      <div>
                        <div>{row.name}</div>
                        <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mt-0.5">{row.department}</div>
                      </div>
                    </td>
                    {WEEK_DATES.map((wd) => {
                      const code = row.schedule[wd.dateStr] || "WO";
                      const info = SHIFT_MAP[code];
                      const isCellSelected = activeCell?.empId === row.employee_id && activeCell?.dateStr === wd.dateStr;

                      return (
                        <td
                          key={wd.dateStr}
                          onClick={() => handleCellClick(row.employee_id, wd.dateStr)}
                          className={`px-3 py-3 text-center border-l border-slate-100 dark:border-slate-800/60 cursor-pointer transition-all hover:bg-slate-50 dark:hover:bg-slate-800/40 relative align-middle ${
                            isCellSelected ? "bg-blue-50/50 dark:bg-blue-950/20 ring-1 ring-blue-500/50" : ""
                          }`}
                        >
                          <div className="flex flex-col items-center justify-center">
                            <span className={`px-2.5 py-1 rounded text-xs font-bold border shadow-3xs select-none ${info.color}`}>
                              {code}
                            </span>
                            <span className="text-[9px] font-semibold text-slate-400 mt-1">{info.timing}</span>
                          </div>

                          {/* Quick selection popover */}
                          {isCellSelected && (
                            <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3.5 py-1 text-left border-b border-slate-100 dark:border-slate-850 pb-1 mb-1">
                                Change Shift
                              </div>
                              {Object.entries(SHIFT_MAP).map(([scode, sinfo]) => (
                                <button
                                  key={scode}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleShiftSelect(scode);
                                  }}
                                  className="w-full text-left px-3.5 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer flex items-center justify-between"
                                >
                                  <span>{sinfo.label} ({scode})</span>
                                  {code === scode && <Check className="h-3 w-3 text-blue-600" />}
                                </button>
                              ))}
                            </div>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Generator Drawer */}
        {isGeneratorOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => setIsGeneratorOpen(false)}
            />
            <div className="relative w-full max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
              <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  <Sparkles className="h-4 w-4 text-blue-600 inline mr-2" />
                  Auto Shift Rotation Generator
                </h3>
                <button
                  onClick={() => setIsGeneratorOpen(false)}
                  className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-500 hover:text-slate-800 cursor-pointer focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <form onSubmit={handleGenerateRotation} className="space-y-6">
                  <div className="p-3.5 bg-blue-50/45 dark:bg-blue-950/15 border border-blue-100 dark:border-blue-900/50 rounded-xl">
                    <p className="text-xs text-blue-750 dark:text-blue-400 font-semibold leading-relaxed">
                      Use the generator to apply a specific shift rules pattern or shift template across multiple employees over a designated period. Sundays will automatically resolve to Weekly Off (WO).
                    </p>
                  </div>

                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Target Shift</label>
                      <select
                        value={rotationShift}
                        onChange={(e) => setRotationShift(e.target.value)}
                        className="w-full rounded-md border border-input bg-card px-3 h-10 text-xs focus:ring-2 focus:ring-ring"
                      >
                        <option value="GS">General Shift (GS)</option>
                        <option value="MS">Morning Shift (MS)</option>
                        <option value="NS">Night Shift (NS)</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Target Employees</label>
                      <select
                        value={rotationEmployees}
                        onChange={(e) => setRotationEmployees(e.target.value)}
                        className="w-full rounded-md border border-input bg-card px-3 h-10 text-xs focus:ring-2 focus:ring-ring"
                      >
                        <option value="All">All Active Employees</option>
                        <option value="Marketing">Marketing Department Only</option>
                        <option value="Developer">Developer Department Only</option>
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Start Date</label>
                        <Input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">End Date</label>
                        <Input
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>
                    </div>
                  </div>

                  <button type="submit" className="hidden" id="drawer-submit-btn" />
                </form>
              </div>

              <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 flex items-center justify-end gap-2.5">
                <Button variant="outline" size="sm" onClick={() => setIsGeneratorOpen(false)} className="text-xs">
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => document.getElementById("drawer-submit-btn")?.click()}
                  className="text-xs shadow-xs"
                >
                  Generate Roster
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
