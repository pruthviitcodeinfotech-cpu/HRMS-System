"use client";

import { useState, useMemo } from "react";
import {
  Fingerprint,
  Cpu,
  ChevronDown,
  ArrowUpDown,
  Info,
  MoreVertical,
  Search,
  PenLine,
} from "lucide-react";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/features/auth";

interface AttendancePermissionItem {
  id: number;
  employee_id: string;
  name: string;
  department: string;
  designation: string;
  biometrics: "Fingerprint" | "-";
  method: "Hardware Device" | "Mobile" | "Both";
  mobile_attendance: boolean;
  geofencing: string;
  auto_punch_out: string;
}

const INITIAL_PERMISSION_ITEMS: AttendancePermissionItem[] = [
  { id: 1, employee_id: "58", name: "Savan Kamuni", department: "Marketing", designation: "marketing", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 2, employee_id: "57", name: "Tulsi baladhiya", department: "Marketing", designation: "Graphic Designer", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 3, employee_id: "56", name: "Hetal Gohil", department: "Marketing", designation: "marketing", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 4, employee_id: "55", name: "Mansi Boghra", department: "Developer", designation: "Python", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 5, employee_id: "54", name: "Divyesh Pipaliya", department: "Marketing", designation: "marketing", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 6, employee_id: "53", name: "Pratik raval", department: "Marketing", designation: "marketing", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 7, employee_id: "52", name: "Krishna Chodvadiya", department: "BDM", designation: "BDM", biometrics: "-", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 8, employee_id: "51", name: "Kunal Kikani", department: "video editing", designation: "video editing", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
  { id: 9, employee_id: "50", name: "Vivek Rathod", department: "Graphic Designer", designation: "Graphic Designer", biometrics: "Fingerprint", method: "Hardware Device", mobile_attendance: false, geofencing: "-", auto_punch_out: "-" },
];

type SortField = "employee_id" | "name" | "department" | "designation";
type SortOrder = "asc" | "desc";

export default function AttendancePermissionPage() {
  const [items, setItems] = useState<AttendancePermissionItem[]>(INITIAL_PERMISSION_ITEMS);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");
  
  // Filters
  const [selectedBranch, setSelectedBranch] = useState("Itcode Infotech");
  const [selectedDevice, setSelectedDevice] = useState("Itcode Infotech(17)");
  const [selectedAttempts, setSelectedAttempts] = useState("7 Attempt");

  // Sorting
  const [sortConfig, setSortConfig] = useState<{ field: SortField; order: SortOrder } | null>(null);

  // Active action dropdown
  const [activeActionId, setActiveActionId] = useState<number | null>(null);

  // Handle row selection
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(items.map(item => item.id)));
    } else {
      setSelectedIds(new Set());
    }
  };

  const handleSelectItem = (id: number, checked: boolean) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  };

  // Toggle single mobile attendance
  const handleToggleMobile = (id: number) => {
    setItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, mobile_attendance: !item.mobile_attendance } : item
      )
    );
    toast.success("Mobile attendance preference updated.");
  };

  // Bulk enable / disable action helper
  const handleBulkAction = (field: "mobile" | "geofencing" | "auto_punch_out", value: boolean) => {
    if (selectedIds.size === 0) {
      toast.warning("Please select at least one employee first.");
      return;
    }

    setItems(prev =>
      prev.map(item => {
        if (!selectedIds.has(item.id)) return item;
        if (field === "mobile") {
          return { ...item, mobile_attendance: value };
        } else if (field === "geofencing") {
          return { ...item, geofencing: value ? "Enabled" : "Disabled" };
        } else {
          return { ...item, auto_punch_out: value ? "Enabled" : "Disabled" };
        }
      })
    );

    toast.success(`Bulk updated for ${selectedIds.size} selected employees.`);
  };

  // Sorting handler
  const handleSort = (field: SortField) => {
    setSortConfig(prev => {
      if (prev && prev.field === field) {
        return { field, order: prev.order === "asc" ? "desc" : "asc" };
      }
      return { field, order: "asc" };
    });
  };

  const getSortIcon = (field: SortField) => {
    const isActive = sortConfig?.field === field;
    return (
      <ArrowUpDown
        className={`ml-1 h-3.5 w-3.5 transition-all inline ${
          isActive ? "text-primary opacity-100" : "opacity-60 hover:opacity-100"
        }`}
      />
    );
  };

  // Filtered & Sorted list
  const processedItems = useMemo(() => {
    let result = [...items];

    if (searchTerm.trim() !== "") {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        item =>
          item.name.toLowerCase().includes(term) ||
          item.employee_id.toLowerCase().includes(term) ||
          item.department.toLowerCase().includes(term) ||
          item.designation.toLowerCase().includes(term)
      );
    }

    if (sortConfig) {
      const { field, order } = sortConfig;
      result.sort((a, b) => {
        let valA = a[field];
        let valB = b[field];

        if (field === "employee_id") {
          const numA = parseInt(valA, 10) || 0;
          const numB = parseInt(valB, 10) || 0;
          return order === "asc" ? numA - numB : numB - numA;
        }

        valA = valA.toLowerCase();
        valB = valB.toLowerCase();

        if (valA < valB) return order === "asc" ? -1 : 1;
        if (valA > valB) return order === "asc" ? 1 : -1;
        return 0;
      });
    }

    return result;
  }, [items, searchTerm, sortConfig]);

  const isAllSelected = items.length > 0 && selectedIds.size === items.length;

  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <div className="p-6 space-y-6 bg-slate-50/40 min-h-screen">
        {/* Header Title and Global Configs */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">Attendance Permission</h1>
          
          {/* Global enable/disable buttons */}
          <div className="flex flex-wrap items-center gap-4 bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-2 rounded-xl shadow-xs">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-450">Mobile Attendance</span>
              <button
                onClick={() => handleBulkAction("mobile", true)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Enable
              </button>
              <button
                onClick={() => handleBulkAction("mobile", false)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Disable
              </button>
            </div>
            
            <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-450">Geo Fencing</span>
              <button
                onClick={() => handleBulkAction("geofencing", true)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Enable
              </button>
              <button
                onClick={() => handleBulkAction("geofencing", false)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-755 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Disable
              </button>
            </div>

            <div className="h-4 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />

            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-450">Auto Punch Out</span>
              <button
                onClick={() => handleBulkAction("auto_punch_out", true)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Enable
              </button>
              <button
                onClick={() => handleBulkAction("auto_punch_out", false)}
                className="px-3 py-1 text-xs border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-100 rounded-md font-semibold cursor-pointer shadow-xs transition-colors"
              >
                Disable
              </button>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 p-4 rounded-xl shadow-xs flex flex-wrap items-center gap-6">
          <div className="w-full sm:w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input
              type="text"
              placeholder="Search employee..."
              value={searchTerm}
              onChange={e => setSearchTerm(e.target.value)}
              className="pl-9 w-full"
            />
          </div>

          <div className="flex flex-wrap items-center gap-4 flex-1">
            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Choose Branch</span>
              <div className="relative">
                <select
                  value={selectedBranch}
                  onChange={e => setSelectedBranch(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer w-44"
                >
                  <option value="Itcode Infotech">Itcode Infotech</option>
                  <option value="Mumbai Branch">Mumbai Branch</option>
                  <option value="Delhi Branch">Delhi Branch</option>
                </select>
                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Choose Device</span>
              <div className="relative">
                <select
                  value={selectedDevice}
                  onChange={e => setSelectedDevice(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer w-44"
                >
                  <option value="Itcode Infotech(17)">Itcode Infotech(17)</option>
                  <option value="Device A">Device A (08)</option>
                  <option value="Device B">Device B (02)</option>
                </select>
                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Choose No Of Attempt</span>
              <div className="relative">
                <select
                  value={selectedAttempts}
                  onChange={e => setSelectedAttempts(e.target.value)}
                  className="appearance-none bg-slate-50 border border-slate-200 rounded-lg pl-3 pr-8 py-1.5 text-xs font-semibold text-slate-700 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer w-36"
                >
                  <option value="7 Attempt">7 Attempt</option>
                  <option value="5 Attempt">5 Attempt</option>
                  <option value="3 Attempt">3 Attempt</option>
                </select>
                <ChevronDown className="absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400 pointer-events-none" />
              </div>
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="w-full overflow-x-auto rounded-xl border border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
          <table className="w-full text-left border-collapse text-sm">
            <thead className="bg-[#f0f4f9] dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 font-semibold text-xs text-slate-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3.5 w-12 text-center align-middle">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={e => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer"
                  />
                </th>
                <th
                  onClick={() => handleSort("employee_id")}
                  className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-800/50 select-none transition-colors whitespace-nowrap"
                >
                  Employee ID {getSortIcon("employee_id")}
                </th>
                <th
                  onClick={() => handleSort("name")}
                  className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-800/50 select-none transition-colors whitespace-nowrap"
                >
                  Employee Name {getSortIcon("name")}
                </th>
                <th
                  onClick={() => handleSort("department")}
                  className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-800/50 select-none transition-colors whitespace-nowrap"
                >
                  Department {getSortIcon("department")}
                </th>
                <th
                  onClick={() => handleSort("designation")}
                  className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-800/50 select-none transition-colors whitespace-nowrap"
                >
                  Designation {getSortIcon("designation")}
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                  Biometrics Registered
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                  Attendance Method
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                  Mobile Attendance
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                  Geofencing
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 whitespace-nowrap inline-flex items-center gap-1">
                  Auto Punch Out
                  <span title="Automatically signs out employees at end of shift">
                    <Info className="h-3.5 w-3.5 text-slate-400 cursor-help" />
                  </span>
                </th>
                <th className="px-4 py-3.5 font-bold text-slate-700 dark:text-slate-300 text-center w-20 whitespace-nowrap">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {processedItems.map(item => (
                <tr
                  key={item.id}
                  className={`hover:bg-slate-50/50 dark:hover:bg-slate-800/20 transition-colors ${
                    selectedIds.has(item.id) ? "bg-primary/5 hover:bg-primary/10" : ""
                  }`}
                >
                  <td className="px-4 py-3 w-12 text-center align-middle">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(item.id)}
                      onChange={e => handleSelectItem(item.id, e.target.checked)}
                      className="h-4 w-4 rounded border-slate-300 text-primary focus:ring-primary cursor-pointer"
                    />
                  </td>
                  
                  <td className="px-4 py-3 align-middle font-medium text-slate-800 dark:text-slate-200">
                    {item.employee_id}
                  </td>
                  
                  <td className="px-4 py-3 align-middle font-semibold text-slate-800 dark:text-slate-200 whitespace-nowrap">
                    {item.name}
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    {item.department}
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    {item.designation}
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    {item.biometrics === "Fingerprint" ? (
                      <span className="inline-flex items-center gap-1 bg-slate-50 dark:bg-slate-800 px-2 py-1 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 border border-slate-100 dark:border-slate-700">
                        <Fingerprint className="h-3.5 w-3.5 text-slate-500" />
                        Fingerprint
                      </span>
                    ) : (
                      "-"
                    )}
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 bg-slate-50 dark:bg-slate-800 px-2 py-1 rounded-md text-xs font-medium text-slate-600 dark:text-slate-400 border border-slate-100 dark:border-slate-700">
                      <Cpu className="h-3.5 w-3.5 text-slate-500" />
                      Hardware Device
                    </span>
                  </td>

                  <td className="px-4 py-3 align-middle whitespace-nowrap">
                    {/* Toggle Switch */}
                    <button
                      type="button"
                      onClick={() => handleToggleMobile(item.id)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-250 ease-in-out focus:outline-none ${
                        item.mobile_attendance ? 'bg-[#007bff]' : 'bg-slate-250 dark:bg-slate-700'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-md ring-0 transition duration-250 ease-in-out ${
                          item.mobile_attendance ? 'translate-x-4' : 'translate-x-0'
                        }`}
                      />
                    </button>
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 text-center whitespace-nowrap">
                    {item.geofencing}
                  </td>

                  <td className="px-4 py-3 align-middle text-slate-600 dark:text-slate-400 text-center whitespace-nowrap">
                    {item.auto_punch_out}
                  </td>

                  <td className="px-4 py-3 align-middle text-center relative whitespace-nowrap">
                    <button
                      onClick={e => {
                        e.stopPropagation();
                        setActiveActionId(activeActionId === item.id ? null : item.id);
                      }}
                      className="p-1 hover:bg-slate-100 dark:hover:bg-slate-850 rounded-md transition-colors text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 cursor-pointer focus:outline-none"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </button>

                    {activeActionId === item.id && (
                      <div className="absolute right-2 top-full mt-0 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg py-1 z-50 animate-in fade-in duration-100">
                        <button
                          onClick={() => {
                            toast.success(`Mobile login reset for ${item.name}`);
                            setActiveActionId(null);
                          }}
                          className="w-full flex items-center gap-2.5 text-left px-3.5 py-2.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
                        >
                          <PenLine className="h-4 w-4 text-slate-450 dark:text-slate-400" />
                          <span>Reset Mobile Login</span>
                        </button>
                        <button
                          onClick={() => {
                            toast.info(`Editing biometrics for ${item.name}`);
                            setActiveActionId(null);
                          }}
                          className="w-full flex items-center gap-2.5 text-left px-3.5 py-2.5 text-xs font-semibold text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer border-t border-slate-100 dark:border-slate-800/80"
                        >
                          <Fingerprint className="h-4 w-4 text-slate-450 dark:text-slate-400" />
                          <span>Edit Biometrics</span>
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </ProtectedRoute>
  );
}
