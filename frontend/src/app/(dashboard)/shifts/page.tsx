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
  Clock,
  Check,
  AlertTriangle,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "@/features/auth";

interface ShiftTiming {
  day: string;
  check_in: string;
  check_out: string;
  break_duration: number; // in minutes
  is_working: boolean;
}

interface ShiftItem {
  shift_id: number;
  shift_name: string;
  shift_type: "Regular" | "Flex" | "Split";
  check_in_grace_mins: number;
  is_default: boolean;
  is_active: boolean;
  timings: ShiftTiming[];
}

const INITIAL_SHIFTS: ShiftItem[] = [
  {
    shift_id: 1,
    shift_name: "General Shift",
    shift_type: "Regular",
    check_in_grace_mins: 15,
    is_default: true,
    is_active: true,
    timings: [
      { day: "Monday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Tuesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Wednesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Thursday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Friday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Saturday", check_in: "09:00", check_out: "14:00", break_duration: 30, is_working: true },
      { day: "Sunday", check_in: "00:00", check_out: "00:00", break_duration: 0, is_working: false },
    ],
  },
  {
    shift_id: 2,
    shift_name: "Morning Shift",
    shift_type: "Regular",
    check_in_grace_mins: 10,
    is_default: false,
    is_active: true,
    timings: [
      { day: "Monday", check_in: "06:00", check_out: "14:00", break_duration: 45, is_working: true },
      { day: "Tuesday", check_in: "06:00", check_out: "14:00", break_duration: 45, is_working: true },
      { day: "Wednesday", check_in: "06:00", check_out: "14:00", break_duration: 45, is_working: true },
      { day: "Thursday", check_in: "06:00", check_out: "14:00", break_duration: 45, is_working: true },
      { day: "Friday", check_in: "06:00", check_out: "14:00", break_duration: 45, is_working: true },
      { day: "Saturday", check_in: "06:00", check_out: "12:00", break_duration: 30, is_working: true },
      { day: "Sunday", check_in: "00:00", check_out: "00:00", break_duration: 0, is_working: false },
    ],
  },
  {
    shift_id: 3,
    shift_name: "Night Shift",
    shift_type: "Regular",
    check_in_grace_mins: 15,
    is_default: false,
    is_active: true,
    timings: [
      { day: "Monday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Tuesday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Wednesday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Thursday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Friday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Saturday", check_in: "22:00", check_out: "06:00", break_duration: 60, is_working: true },
      { day: "Sunday", check_in: "00:00", check_out: "00:00", break_duration: 0, is_working: false },
    ],
  },
];

export default function ShiftsPage() {
  const router = useRouter();
  const [shifts, setShifts] = useState<ShiftItem[]>(INITIAL_SHIFTS);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("All");
  
  // Drawer state
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerMode, setDrawerMode] = useState<"add" | "edit">("add");
  const [selectedShiftId, setSelectedShiftId] = useState<number | null>(null);

  // Form Fields State
  const [shiftName, setShiftName] = useState("");
  const [shiftType, setShiftType] = useState<"Regular" | "Flex" | "Split">("Regular");
  const [graceMins, setGraceMins] = useState("15");
  const [isDefault, setIsDefault] = useState(false);
  const [weeklyTimings, setWeeklyTimings] = useState<ShiftTiming[]>([
    { day: "Monday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
    { day: "Tuesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
    { day: "Wednesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
    { day: "Thursday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
    { day: "Friday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
    { day: "Saturday", check_in: "09:00", check_out: "14:00", break_duration: 30, is_working: true },
    { day: "Sunday", check_in: "00:00", check_out: "00:00", break_duration: 0, is_working: false },
  ]);

  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Filtered list
  const filteredShifts = useMemo(() => {
    let result = [...shifts];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter((s) => s.shift_name.toLowerCase().includes(q));
    }
    if (selectedType !== "All") {
      result = result.filter((s) => s.shift_type === selectedType);
    }
    return result;
  }, [shifts, searchQuery, selectedType]);

  const handleToggleActive = (id: number) => {
    setShifts((prev) =>
      prev.map((s) => (s.shift_id === id ? { ...s, is_active: !s.is_active } : s))
    );
    const target = shifts.find((s) => s.shift_id === id);
    toast.success(`Shift "${target?.shift_name}" status updated.`);
    setActiveMenuId(null);
  };

  const handleDeleteShift = (id: number) => {
    const target = shifts.find((s) => s.shift_id === id);
    if (target?.is_default) {
      toast.error("Cannot delete the default shift.");
      return;
    }
    setShifts((prev) => prev.filter((s) => s.shift_id !== id));
    toast.success(`Shift "${target?.shift_name}" deleted.`);
    setActiveMenuId(null);
  };

  const handleOpenAdd = () => {
    setDrawerMode("add");
    setShiftName("");
    setShiftType("Regular");
    setGraceMins("15");
    setIsDefault(false);
    setWeeklyTimings([
      { day: "Monday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Tuesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Wednesday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Thursday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Friday", check_in: "09:00", check_out: "18:00", break_duration: 60, is_working: true },
      { day: "Saturday", check_in: "09:00", check_out: "14:00", break_duration: 30, is_working: true },
      { day: "Sunday", check_in: "00:00", check_out: "00:00", break_duration: 0, is_working: false },
    ]);
    setIsDrawerOpen(true);
  };

  const handleOpenEdit = (shift: ShiftItem) => {
    setDrawerMode("edit");
    setSelectedShiftId(shift.shift_id);
    setShiftName(shift.shift_name);
    setShiftType(shift.shift_type);
    setGraceMins(String(shift.check_in_grace_mins));
    setIsDefault(shift.is_default);
    setWeeklyTimings(shift.timings.map((t) => ({ ...t })));
    setIsDrawerOpen(true);
    setActiveMenuId(null);
  };

  const handleSaveShift = (e: React.FormEvent) => {
    e.preventDefault();
    if (!shiftName.trim()) {
      toast.error("Shift Name is required");
      return;
    }

    if (drawerMode === "add") {
      const newId = shifts.length > 0 ? Math.max(...shifts.map((s) => s.shift_id)) + 1 : 1;
      const newShift: ShiftItem = {
        shift_id: newId,
        shift_name: shiftName,
        shift_type: shiftType,
        check_in_grace_mins: Number(graceMins) || 0,
        is_default: isDefault,
        is_active: true,
        timings: weeklyTimings,
      };

      setShifts((prev) => {
        let list = prev;
        if (isDefault) {
          list = list.map((s) => ({ ...s, is_default: false }));
        }
        return [...list, newShift];
      });
      toast.success("Shift template created successfully.");
    } else {
      setShifts((prev) => {
        let list = prev;
        if (isDefault) {
          list = list.map((s) => ({ ...s, is_default: false }));
        }
        return list.map((s) =>
          s.shift_id === selectedShiftId
            ? {
                ...s,
                shift_name: shiftName,
                shift_type: shiftType,
                check_in_grace_mins: Number(graceMins) || 0,
                is_default: isDefault,
                timings: weeklyTimings,
              }
            : s
        );
      });
      toast.success("Shift template updated successfully.");
    }
    setIsDrawerOpen(false);
  };

  const handleTimingChange = (index: number, field: keyof ShiftTiming, value: any) => {
    setWeeklyTimings((prev) =>
      prev.map((item, idx) => (idx === index ? { ...item, [field]: value } : item))
    );
  };

  const formatShiftWorkingDays = (timings: ShiftTiming[]) => {
    const days = timings.filter((t) => t.is_working).map((t) => t.day.substring(0, 3));
    if (days.length === 7) return "All Days";
    if (days.length === 6 && !timings.find((t) => t.day === "Sunday" && t.is_working)) return "Mon - Sat";
    if (days.length === 5 && !timings.find((t) => (t.day === "Saturday" || t.day === "Sunday") && t.is_working)) return "Mon - Fri";
    if (days.length === 0) return "None";
    return days.join(", ");
  };

  const getShiftTimeRange = (timings: ShiftTiming[]) => {
    const active = timings.find((t) => t.is_working);
    if (!active) return "Off Day";
    return `${active.check_in} - ${active.check_out}`;
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
              <span>Dashboard</span>
            </button>
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Shift Scheduler & Templates</h1>
          </div>
        </div>

        {/* Filters and Search toolbar */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-4 rounded-xl shadow-xs flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1 min-w-[280px]">
            <div className="relative w-full sm:max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Search shifts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 w-full"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Type:</span>
              <div className="relative">
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer w-28"
                >
                  <option value="All">All Types</option>
                  <option value="Regular">Regular</option>
                  <option value="Flex">Flex</option>
                  <option value="Split">Split</option>
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
                setSelectedType("All");
              }}
              className="gap-1.5 text-xs text-slate-500 border-slate-200 hover:bg-slate-50"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              Reset
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleOpenAdd}
              className="gap-1.5 text-xs shadow-xs"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Shift
            </Button>
          </div>
        </div>

        {/* Table representation */}
        <div className="w-full overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-[#f0f4f9] dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 font-semibold text-xs text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300">Shift Name</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Type</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Timings</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Working Days</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Grace Period</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Default</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center">Status</th>
                <th className="px-6 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-right w-20">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {filteredShifts.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-slate-500">
                    No shift templates found matching filters.
                  </td>
                </tr>
              ) : (
                filteredShifts.map((shift) => (
                  <tr key={shift.shift_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors">
                    <td className="px-6 py-4 font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 rounded-lg bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-450 shrink-0">
                          <Clock className="h-4 w-4" />
                        </div>
                        {shift.shift_name}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <Badge variant="info">{shift.shift_type}</Badge>
                    </td>
                    <td className="px-6 py-4 text-center font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                      {getShiftTimeRange(shift.timings)}
                    </td>
                    <td className="px-6 py-4 text-center text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {formatShiftWorkingDays(shift.timings)}
                    </td>
                    <td className="px-6 py-4 text-center text-slate-650 dark:text-slate-400 whitespace-nowrap font-medium">
                      {shift.check_in_grace_mins} mins
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      {shift.is_default ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200/35">
                          <Check className="h-3 w-3" /> Default
                        </span>
                      ) : (
                        "-"
                      )}
                    </td>
                    <td className="px-6 py-4 text-center whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-bold border border-border/40 ${
                          shift.is_active
                            ? "bg-emerald-500/5 text-emerald-700 dark:text-emerald-400 border-emerald-500/10"
                            : "bg-yellow-500/5 text-yellow-750 dark:text-yellow-450 border-yellow-500/10"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            shift.is_active ? "bg-emerald-500" : "bg-yellow-500"
                          }`}
                        />
                        {shift.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right relative whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveMenuId(activeMenuId === shift.shift_id ? null : shift.shift_id);
                        }}
                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md transition-colors text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer focus:outline-none"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </button>
                      {activeMenuId === shift.shift_id && (
                        <div className="absolute right-6 top-10 w-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in slide-in-from-top-1 duration-100">
                          <button
                            onClick={() => handleOpenEdit(shift)}
                            className="w-full text-left px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-850 cursor-pointer flex items-center gap-2"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                            Edit
                          </button>
                          <button
                            onClick={() => handleToggleActive(shift.shift_id)}
                            className="w-full text-left px-3.5 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-850 cursor-pointer flex items-center gap-2"
                          >
                            <Check className="h-3.5 w-3.5 text-slate-400" />
                            {shift.is_active ? "Deactivate" : "Activate"}
                          </button>
                          <button
                            onClick={() => handleDeleteShift(shift.shift_id)}
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

        {/* Drawer: Add / Edit Shift */}
        {isDrawerOpen && (
          <div className="fixed inset-0 z-[100] flex justify-end">
            <div
              className="absolute inset-0 bg-black/60 backdrop-blur-xs transition-opacity"
              onClick={() => setIsDrawerOpen(false)}
            />
            <div className="relative w-full max-w-2xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 h-full shadow-2xl flex flex-col justify-between z-10 animate-in slide-in-from-right duration-250">
              <div className="p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50 dark:bg-slate-950">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                  {drawerMode === "add" ? "Create Shift Template" : "Modify Shift Template"}
                </h3>
                <button
                  onClick={() => setIsDrawerOpen(false)}
                  className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-md text-slate-500 hover:text-slate-850 cursor-pointer focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <form onSubmit={handleSaveShift} className="space-y-6">
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Shift Name <span className="text-red-500">*</span>
                      </label>
                      <Input
                        value={shiftName}
                        onChange={(e) => setShiftName(e.target.value)}
                        placeholder="e.g. General Shift"
                        className="h-10 text-xs w-full bg-card"
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Shift Type</label>
                        <select
                          value={shiftType}
                          onChange={(e) => setShiftType(e.target.value as any)}
                          className="w-full rounded-md border border-input bg-card px-3 h-10 text-xs focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        >
                          <option value="Regular">Regular</option>
                          <option value="Flex">Flex</option>
                          <option value="Split">Split</option>
                        </select>
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">Grace Period (Minutes)</label>
                        <Input
                          type="number"
                          value={graceMins}
                          onChange={(e) => setGraceMins(e.target.value)}
                          className="h-10 text-xs w-full bg-card"
                        />
                      </div>

                      <div className="space-y-1.5 flex flex-col justify-end pb-2">
                        <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 dark:text-slate-300">
                          <input
                            type="checkbox"
                            checked={isDefault}
                            onChange={(e) => setIsDefault(e.target.checked)}
                            className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer"
                          />
                          Set as Default Shift
                        </label>
                      </div>
                    </div>
                  </div>

                  {/* Day-wise Timings Schedule */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Shift Day Timings</h4>
                    <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden divide-y divide-slate-100 dark:divide-slate-800">
                      {weeklyTimings.map((timing, idx) => (
                        <div key={timing.day} className={`p-3 grid grid-cols-12 gap-3 items-center ${timing.is_working ? "bg-white dark:bg-slate-900" : "bg-slate-50/50 dark:bg-slate-950/20"}`}>
                          <div className="col-span-3 flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={timing.is_working}
                              onChange={(e) => handleTimingChange(idx, "is_working", e.target.checked)}
                              className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer"
                            />
                            <span className="text-xs font-bold text-slate-700 dark:text-slate-300">{timing.day}</span>
                          </div>
                          
                          {timing.is_working ? (
                            <>
                              <div className="col-span-3 space-y-1">
                                <span className="text-[10px] text-slate-400 font-bold block">Check In</span>
                                <input
                                  type="time"
                                  value={timing.check_in}
                                  onChange={(e) => handleTimingChange(idx, "check_in", e.target.value)}
                                  className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-xs font-semibold focus:outline-none"
                                />
                              </div>
                              <div className="col-span-3 space-y-1">
                                <span className="text-[10px] text-slate-400 font-bold block">Check Out</span>
                                <input
                                  type="time"
                                  value={timing.check_out}
                                  onChange={(e) => handleTimingChange(idx, "check_out", e.target.value)}
                                  className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-xs font-semibold focus:outline-none"
                                />
                              </div>
                              <div className="col-span-3 space-y-1">
                                <span className="text-[10px] text-slate-400 font-bold block">Break (Mins)</span>
                                <input
                                  type="number"
                                  value={timing.break_duration}
                                  onChange={(e) => handleTimingChange(idx, "break_duration", Number(e.target.value) || 0)}
                                  className="w-full bg-slate-50 border border-slate-200 rounded px-2 py-1 text-xs font-semibold focus:outline-none"
                                />
                              </div>
                            </>
                          ) : (
                            <div className="col-span-9 text-xs text-slate-400 italic font-semibold">
                              Weekly Off / Rest Day
                            </div>
                          )}
                        </div>
                      ))}
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
                  Save Shift
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
