"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import { ProtectedRoute } from "@/features/auth";
import {
  Users,
  UserCheck,
  Clock,
  Trees,
  Fingerprint,
  Info,
  Calendar,
  AlertTriangle,
  RefreshCw,
  Check,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  CircleDot,
  CheckCircle2,
  Filter,
  Briefcase,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { ApprovalRequest } from "@/features/approvals";
import {
  useDashboardKPIs,
  useAttendanceDays,
  useShiftSummary,
  useDepartmentAttendance,
  useDevicesList,
  useApprovalsDashboard,
  useApproveApproval,
  useRejectApproval,
  usePendingBiometrics,
} from "@/features/dashboard";

// Helper formatters
const formatPunchTime = (dateStr: string | null) => {
  if (!dateStr) return "-";
  try {
    const d = new Date(dateStr);
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${String(hours).padStart(2, '0')}:${minutes} ${ampm}`;
  } catch {
    return dateStr;
  }
};

const formatHours = (hours: number | null) => {
  if (hours === null || hours === undefined) return "-";
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  if (h === 0 && m === 0) return "-";
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
};

const formatDeviceDate = (dateStr: string | null) => {
  if (!dateStr) return "Never";
  try {
    const d = new Date(dateStr);
    const pad = (n: number) => String(n).padStart(2, '0');
    const day = pad(d.getDate());
    const month = pad(d.getMonth() + 1);
    const year = d.getFullYear();
    let hours = d.getHours();
    const minutes = pad(d.getMinutes());
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${day}-${month}-${year} | ${pad(hours)}:${minutes} ${ampm}`;
  } catch {
    return dateStr;
  }
};

const formatApprovalDate = (dateStr: string) => {
  try {
    const d = new Date(dateStr);
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const dateNum = d.getDate();
    const monthStr = months[d.getMonth()];
    const dayStr = days[d.getDay()];
    return `${dateNum} ${monthStr} (${dayStr})`;
  } catch {
    return dateStr;
  }
};

const formatDateForButton = (dateStr: string) => {
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    const day = d.getDate();
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    return `${day} ${month}, ${year}`;
  } catch {
    return dateStr;
  }
};

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

const getCalendarGridDays = (viewDate: Date) => {
  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();

  const firstDayIndex = new Date(year, month, 1).getDay();
  const totalDays = new Date(year, month + 1, 0).getDate();
  const prevMonthTotalDays = new Date(year, month, 0).getDate();

  const days: { date: Date; isCurrentMonth: boolean }[] = [];

  for (let i = firstDayIndex - 1; i >= 0; i--) {
    days.push({
      date: new Date(year, month - 1, prevMonthTotalDays - i),
      isCurrentMonth: false,
    });
  }

  for (let i = 1; i <= totalDays; i++) {
    days.push({
      date: new Date(year, month, i),
      isCurrentMonth: true,
    });
  }

  const remainingCells = 42 - days.length;
  for (let i = 1; i <= remainingCells; i++) {
    days.push({
      date: new Date(year, month + 1, i),
      isCurrentMonth: false,
    });
  }

  return days;
};

const formatDateStr = (date: Date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
};


// Skeletons
const CardSkeleton = () => (
  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="bg-card border border-border rounded-xl p-4 shadow-xs flex items-center space-x-4 animate-pulse">
        <div className="h-12 w-12 rounded-lg bg-slate-200 dark:bg-slate-800 shrink-0" />
        <div className="space-y-2 flex-1">
          <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-2/3" />
          <div className="h-6 bg-slate-200 dark:bg-slate-800 rounded w-1/2" />
        </div>
      </div>
    ))}
  </div>
);

const WidgetSkeleton = ({ title }: { title: string }) => (
  <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden">
    <div className="p-4 border-b border-border bg-slate-50/30 dark:bg-slate-900/10">
      <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs tracking-tight">{title}</h4>
    </div>
    <div className="p-6 space-y-4 animate-pulse">
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-8 bg-slate-100 dark:bg-slate-900 rounded w-full" />
        ))}
      </div>
    </div>
  </div>
);

const ErrorWidget = ({ title, error }: { title: string; error: { message?: string } | null }) => (
  <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden p-6 text-center text-rose-500 dark:text-rose-400">
    <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
    <h4 className="font-bold text-xs">{title} failed to load</h4>
    <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-1">
      {error?.message || "Please check your credentials/network and try again."}
    </p>
  </div>
);

export default function DashboardPage() {
  const router = useRouter();
  const [targetDate, setTargetDate] = useState<string>("2026-07-15");
  const [isCalendarOpen, setIsCalendarOpen] = useState(false);
  const [viewDate, setViewDate] = useState<Date>(new Date(2026, 6, 15)); // July 15, 2026
  const calendarRef = useRef<HTMLDivElement>(null);

  const [localPendingApprovals] = useState<ApprovalRequest[]>([]);

  // Close calendar popover on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (calendarRef.current && !calendarRef.current.contains(event.target as Node)) {
        setIsCalendarOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const handlePrevMonth = () => {
    setViewDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setViewDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleSelectDay = (date: Date) => {
    setTargetDate(formatDateStr(date));
    setIsCalendarOpen(false);
  };

  const isSelected = (date: Date) => {
    return formatDateStr(date) === targetDate;
  };

  const calendarDays = getCalendarGridDays(viewDate);

  // Tab and Filter selection states
  const [activeTab, setActiveTab] = useState<"all" | "open" | "khushi" | "night" | "daily">("all");
  const [selectedFilter, setSelectedFilter] = useState<"on-time" | "late" | "not-in" | "time-off">("on-time");
  const [isSyncing, setIsSyncing] = useState(false);

  // Filter visibility states
  const [visibleFilters, setVisibleFilters] = useState<Record<string, boolean>>({});
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  // Table sorting states
  const [sortConfig, setSortConfig] = useState<{ key: string; direction: "asc" | "desc" } | null>(null);

  // Table filter states
  const [selectedEmpId, setSelectedEmpId] = useState<string | null>(null);
  const [selectedEmpName, setSelectedEmpName] = useState("");
  const [selectedDept, setSelectedDept] = useState<string | null>(null);
  const [selectedDesig, setSelectedDesig] = useState<string | null>(null);
  const [selectedShift, setSelectedShift] = useState<string | null>(null);
  const [selectedDeptSummary, setSelectedDeptSummary] = useState<string | null>(null);

  // Drawer states
  const [drawerTitle, setDrawerTitle] = useState<string | null>(null);
  const [selectedKpi, setSelectedKpi] = useState<string>("Total Employees");

  // Queries
  const { data: kpiData, isLoading: isKpisLoading, error: kpisError } = useDashboardKPIs(targetDate);
  const {
    data: attendanceData,
    isLoading: isAttendanceLoading,
    error: attendanceError,
    refetch: refetchAttendance,
  } = useAttendanceDays({
    date: targetDate,
    page: 1,
    page_size: 150, // Fetch all records for drawer matching
  });
  const { data: shiftData, isLoading: isShiftsLoading, error: shiftsError, refetch: refetchShifts } = useShiftSummary(targetDate);
  const { data: deptChartData, isLoading: isDeptLoading, error: deptError } = useDepartmentAttendance(targetDate);
  const { data: devicesData, isLoading: isDevicesLoading, error: devicesError, refetch: refetchDevices } = useDevicesList({
    page: 1,
    page_size: 50,
  });
  const { data: approvalsData, isLoading: isApprovalsLoading, error: approvalsError } = useApprovalsDashboard();
  const { data: pendingBioData } = usePendingBiometrics({ page: 1, page_size: 100 });

  // Mutations
  const approveMutation = useApproveApproval();
  const rejectMutation = useRejectApproval();

  const handleSyncDevices = async () => {
    setIsSyncing(true);
    try {
      await refetchDevices();
      await refetchAttendance();
      await refetchShifts();
      toast.success("Biometric hardware status re-synchronized successfully!");
    } catch {
      toast.error("Failed to re-synchronize biometric hardware.");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleApprovalAction = async (id: number | string, action: "approve" | "reject") => {
    try {
      if (typeof id === "number") {
        if (action === "approve") {
          await approveMutation.mutateAsync({ id, remarks: "Approved via dashboard" });
          toast.success(`Request #${id} approved successfully.`);
        } else {
          await rejectMutation.mutateAsync({ id, remarks: "Rejected via dashboard" });
          toast.success(`Request #${id} rejected successfully.`);
        }
      } else {
        toast.info("Backend approval integration pending for legacy request ID.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : `Failed to ${action} request.`;
      toast.error(msg);
    }
  };

  // Dynamic filter lists from data
  const employeeIds = Array.from(
    new Set((attendanceData?.items || []).map((emp) => String(emp.employee_id)))
  ).sort((a, b) => Number(a) - Number(b));

  const departments = Array.from(
    new Set((attendanceData?.items || []).map((emp) => emp.department_name).filter(Boolean))
  ) as string[];

  const designations = Array.from(
    new Set((attendanceData?.items || []).map((emp) => emp.designation).filter(Boolean))
  ) as string[];

  const shiftNames = Array.from(
    new Set((shiftData?.shifts || []).map((row) => row.shift_name))
  );

  const deptSummaryNames = Array.from(
    new Set(deptChartData?.labels || [])
  );

  const toggleFilterVisibility = (colKey: string) => {
    setVisibleFilters((prev) => ({
      ...prev,
      [colKey]: !prev[colKey],
    }));
  };

  const handleSort = (key: string) => {
    setSortConfig((prev) => {
      if (!prev || prev.key !== key) {
        return { key, direction: "asc" };
      }
      if (prev.direction === "asc") {
        return { key, direction: "desc" };
      }
      return null;
    });
  };

  const renderSortIcon = (key: string) => {
    if (sortConfig?.key !== key) {
      return <ArrowUpDown className="h-3.5 w-3.5 opacity-50 shrink-0" />;
    }
    if (sortConfig.direction === "asc") {
      return <ArrowUp className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" />;
    }
    return <ArrowDown className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400 shrink-0" />;
  };

  const getFilteredItemsByShift = () => {
    if (!attendanceData?.items) return [];
    let items = attendanceData.items;
    if (activeTab !== "all") {
      const tabToShiftName: Record<string, string> = {
        open: "Open Shift",
        khushi: "Khushi maam 8 to 6",
        night: "Night Shift Developer",
        daily: "Daily",
      };
      const targetShiftName = tabToShiftName[activeTab];
      if (targetShiftName) {
        items = items.filter(
          (row) => (row.shift_name || "").toLowerCase() === targetShiftName.toLowerCase()
        );
      }
    }
    return items;
  };

  const getShiftTotalCount = (tabId: string) => {
    if (!attendanceData?.items) return 0;
    if (tabId === "all") return attendanceData.items.length;
    
    const tabToShiftName: Record<string, string> = {
      open: "Open Shift",
      khushi: "Khushi maam 8 to 6",
      night: "Night Shift Developer",
      daily: "Daily",
    };
    const targetShiftName = tabToShiftName[tabId];
    if (!targetShiftName) return 0;
    
    return attendanceData.items.filter(
      (row) => (row.shift_name || "").toLowerCase() === targetShiftName.toLowerCase()
    ).length;
  };

  const getTableData = () => {
    if (!attendanceData?.items) return [];
    
    let data = getFilteredItemsByShift();
    
    if (selectedFilter === "on-time") {
      data = data.filter((row) => (row.status === "present" || row.status === "half_day") && (row.late_minutes || 0) === 0);
    } else if (selectedFilter === "late") {
      data = data.filter((row) => (row.status === "present" || row.status === "half_day") && (row.late_minutes || 0) > 0);
    } else if (selectedFilter === "not-in") {
      data = data.filter((row) => row.status === "absent" || row.status === "not_marked");
    } else if (selectedFilter === "time-off") {
      data = data.filter((row) => row.status === "on_leave");
    }

    if (selectedEmpId) {
      data = data.filter((row) => String(row.employee_id) === selectedEmpId);
    }
    if (selectedEmpName.trim()) {
      data = data.filter((row) => 
        (row.employee_name || "").toLowerCase().includes(selectedEmpName.toLowerCase())
      );
    }
    if (selectedDept) {
      data = data.filter((row) => 
        (row.department_name || "").toLowerCase() === selectedDept.toLowerCase()
      );
    }
    if (selectedDesig) {
      data = data.filter((row) => 
        (row.designation || "").toLowerCase() === selectedDesig.toLowerCase()
      );
    }

    // Apply sorting
    if (sortConfig) {
      data = [...data].sort((a, b) => {
        let aVal: any = null;
        let bVal: any = null;

        if (sortConfig.key === "empId") {
          aVal = a.employee_id;
          bVal = b.employee_id;
        } else if (sortConfig.key === "empName") {
          aVal = a.employee_name;
          bVal = b.employee_name;
        } else if (sortConfig.key === "dept") {
          aVal = a.department_name;
          bVal = b.department_name;
        } else if (sortConfig.key === "desig") {
          aVal = a.designation;
          bVal = b.designation;
        }

        if (aVal === undefined || aVal === null) return 1;
        if (bVal === undefined || bVal === null) return -1;

        if (typeof aVal === "number" && typeof bVal === "number") {
          return sortConfig.direction === "asc" ? aVal - bVal : bVal - aVal;
        }

        const aStr = String(aVal).trim().toLowerCase();
        const bStr = String(bVal).trim().toLowerCase();

        if (aStr < bStr) return sortConfig.direction === "asc" ? -1 : 1;
        if (aStr > bStr) return sortConfig.direction === "asc" ? 1 : -1;
        return 0;
      });
    }
    
    return data;
  };

  const getShiftData = () => {
    const shifts = shiftData?.shifts || [];
    if (selectedShift) {
      return shifts.filter((row) => row.shift_name.toLowerCase() === selectedShift.toLowerCase());
    }
    return shifts;
  };

  const getDeptSummaryData = () => {
    if (!deptChartData?.labels) return [];
    const presentSeries = deptChartData.series.find(s => s.name === "Present");
    const absentSeries = deptChartData.series.find(s => s.name === "Absent");
    
    const mapped = deptChartData.labels.map((deptName, i) => {
      return {
        name: deptName,
        checkedIn: presentSeries ? presentSeries.points[i] : 0,
        notIn: absentSeries ? absentSeries.points[i] : 0,
        off: 0
      };
    });
    
    if (selectedDeptSummary) {
      return mapped.filter((row) => row.name.toLowerCase() === selectedDeptSummary.toLowerCase());
    }
    return mapped;
  };

  const getDrawerEmployees = () => {
    if (!attendanceData?.items) return [];
    
    switch (drawerTitle) {
      case "Total Employees":
        return attendanceData.items.map(item => ({
          id: String(item.employee_id),
          name: item.employee_name || `Employee #${item.employee_id}`
        }));
      case "Currently Working":
        return attendanceData.items
          .filter(item => item.status === "present" || item.status === "half_day")
          .map(item => ({
            id: String(item.employee_id),
            name: item.employee_name || `Employee #${item.employee_id}`
          }));
      case "On Break":
        return attendanceData.items
          .filter(item => item.is_on_break)
          .map(item => ({
            id: String(item.employee_id),
            name: item.employee_name || `Employee #${item.employee_id}`
          }));
      case "Time Off":
        return attendanceData.items
          .filter(item => item.status === "on_leave")
          .map(item => ({
            id: String(item.employee_id),
            name: item.employee_name || `Employee #${item.employee_id}`
          }));
      case "Pending Biometrics":
        return (pendingBioData?.items || []).map(item => ({
          id: String(item.employee_id),
          name: item.employee_name || `Employee #${item.employee_id}`
        }));
      default:
        return [];
    }
  };

  const pendingApprovals = useMemo(() => {
    if (approvalsData?.recent && approvalsData.recent.length > 0) {
      return approvalsData.recent;
    }
    return localPendingApprovals.map((req) => ({
      id: req.id,
      requester_name: `${req.employeeCode} - ${req.employeeName}`,
      request_type: `${req.type} (${req.subtype})`,
      submitted_at: req.submittedDate,
    }));
  }, [approvalsData, localPendingApprovals]);

  return (
    <ProtectedRoute requiredPermission={{ feature: "dashboard", action: "read" }}>
      <div className="space-y-6">
        


        {/* Row 1: KPI Summary Cards */}
        {isKpisLoading ? (
          <CardSkeleton />
        ) : kpisError ? (
          <div className="p-6 text-center text-rose-500 border border-border bg-card rounded-xl">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
            <p className="font-semibold text-xs">Failed to load Dashboard KPIs</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            
            {/* Card 1: Total Employees */}
            <div
              onClick={() => {
                setSelectedKpi("Total Employees");
                setDrawerTitle("Total Employees");
              }}
              className={`bg-card text-card-foreground rounded-xl p-4 shadow-xs flex items-center space-x-4 hover:shadow-md cursor-pointer transition-all duration-300 ${
                selectedKpi === "Total Employees"
                  ? "border-2 border-blue-500/80 shadow-sm shadow-blue-500/5 bg-blue-50/5 dark:bg-blue-950/10"
                  : "border border-border"
              }`}
            >
              <div className="h-12 w-12 rounded-lg bg-blue-50 dark:bg-blue-950/30 flex items-center justify-center text-blue-600 dark:text-blue-400 shrink-0">
                <Users className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center space-x-1">
                  <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                    Total Employees
                  </span>
                  <Info className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500 hover:text-slate-600 cursor-pointer" />
                </div>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1 leading-none">
                  {kpiData?.total_employees || 0}
                </p>
              </div>
            </div>

            {/* Card 2: Currently Working */}
            <div
              onClick={() => {
                setSelectedKpi("Currently Working");
                setDrawerTitle("Currently Working");
              }}
              className={`bg-card text-card-foreground rounded-xl p-4 shadow-xs flex items-center space-x-4 hover:shadow-md cursor-pointer transition-all duration-300 ${
                selectedKpi === "Currently Working"
                  ? "border-2 border-emerald-500/80 shadow-sm shadow-emerald-500/5 bg-emerald-50/5 dark:bg-emerald-950/10"
                  : "border border-border"
              }`}
            >
              <div className="h-12 w-12 rounded-lg bg-emerald-50 dark:bg-emerald-950/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                <UserCheck className="h-6 w-6" />
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                  Currently Working
                </span>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1 leading-none">
                  {kpiData?.present_today || 0}
                </p>
              </div>
            </div>

            {/* Card 3: On Break */}
            <div
              onClick={() => {
                setSelectedKpi("On Break");
                setDrawerTitle("On Break");
              }}
              className={`bg-card text-card-foreground rounded-xl p-4 shadow-xs flex items-center space-x-4 hover:shadow-md cursor-pointer transition-all duration-300 ${
                selectedKpi === "On Break"
                  ? "border-2 border-amber-500/80 shadow-sm shadow-amber-500/5 bg-amber-50/5 dark:bg-amber-950/10"
                  : "border border-border"
              }`}
            >
              <div className="h-12 w-12 rounded-lg bg-amber-50 dark:bg-amber-950/30 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
                <Clock className="h-6 w-6" />
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                  On Break
                </span>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1 leading-none">
                  {kpiData?.on_break_today || 0}
                </p>
              </div>
            </div>

            {/* Card 4: Time Off */}
            <div
              onClick={() => {
                setSelectedKpi("Time Off");
                setDrawerTitle("Time Off");
              }}
              className={`bg-card text-card-foreground rounded-xl p-4 shadow-xs flex items-center space-x-4 hover:shadow-md cursor-pointer transition-all duration-300 ${
                selectedKpi === "Time Off"
                  ? "border-2 border-indigo-500/80 shadow-sm shadow-indigo-500/5 bg-indigo-50/5 dark:bg-indigo-950/10"
                  : "border border-border"
              }`}
            >
              <div className="h-12 w-12 rounded-lg bg-indigo-50 dark:bg-indigo-950/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                <Trees className="h-6 w-6" />
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                  Time Off
                </span>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1 leading-none">
                  {kpiData?.on_leave_today || 0}
                </p>
              </div>
            </div>

            {/* Card 5: Pending Biometrics */}
            <div
              onClick={() => {
                setSelectedKpi("Pending Biometrics");
                setDrawerTitle("Pending Biometrics");
              }}
              className={`bg-card text-card-foreground rounded-xl p-4 shadow-xs flex items-center space-x-4 hover:shadow-md cursor-pointer transition-all duration-300 ${
                selectedKpi === "Pending Biometrics"
                  ? "border-2 border-rose-500/80 shadow-sm shadow-rose-500/5 bg-rose-50/5 dark:bg-rose-950/10"
                  : "border border-border"
              }`}
            >
              <div className="h-12 w-12 rounded-lg bg-rose-50 dark:bg-rose-950/30 flex items-center justify-center text-rose-600 dark:text-rose-400 shrink-0">
                <Fingerprint className="h-6 w-6" />
              </div>
              <div>
                <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider block">
                  Pending Biometrics
                </span>
                <p className="text-2xl font-bold text-slate-800 dark:text-slate-100 mt-1 leading-none">
                  {kpiData?.pending_biometrics || 0}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Row 2: Quick Attendance Summary Widget Container */}
        {isAttendanceLoading ? (
          <WidgetSkeleton title="Quick Attendance Summary" />
        ) : attendanceError ? (
          <ErrorWidget title="Quick Attendance Summary" error={attendanceError} />
        ) : (
          <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden">
            {/* Header area */}
            <div className="p-5 border-b border-border flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-slate-50/30 dark:bg-slate-900/10">
              <h3 className="font-bold text-slate-800 dark:text-slate-100 text-sm tracking-tight">
                Quick Attendance Summary
              </h3>
              
              {/* Dynamic Calendar Picker */}
              <div className="relative" ref={calendarRef}>
                <button
                  onClick={() => {
                    const currentTarget = new Date(targetDate);
                    if (!isNaN(currentTarget.getTime())) {
                      setViewDate(currentTarget);
                    }
                    setIsCalendarOpen(!isCalendarOpen);
                  }}
                  className="inline-flex items-center gap-2.5 px-3 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/80 shadow-xs transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500/25"
                >
                  <Calendar className="h-4 w-4 text-slate-400 dark:text-slate-500" />
                  <span>{formatDateForButton(targetDate)}</span>
                  <ChevronDown className="h-3.5 w-3.5 text-slate-400 dark:text-slate-500 transition-transform duration-200" />
                </button>

                {isCalendarOpen && (
                  <div className="absolute right-0 mt-2 w-80 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-lg p-4 z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* Calendar Header */}
                    <div className="flex items-center justify-between mb-4">
                      <button
                        onClick={handlePrevMonth}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500 dark:text-slate-400 transition-colors"
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </button>
                      <span className="text-sm font-semibold text-slate-700 dark:text-slate-200">
                        {MONTH_NAMES[viewDate.getMonth()]} {viewDate.getFullYear()}
                      </span>
                      <button
                        onClick={handleNextMonth}
                        className="p-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg text-slate-500 dark:text-slate-400 transition-colors"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>

                    {/* Weekday labels */}
                    <div className="grid grid-cols-7 gap-1 mb-1">
                      {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map(day => (
                        <div
                          key={day}
                          className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider text-center py-1"
                        >
                          {day}
                        </div>
                      ))}
                    </div>

                    {/* Calendar Grid */}
                    <div className="grid grid-cols-7 gap-1">
                      {calendarDays.map((cell, idx) => {
                        const selected = isSelected(cell.date);
                        return (
                          <button
                            key={idx}
                            onClick={() => handleSelectDay(cell.date)}
                            className={`h-9 w-9 rounded-full flex items-center justify-center text-xs transition-all duration-200 focus:outline-none ${
                              selected
                                ? "bg-blue-500 dark:bg-blue-600 text-white font-semibold shadow-xs"
                                : cell.isCurrentMonth
                                ? "text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
                                : "text-slate-300 dark:text-slate-600 hover:bg-slate-50 dark:hover:bg-slate-900/50 cursor-pointer"
                            }`}
                          >
                            {cell.date.getDate()}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            </div>
            {/* Shift Tabs */}
            <div className="px-5 border-b border-border flex items-center space-x-6 overflow-x-auto scrollbar-none py-1">
              {[
                { id: "all", label: "All" },
                { id: "open", label: "Open Shift" },
                { id: "khushi", label: "Khushi maam 8 to 6" },
                { id: "night", label: "Night Shift Developer" },
                { id: "daily", label: "Daily" },
              ].map((tab) => {
                const count = getShiftTotalCount(tab.id);
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id as any);
                      setSelectedFilter("on-time");
                    }}
                    className={`py-3.5 text-xs font-semibold tracking-wide border-b-2 relative transition-all duration-200 shrink-0 cursor-pointer ${
                      activeTab === tab.id
                        ? "border-blue-600 dark:border-blue-500 text-blue-600 dark:text-blue-400 font-bold"
                        : "border-transparent text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-200"
                    }`}
                  >
                    <span>{tab.label}</span>
                    <span className={`ml-1.5 px-1.5 py-0.5 rounded-full text-[10px] ${
                      activeTab === tab.id
                        ? "bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 font-bold"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                    }`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Sub-filters Cards */}
            {(() => {
              const items = getFilteredItemsByShift();
              const onTimeCount = items.filter(
                (row) => (row.status === "present" || row.status === "half_day") && (row.late_minutes || 0) === 0
              ).length;
              const lateCount = items.filter(
                (row) => (row.status === "present" || row.status === "half_day") && (row.late_minutes || 0) > 0
              ).length;
              const notInYetCount = items.filter(
                (row) => row.status === "absent" || row.status === "not_marked"
              ).length;
              const timeOffCount = items.filter(
                (row) => row.status === "on_leave"
              ).length;

              return (
                <div className="p-5 flex flex-wrap gap-4 border-b border-slate-50 dark:border-slate-850 bg-slate-50/10 dark:bg-slate-900/5">
                  {/* On Time Filter */}
                  <button
                    onClick={() => setSelectedFilter("on-time")}
                    className={`flex-1 min-w-[200px] flex items-center space-x-3 p-4 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer ${
                      selectedFilter === "on-time"
                        ? "border-blue-500 bg-blue-50/20 dark:bg-blue-950/20 shadow-md shadow-blue-500/5"
                        : "border-border hover:border-slate-350 dark:hover:border-slate-700 bg-card"
                    }`}
                  >
                    <CircleDot className={`h-4.5 w-4.5 ${selectedFilter === "on-time" ? "text-blue-500 fill-blue-500" : "text-slate-400 dark:text-slate-500"}`} />
                    <div>
                      <p className="text-xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                        {onTimeCount}
                      </p>
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-1">On Time</p>
                    </div>
                  </button>

                  {/* Late Filter */}
                  <button
                    onClick={() => setSelectedFilter("late")}
                    className={`flex-1 min-w-[200px] flex items-center space-x-3 p-4 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer ${
                      selectedFilter === "late"
                        ? "border-rose-500 bg-rose-50/10 dark:bg-rose-950/10 shadow-md shadow-rose-500/5"
                        : "border-border hover:border-slate-350 dark:hover:border-slate-700 bg-card"
                    }`}
                  >
                    <CircleDot className={`h-4.5 w-4.5 ${selectedFilter === "late" ? "text-rose-500 fill-rose-500" : "text-slate-400 dark:text-slate-500"}`} />
                    <div>
                      <p className="text-xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                        {lateCount}
                      </p>
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-1">Late</p>
                    </div>
                  </button>

                  {/* Not In Yet Filter */}
                  <button
                    onClick={() => setSelectedFilter("not-in")}
                    className={`flex-1 min-w-[200px] flex items-center space-x-3 p-4 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer ${
                      selectedFilter === "not-in"
                        ? "border-amber-500 bg-amber-50/10 dark:bg-amber-950/10 shadow-md shadow-amber-500/5"
                        : "border-border hover:border-slate-350 dark:hover:border-slate-700 bg-card"
                    }`}
                  >
                    <CircleDot className={`h-4.5 w-4.5 ${selectedFilter === "not-in" ? "text-amber-500 fill-amber-500" : "text-slate-400 dark:text-slate-500"}`} />
                    <div>
                      <p className="text-xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                        {notInYetCount}
                      </p>
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-1">Not in Yet</p>
                    </div>
                  </button>

                  {/* Time Off Filter */}
                  <button
                    onClick={() => setSelectedFilter("time-off")}
                    className={`flex-1 min-w-[200px] flex items-center space-x-3 p-4 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer ${
                      selectedFilter === "time-off"
                        ? "border-purple-500 bg-purple-50/20 dark:bg-purple-950/20 shadow-md shadow-purple-500/5"
                        : "border-border hover:border-slate-350 dark:hover:border-slate-700 bg-card"
                    }`}
                  >
                    <CircleDot className={`h-4.5 w-4.5 ${selectedFilter === "time-off" ? "text-purple-500 fill-purple-500" : "text-slate-400 dark:text-slate-500"}`} />
                    <div>
                      <p className="text-xl font-bold text-slate-800 dark:text-slate-100 leading-none">
                        {timeOffCount}
                      </p>
                      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-1">Time Off</p>
                    </div>
                  </button>
                </div>
              );
            })()}

            {/* Table Container */}
            <div className="overflow-x-auto">
              {getTableData().length > 0 ? (
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-border text-slate-500 dark:text-slate-400 bg-slate-50/20 dark:bg-slate-900/10 font-semibold select-none">
                      
                      {/* Employee ID Column */}
                      <th className="py-3 px-5 relative group">
                        <div className="flex items-center">
                          <span
                            onClick={() => handleSort("empId")}
                            className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                          >
                            <span>Employee ID</span>
                            {renderSortIcon("empId")}
                          </span>
                          
                          <span className={`mx-2 text-slate-300 dark:text-slate-750 font-light select-none ${selectedEmpId ? "flex" : "hidden group-hover:flex"}`}>|</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDropdown(activeDropdown === "empId" ? null : "empId");
                            }}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              selectedEmpId
                                ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 flex"
                                : "text-slate-400 dark:text-slate-500 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 hidden group-hover:flex"
                            }`}
                            title="Filter Employee ID"
                          >
                            <Filter className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {activeDropdown === "empId" && (
                          <div className="absolute left-5 top-full mt-1 w-40 rounded-lg border border-border bg-card shadow-lg z-20 py-1 text-slate-755 dark:text-slate-255">
                            <button
                              onClick={() => {
                                setSelectedEmpId(null);
                                setActiveDropdown(null);
                              }}
                              className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                selectedEmpId === null ? "font-bold text-blue-600 dark:text-blue-400" : ""
                              }`}
                            >
                              <span>All IDs</span>
                              {selectedEmpId === null && <Check className="h-3.5 w-3.5" />}
                            </button>
                            {employeeIds.map((id) => (
                              <button
                                key={id}
                                onClick={() => {
                                  setSelectedEmpId(id);
                                  setActiveDropdown(null);
                                }}
                                className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                  selectedEmpId === id ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                }`}
                              >
                                <span>{id}</span>
                                {selectedEmpId === id && <Check className="h-3.5 w-3.5" />}
                              </button>
                            ))}
                          </div>
                        )}
                      </th>

                      {/* Employee Name Column */}
                      <th className="py-3 px-5 relative group">
                        <div className="flex items-center">
                          <span
                            onClick={() => handleSort("empName")}
                            className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                          >
                            <span>Employee Name</span>
                            {renderSortIcon("empName")}
                          </span>
                          
                          <span className={`mx-2 text-slate-300 dark:text-slate-750 font-light select-none ${selectedEmpName.trim() ? "flex" : "hidden group-hover:flex"}`}>|</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDropdown(activeDropdown === "empName" ? null : "empName");
                            }}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              selectedEmpName.trim()
                                ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 flex"
                                : "text-slate-400 dark:text-slate-500 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 hidden group-hover:flex"
                            }`}
                            title="Search Employee Name"
                          >
                            <Filter className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {activeDropdown === "empName" && (
                          <div className="absolute left-5 top-full mt-1 w-48 rounded-lg border border-border bg-card shadow-lg z-20 p-2 text-slate-755 dark:text-slate-255">
                            <input
                              type="text"
                              placeholder="Search name..."
                              value={selectedEmpName}
                              onChange={(e) => setSelectedEmpName(e.target.value)}
                              className="w-full px-2 py-1 text-xs border border-border rounded bg-card text-card-foreground focus:outline-none focus:ring-1 focus:ring-blue-500"
                              autoFocus
                            />
                            {selectedEmpName && (
                              <button
                                onClick={() => {
                                  setSelectedEmpName("");
                                  setActiveDropdown(null);
                                }}
                                className="w-full text-center text-[10px] text-blue-600 dark:text-blue-400 hover:underline mt-1.5 font-bold cursor-pointer"
                              >
                                Clear Search
                              </button>
                            )}
                          </div>
                        )}
                      </th>

                      {/* Department Column */}
                      <th className="py-3 px-5 relative group">
                        <div className="flex items-center">
                          <span
                            onClick={() => handleSort("dept")}
                            className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                          >
                            <span>Department</span>
                            {renderSortIcon("dept")}
                          </span>
                          
                          <span className={`mx-2 text-slate-300 dark:text-slate-700 font-light select-none ${selectedDept ? "flex" : "hidden group-hover:flex"}`}>|</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDropdown(activeDropdown === "dept" ? null : "dept");
                            }}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              selectedDept
                                ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 flex"
                                : "text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-450 hover:bg-slate-100 dark:hover:bg-slate-800 hidden group-hover:flex"
                            }`}
                            title="Filter by Department"
                          >
                            <Filter className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {activeDropdown === "dept" && (
                          <div className="absolute left-5 top-full mt-1 w-48 rounded-lg border border-border bg-card shadow-lg z-20 py-1 text-slate-750 dark:text-slate-255 font-normal">
                            <button
                              onClick={() => {
                                setSelectedDept(null);
                                setActiveDropdown(null);
                              }}
                              className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                selectedDept === null ? "font-bold text-blue-600 dark:text-blue-400" : ""
                              }`}
                            >
                              <span>All Departments</span>
                              {selectedDept === null && <Check className="h-3.5 w-3.5" />}
                            </button>
                            {departments.map((dept) => (
                              <button
                                key={dept}
                                onClick={() => {
                                  setSelectedDept(dept);
                                  setActiveDropdown(null);
                                }}
                                className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between capitalize cursor-pointer ${
                                  selectedDept === dept ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                }`}
                              >
                                <span>{dept}</span>
                                {selectedDept === dept && <Check className="h-3.5 w-3.5" />}
                              </button>
                            ))}
                          </div>
                        )}
                      </th>

                      {/* Designation Column */}
                      <th className="py-3 px-5 relative group">
                        <div className="flex items-center">
                          <span
                            onClick={() => handleSort("desig")}
                            className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                          >
                            <span>Designation</span>
                            {renderSortIcon("desig")}
                          </span>
                          
                          <span className={`mx-2 text-slate-300 dark:text-slate-750 font-light select-none ${selectedDesig ? "flex" : "hidden group-hover:flex"}`}>|</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setActiveDropdown(activeDropdown === "desig" ? null : "desig");
                            }}
                            className={`p-1 rounded transition-colors cursor-pointer ${
                              selectedDesig
                                ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40 flex"
                                : "text-slate-400 dark:text-slate-500 hover:text-slate-650 hover:bg-slate-100 dark:hover:bg-slate-800 hidden group-hover:flex"
                            }`}
                            title="Filter by Designation"
                          >
                            <Filter className="h-3.5 w-3.5" />
                          </button>
                        </div>

                        {activeDropdown === "desig" && (
                          <div className="absolute left-5 top-full mt-1 w-48 rounded-lg border border-border bg-card shadow-lg z-20 py-1 text-slate-755 dark:text-slate-255 font-normal">
                            <button
                              onClick={() => {
                                setSelectedDesig(null);
                                setActiveDropdown(null);
                              }}
                              className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                selectedDesig === null ? "font-bold text-blue-600 dark:text-blue-400" : ""
                              }`}
                            >
                              <span>All Designations</span>
                              {selectedDesig === null && <Check className="h-3.5 w-3.5" />}
                            </button>
                            {designations.map((desig) => (
                              <button
                                key={desig}
                                onClick={() => {
                                  setSelectedDesig(desig);
                                  setActiveDropdown(null);
                                }}
                                className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between capitalize cursor-pointer ${
                                  selectedDesig === desig ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                }`}
                              >
                                <span>{desig}</span>
                                {selectedDesig === desig && <Check className="h-3.5 w-3.5" />}
                              </button>
                            ))}
                          </div>
                        )}
                      </th>

                      <th className="py-3 px-5">First Punch</th>
                      <th className="py-3 px-5">Last Punch</th>
                      <th className="py-3 px-5">Total Working Hours</th>
                      <th className="py-3 px-5">Total Break Hours</th>
                      <th className="py-3 px-5">Overtime Hour</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {getTableData().map((row) => (
                      <tr key={row.employee_id} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/10 transition-colors text-slate-700 dark:text-slate-300">
                        <td className="py-3 px-5 font-semibold text-slate-600 dark:text-slate-400">{row.employee_id}</td>
                        <td className="py-3 px-5 font-bold text-slate-800 dark:text-slate-200 capitalize">{row.employee_name}</td>
                        <td className="py-3 px-5 text-slate-600 dark:text-slate-400 capitalize">{row.department_name}</td>
                        <td className="py-3 px-5 text-slate-600 dark:text-slate-400 capitalize">{row.designation}</td>
                        <td className="py-3 px-5 font-medium text-slate-600 dark:text-slate-300">
                          {formatPunchTime(row.first_punch || row.first_in)}
                        </td>
                        <td className="py-3 px-5 text-slate-400 dark:text-slate-500">
                          {formatPunchTime(row.last_punch || row.last_out)}
                        </td>
                        <td className="py-3 px-5">
                          {row.working_hours !== null && row.working_hours > 0 ? (
                            <span className="flex items-center space-x-1 px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-900/30 text-amber-700 dark:text-amber-400 font-bold w-fit text-[11px]">
                              <span>{formatHours(row.working_hours)}</span>
                              {row.working_hours < 8 && <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />}
                            </span>
                          ) : (
                            <span className="text-slate-400">-</span>
                          )}
                        </td>
                        <td className="py-3 px-5 text-slate-400 dark:text-slate-500">{formatHours(row.break_hours)}</td>
                        <td className="py-3 px-5 text-slate-400 dark:text-slate-500">{formatHours(row.overtime)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="flex flex-col items-center justify-center p-12 text-center">
                  <div className="h-16 w-16 rounded-full bg-blue-50 dark:bg-blue-950/20 flex items-center justify-center text-blue-550 dark:text-blue-400 mb-4 border border-blue-100 dark:border-blue-900/30">
                    <Briefcase className="h-7 w-7" />
                  </div>
                  <p className="text-slate-500 dark:text-slate-400 font-semibold text-sm">No Attendance Data Available</p>
                </div>
              )}
            </div>

            {/* Table footer */}
            <div className="p-3 border-t border-border flex justify-end bg-slate-50/20 dark:bg-slate-800/5">
              <button className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors flex items-center space-x-1 cursor-pointer">
                <span>View More</span>
                <ChevronDown className="h-4 w-4 rotate-270" />
              </button>
            </div>
          </div>
        )}

        {/* Row 3: Shift Summary, Department Summary, Device sync, Pending approvals grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Widget 1: Today's Shift Wise Attendance Summary */}
          {isShiftsLoading ? (
            <WidgetSkeleton title="Today's Shift Wise Attendance Summary" />
          ) : shiftsError ? (
            <ErrorWidget title="Today's Shift Wise Attendance Summary" error={shiftsError} />
          ) : (
            <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden flex flex-col justify-between">
              <div>
                <div className="p-4 border-b border-border bg-slate-50/30 dark:bg-slate-900/10">
                  <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs tracking-tight">
                    Today&apos;s Shift Wise Attendance Summary
                  </h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border text-slate-500 dark:text-slate-400 font-semibold select-none">
                        
                        {/* Shift Name Column */}
                        <th className="py-2.5 px-4 relative">
                          <div className="flex items-center">
                            <span
                              onClick={() => toggleFilterVisibility("shiftName")}
                              className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                            >
                              <span>Shift Name</span>
                              <ArrowUpDown className="h-3 w-3 opacity-50" />
                            </span>
                            
                            {(visibleFilters["shiftName"] || selectedShift) && (
                              <>
                                <span className="mx-2 text-slate-355 dark:text-slate-700 font-light select-none">|</span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveDropdown(activeDropdown === "shiftName" ? null : "shiftName");
                                  }}
                                  className={`p-0.5 rounded transition-colors cursor-pointer ${
                                    selectedShift
                                      ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40"
                                      : "text-slate-400 dark:text-slate-500 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                                  }`}
                                  title="Filter by Shift Name"
                                >
                                  <Filter className="h-3 w-3" />
                                </button>
                              </>
                            )}
                          </div>

                          {activeDropdown === "shiftName" && (
                            <div className="absolute left-4 top-full mt-1 w-44 rounded-lg border border-border bg-card shadow-lg z-20 py-1 text-slate-755 dark:text-slate-255">
                              <button
                                onClick={() => {
                                  setSelectedShift(null);
                                  setActiveDropdown(null);
                                }}
                                className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                  selectedShift === null ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                }}`}
                              >
                                <span>All Shifts</span>
                                {selectedShift === null && <Check className="h-3.5 w-3.5" />}
                              </button>
                              {shiftNames.map((shift) => (
                                <button
                                  key={shift}
                                  onClick={() => {
                                    setSelectedShift(shift);
                                    setActiveDropdown(null);
                                  }}
                                  className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                    selectedShift === shift ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                  }`}
                                >
                                  <span>{shift}</span>
                                  {selectedShift === shift && <Check className="h-3.5 w-3.5" />}
                                </button>
                              ))}
                            </div>
                          )}
                        </th>

                        <th className="py-2.5 px-4 text-center">On Time</th>
                        <th className="py-2.5 px-4 text-center">Late</th>
                        <th className="py-2.5 px-4 text-center">Not In Yet</th>
                        <th className="py-2.5 px-4 text-center">Time Off</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-slate-700 dark:text-slate-300">
                      {getShiftData().map((row) => (
                        <tr key={row.shift_id} className="hover:bg-slate-50/30 dark:hover:bg-slate-800/10">
                          <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400">{row.shift_name}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.present}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.late}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.absent}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.on_leave}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Widget 2: Today's Department Wise Attendance Summary */}
          {isDeptLoading ? (
            <WidgetSkeleton title="Today's Department Wise Attendance Summary" />
          ) : deptError ? (
            <ErrorWidget title="Today's Department Wise Attendance Summary" error={deptError} />
          ) : (
            <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden flex flex-col justify-between">
              <div>
                <div className="p-4 border-b border-border bg-slate-50/30 dark:bg-slate-900/10">
                  <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs tracking-tight">
                    Today&apos;s Department Wise Attendance Summary
                  </h4>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border text-slate-500 dark:text-slate-400 font-semibold select-none">
                        
                        {/* Department Summary Name Column */}
                        <th className="py-2.5 px-4 relative">
                          <div className="flex items-center">
                            <span
                              onClick={() => toggleFilterVisibility("deptName")}
                              className="flex items-center space-x-1 hover:text-slate-700 dark:hover:text-slate-200 cursor-pointer select-none"
                            >
                              <span>Department Name</span>
                              <ArrowUpDown className="h-3 w-3 opacity-50" />
                            </span>
                            
                            {(visibleFilters["deptName"] || selectedDeptSummary) && (
                              <>
                                <span className="mx-2 text-slate-355 dark:text-slate-700 font-light select-none">|</span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setActiveDropdown(activeDropdown === "deptName" ? null : "deptName");
                                  }}
                                  className={`p-0.5 rounded transition-colors cursor-pointer ${
                                    selectedDeptSummary
                                      ? "text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-950/40"
                                      : "text-slate-400 dark:text-slate-500 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800"
                                  }`}
                                  title="Filter by Department Name"
                                >
                                  <Filter className="h-3 w-3" />
                                </button>
                              </>
                            )}
                          </div>

                          {activeDropdown === "deptName" && (
                            <div className="absolute left-4 top-full mt-1 w-44 rounded-lg border border-border bg-card shadow-lg z-20 py-1 text-slate-755 dark:text-slate-255">
                              <button
                                onClick={() => {
                                  setSelectedDeptSummary(null);
                                  setActiveDropdown(null);
                                }}
                                className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between cursor-pointer ${
                                  selectedDeptSummary === null ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                }`}
                              >
                                <span>All Departments</span>
                                {selectedDeptSummary === null && <Check className="h-3.5 w-3.5" />}
                              </button>
                              {deptSummaryNames.map((dept) => (
                                <button
                                  key={dept}
                                  onClick={() => {
                                    setSelectedDeptSummary(dept);
                                    setActiveDropdown(null);
                                  }}
                                  className={`w-full text-left px-3 py-1.5 hover:bg-slate-50 dark:hover:bg-slate-800 text-xs flex items-center justify-between capitalize cursor-pointer ${
                                    selectedDeptSummary === dept ? "font-bold text-blue-600 dark:text-blue-400" : ""
                                  }`}
                                >
                                  <span>{dept}</span>
                                  {selectedDeptSummary === dept && <Check className="h-3.5 w-3.5" />}
                                </button>
                              ))}
                            </div>
                          )}
                        </th>

                        <th className="py-2.5 px-4 text-center">Checked In</th>
                        <th className="py-2.5 px-4 text-center">Not In Yet</th>
                        <th className="py-2.5 px-4 text-center">Time Off</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-slate-700 dark:text-slate-300">
                      {getDeptSummaryData().map((row) => (
                        <tr key={row.name} className="hover:bg-slate-50/30 dark:hover:bg-slate-800/10">
                          <td className="py-3 px-4 font-semibold text-slate-600 dark:text-slate-400 capitalize">{row.name}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.checkedIn}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.notIn}</td>
                          <td className="py-3 px-4 text-center font-medium">{row.off}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Widget 3: Device Sync Status */}
          {isDevicesLoading ? (
            <WidgetSkeleton title="Device Sync Status" />
          ) : devicesError ? (
            <ErrorWidget title="Device Sync Status" error={devicesError} />
          ) : (
            <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden flex flex-col justify-between">
              <div className="p-4 border-b border-border bg-slate-50/30 dark:bg-slate-900/10 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs tracking-tight">
                    Device Sync Status
                  </h4>
                  <span className="bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold text-[10px] px-1.5 py-0.5 rounded-full">
                    {devicesData?.total || 0}
                  </span>
                </div>
                <button
                  onClick={handleSyncDevices}
                  disabled={isSyncing}
                  className="h-7 w-7 rounded-full bg-blue-50 dark:bg-blue-950/40 hover:bg-blue-100 dark:hover:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400 hover:text-blue-700 transition-all cursor-pointer shadow-xs disabled:opacity-50"
                  title="Synchronize biometric logs"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                </button>
              </div>
              
              <div className="p-5 flex-1 space-y-3">
                {devicesData?.items && devicesData.items.length > 0 ? (
                  devicesData.items.map((device) => (
                    <div key={device.id} className="p-4 border border-border rounded-xl bg-card flex items-center justify-between shadow-xs">
                      <div className="space-y-1.5">
                        <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                          {device.device_name} ({device.total_logs})
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono leading-none">
                          ID: {device.mac_address || device.serial_number}
                        </p>
                        <p className="text-[9px] text-slate-400 dark:text-slate-500 font-semibold leading-none pt-0.5">
                          LAST SYNC: {formatDeviceDate(device.last_sync_at)}
                        </p>
                      </div>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border capitalize ${
                        device.status === "online"
                          ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-900/30"
                          : "bg-rose-50 dark:bg-rose-950/20 text-rose-600 dark:text-rose-400 border-rose-100 dark:border-rose-900/30"
                      }`}>
                        {device.status}
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="py-6 text-center text-slate-400">
                    No devices registered.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Widget 4: Pending Approvals */}
          {isApprovalsLoading ? (
            <WidgetSkeleton title="Pending Approvals" />
          ) : approvalsError ? (
            <ErrorWidget title="Pending Approvals" error={approvalsError} />
          ) : (
            <div className="bg-card text-card-foreground rounded-xl border border-border shadow-xs overflow-hidden flex flex-col justify-between">
              <div className="p-4 border-b border-border bg-slate-50/30 dark:bg-slate-900/10 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h4 className="font-bold text-slate-800 dark:text-slate-100 text-xs tracking-tight">
                    Pending Approvals
                  </h4>
                  <span className="bg-blue-50 dark:bg-blue-950/30 text-blue-600 dark:text-blue-400 font-bold text-[10px] px-1.5 py-0.5 rounded-full">
                    {pendingApprovals.length}
                  </span>
                </div>
                <button
                  onClick={() => router.push("/approvals")}
                  className="text-[11px] font-bold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors flex items-center cursor-pointer"
                >
                  <span>View More</span>
                </button>
              </div>

              <div className="p-4 flex-1 space-y-3">
                {pendingApprovals.length > 0 ? (
                  pendingApprovals.map((item: { id: number | string; requester_name: string; request_type: string; submitted_at: string }) => {
                    const isLeave = item.request_type.toLowerCase().includes("leave");
                    return (
                      <div
                        key={item.id}
                        className="p-3 border border-border rounded-xl bg-card hover:bg-slate-50/50 dark:hover:bg-slate-800/20 flex items-center justify-between shadow-xs transition-colors"
                      >
                        <div className="flex items-center space-x-3 min-w-0">
                          {/* Avatar container */}
                          <div className={`h-8 w-8 rounded-full flex items-center justify-center shrink-0 text-white ${
                            !isLeave ? "bg-blue-600" : "bg-amber-500"
                          }`}>
                            {!isLeave ? <Clock className="h-4 w-4" /> : <Trees className="h-4 w-4" />}
                          </div>
                          
                          <div className="min-w-0">
                            <p className="text-xs font-bold text-slate-800 dark:text-slate-200 leading-tight truncate">
                              #{item.id} - {item.requester_name}
                            </p>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-none truncate mt-0.5">
                              {isLeave ? "Leave Request" : "Punch Correction"}
                            </p>
                            <p className="text-[9px] text-slate-400 dark:text-slate-500 font-semibold leading-none pt-1">
                              {formatApprovalDate(item.submitted_at)}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center space-x-2 shrink-0">
                          {/* Approve button */}
                          <button
                            onClick={() => handleApprovalAction(item.id, "approve")}
                            className="h-7 w-7 rounded-full border border-emerald-200 dark:border-emerald-900 bg-emerald-50 dark:bg-emerald-950/20 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 flex items-center justify-center text-emerald-600 dark:text-emerald-400 transition-all cursor-pointer shadow-2xs"
                            title="Approve request"
                          >
                            <Check className="h-4 w-4" />
                          </button>

                          {/* Reject button */}
                          <button
                            onClick={() => handleApprovalAction(item.id, "reject")}
                            className="h-7 w-7 rounded-full border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/20 hover:bg-rose-100 dark:hover:bg-rose-900/40 flex items-center justify-center text-rose-600 dark:text-rose-400 transition-all cursor-pointer shadow-2xs"
                            title="Reject request"
                          >
                            <X className="h-4 w-4" />
                          </button>

                          {/* Dropdown trigger */}
                          <button className="h-7 w-5 rounded flex items-center justify-center text-slate-400 hover:text-slate-655 transition-all cursor-pointer">
                            <ChevronDown className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="py-6 text-center">
                    <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
                    <p className="text-slate-500 dark:text-slate-400 font-semibold text-xs">All caught up!</p>
                    <p className="text-slate-400 dark:text-slate-500 text-[10px] mt-0.5">No pending leave or punch correction requests.</p>
                  </div>
                )}
              </div>
            </div>
          )}

        </div>

      </div>

      {/* Drawer Overlay Backdrop */}
      {drawerTitle && (
        <div
          onClick={() => setDrawerTitle(null)}
          className="fixed inset-0 bg-black/40 backdrop-blur-xs z-40 transition-opacity duration-300"
        />
      )}

      {/* Slide-out Side Drawer Panel */}
      <div
        className={`fixed right-0 top-0 bottom-0 w-full sm:w-[450px] bg-card border-l border-border shadow-2xl z-50 flex flex-col transform transition-transform duration-300 ease-in-out ${
          drawerTitle ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {drawerTitle && (
          <>
            {/* Drawer Header */}
            <div className={`py-3.5 px-5 font-bold border-b-2 flex items-center justify-between select-none ${
              drawerTitle === "Total Employees"
                ? "bg-blue-50 dark:bg-blue-950/20 text-blue-800 dark:text-blue-300 border-blue-500"
                : drawerTitle === "Currently Working"
                ? "bg-emerald-50 dark:bg-emerald-950/20 text-emerald-800 dark:text-emerald-300 border-emerald-500"
                : drawerTitle === "On Break"
                ? "bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 border-amber-500"
                : drawerTitle === "Time Off"
                ? "bg-indigo-50 dark:bg-indigo-950/20 text-indigo-800 dark:text-indigo-300 border-indigo-500"
                : "bg-rose-50 dark:bg-rose-950/20 text-rose-800 dark:text-rose-300 border-rose-500"
            }`}>
              <span className="text-sm tracking-tight">{drawerTitle}</span>
              <button
                onClick={() => setDrawerTitle(null)}
                className="p-1 rounded hover:bg-slate-200/50 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors cursor-pointer"
                title="Close panel"
              >
                <X className="h-4.5 w-4.5" />
              </button>
            </div>
            
            {/* Drawer Table/Content Body */}
            <div className="flex-1 overflow-y-auto p-5">
              {getDrawerEmployees().length > 0 ? (
                <div className="border border-border rounded-lg overflow-hidden bg-card shadow-xs">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-slate-50/50 dark:bg-slate-900/20 border-b border-border text-slate-500 dark:text-slate-400 font-bold select-none">
                        <th className="py-2.5 px-4 w-28 border-r border-border">Employee ID</th>
                        <th className="py-2.5 px-4">Employee Name</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-slate-700 dark:text-slate-350">
                      {getDrawerEmployees().map((emp) => (
                        <tr key={emp.id} className="hover:bg-slate-50/30 dark:hover:bg-slate-800/10 transition-colors">
                          <td className="py-2.5 px-4 font-semibold text-slate-600 dark:text-slate-400 border-r border-border">{emp.id}</td>
                          <td className="py-2.5 px-4 font-bold text-slate-800 dark:text-slate-200 capitalize">{emp.name}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="py-20 text-center">
                  <CircleDot className="h-10 w-10 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
                  <p className="text-slate-500 dark:text-slate-400 font-bold text-xs">No records found</p>
                  <p className="text-slate-455 dark:text-slate-500 text-[10px] mt-1 max-w-[250px] mx-auto leading-relaxed">
                    There are no employees registered in the &quot;{drawerTitle}&quot; status category today.
                  </p>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </ProtectedRoute>
  );
}
