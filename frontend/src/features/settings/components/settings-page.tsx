"use client";

import React, { useState, useId } from "react";
import {
  Clock,
  CalendarCheck,
  Cpu,
  Users,
  CreditCard,
  Sliders,
  FileText,
  AlertCircle,
  RefreshCw,
  FolderOpen,
  Loader2,
  ExternalLink,
  Building2,
} from "lucide-react";
import { toast } from "sonner";
import { useSettings, usePayrollSettings, useUpdateSettings } from "../hooks/use-settings";

export type UIState = "normal" | "loading" | "empty" | "error";

export interface SettingsNavItem {
  id: string;
  label: string;
  icon: React.ElementType;
}

const SETTINGS_NAV_ITEMS: SettingsNavItem[] = [
  { id: "shifts", label: "Shifts & Time Management", icon: Clock },
  { id: "attendance", label: "Attendance Management", icon: CalendarCheck },
  { id: "hardware", label: "Hardware Management", icon: Cpu },
  { id: "employee", label: "Employee Management", icon: Users },
  { id: "payroll", label: "Payroll Management", icon: CreditCard },
  { id: "configurations", label: "Configurations", icon: Sliders },
  { id: "salary-slip", label: "Salary Slip", icon: FileText },
  { id: "organization", label: "Organization Management", icon: Building2 },
];

export function SettingsPage() {
  // Navigation & UI State
  const [activeTab, setActiveTab] = useState<string>("shifts");
  const [uiState, setUiState] = useState<UIState>("normal");
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [deviceSyncTime, setDeviceSyncTime] = useState<string>("4:51 PM");

  // Payroll Management Form State
  // Payroll state values use raw backend enum strings as-is (no UI label mapping needed)
  const [workingHourType, setWorkingHourType] = useState<string>("fixed");
  const [fullDayWorkingHours, setFullDayWorkingHours] = useState<string>("09:00");
  const [halfDayWorkingHours, setHalfDayWorkingHours] = useState<string>("04:30");
  const [attendanceMode, setAttendanceMode] = useState<string>("consider_all_punch");
  const [offDayCompensation, setOffDayCompensation] = useState<string>("paid");
  const [weekOffMultiplier, setWeekOffMultiplier] = useState<string>("1.0");
  const [dailyWageCalculation, setDailyWageCalculation] = useState<string>("calendar_days");
  const [overtimeType, setOvertimeType] = useState<string>("multiplier");
  const [overtimeMultiplier, setOvertimeMultiplier] = useState<string>("1.5");
  const [overtimeBufferPeriod, setOvertimeBufferPeriod] = useState<string>("00:30");
  const [overtimePeriod, setOvertimePeriod] = useState<string>("daily");

  const [fullDayPenalty, setFullDayPenalty] = useState<boolean>(false);
  const [halfDayPenalty, setHalfDayPenalty] = useState<boolean>(false);
  const [lateComingPenalty, setLateComingPenalty] = useState<boolean>(false);
  const [graceTime, setGraceTime] = useState<string>("00:15");

  // Integration Codes State
  const [syncCode, setSyncCode] = useState<string>("delfawno");
  const [passCode, setPassCode] = useState<string>("050226");

  // Salary Slip Form State
  const [salarySlipCompany, setSalarySlipCompany] = useState<string>("Itcode Infotech");
  const [salarySlipAddress, setSalarySlipAddress] = useState<string>("C1 - 1003, Pragti it park , mota varachha, surat - 394105");
  const [salarySlipContact, setSalarySlipContact] = useState<string>("Contact");
  const [salarySlipEmail, setSalarySlipEmail] = useState<string>("");
  const [autoReleasePayslip, setAutoReleasePayslip] = useState<boolean>(true);
  const [branchWisePayslip, setBranchWisePayslip] = useState<boolean>(false);

  const [showLogo, setShowLogo] = useState<boolean>(true);
  const [showSignature, setShowSignature] = useState<boolean>(true);
  const [showPf, setShowPf] = useState<boolean>(true);
  const [showEsic, setShowEsic] = useState<boolean>(true);
  const [showLeaveBalance, setShowLeaveBalance] = useState<boolean>(true);

  // Settings State (Static/Mock presentation layer)
  const [settings, setSettings] = useState({
    // Shifts & Time Management
    advanceShift: false,
    autoShiftAssign: true,
    flexibleHours: false,

    // Attendance Management
    enableRegularization: false,
    enablePhotoPunch: false,
    autoPunchOut: true,
    overtimeApproval: true,
    geoFencing: false,

    // Hardware Management
    biometricSync: true,
    realtimeAlerts: true,
    autoPushData: false,

    // Employee Management
    autoEmployeeCode: true,
    probationTracking: true,
    documentExpiryAlerts: true,

    // Payroll Management
    autoTaxCalculation: true,
    directDepositApproval: false,
    prorateSalary: true,

    // Configurations
    auditLogging: true,
    emailNotifications: true,
    maintenanceMode: false,

    // Salary Slip
    showCompanyLogo: true,
    passwordProtectPdf: true,
    hideYtdTotals: false,

    // Organization Management
    multiBranchSupport: true,
    allowBranchTransfer: false,
    centralizedHolidayCalendar: true,
  });

  const advanceShiftHelpId = useId();
  const advanceShiftLabelId = useId();

  const handleToggle = (key: keyof typeof settings) => {
    setSettings((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
    setIsDirty(true);
  };

  // React Query Settings Data & Mutation Integration
  const { data: serverSettings, isLoading: isQueryLoading, isError: isQueryError, refetch } = useSettings();
  const { data: serverPayrollSettings } = usePayrollSettings();
  const updateSettingsMutation = useUpdateSettings();

  // Populate state when serverSettings changes from API
  React.useEffect(() => {
    if (serverSettings) {
      if (serverSettings.organization) {
        setSettings((prev) => ({
          ...prev,
          advanceShift: serverSettings.organization?.advance_shift_enabled ?? prev.advanceShift,
          enableRegularization: serverSettings.organization?.enable_regularization ?? prev.enableRegularization,
          enablePhotoPunch: serverSettings.organization?.enable_photo_punch ?? prev.enablePhotoPunch,
        }));
        if (serverSettings.organization.device_sync_time) {
          setDeviceSyncTime(serverSettings.organization.device_sync_time);
        }
        if (serverSettings.organization.sync_code) {
          setSyncCode(serverSettings.organization.sync_code);
        }
        if (serverSettings.organization.pass_code) {
          setPassCode(serverSettings.organization.pass_code);
        }
      }

      if (serverSettings.salary_slip) {
        setSalarySlipCompany(serverSettings.salary_slip.company_name || "Itcode Infotech");
        setSalarySlipAddress(serverSettings.salary_slip.company_address || "C1 - 1003, Pragti it park, mota varachha, surat - 394105");
        setSalarySlipContact(serverSettings.salary_slip.company_contact || "Contact");
        setSalarySlipEmail(serverSettings.salary_slip.company_website_email || "");
        setAutoReleasePayslip(serverSettings.salary_slip.auto_release_payslip ?? true);
        setBranchWisePayslip(serverSettings.salary_slip.branch_wise_payslip ?? false);
      }
    }
  }, [serverSettings]);

  // Populate payroll state from server — values are stored as raw backend strings directly
  React.useEffect(() => {
    if (serverPayrollSettings) {
      setWorkingHourType(serverPayrollSettings.working_hour_type);
      setFullDayWorkingHours(String(serverPayrollSettings.full_day_working_hours).substring(0, 5));
      setHalfDayWorkingHours(String(serverPayrollSettings.half_day_working_hours).substring(0, 5));
      setAttendanceMode(serverPayrollSettings.attendance_mode);
      setOffDayCompensation(serverPayrollSettings.off_day_compensation);
      setWeekOffMultiplier(String(serverPayrollSettings.off_day_wage_multiplier));
      setDailyWageCalculation(serverPayrollSettings.daily_wage_formula);
      setOvertimeType(serverPayrollSettings.overtime_type);
      setOvertimeMultiplier(String(serverPayrollSettings.overtime_hourly_multiplier));
      setOvertimeBufferPeriod(String(serverPayrollSettings.overtime_buffer_period).substring(0, 5));
      setOvertimePeriod(serverPayrollSettings.overtime_period_interval ?? "daily");
      setFullDayPenalty(serverPayrollSettings.full_day_penalty_enabled);
      setHalfDayPenalty(serverPayrollSettings.half_day_penalty_enabled);
      setLateComingPenalty(serverPayrollSettings.late_coming_penalty_enabled);
      setGraceTime(String(serverPayrollSettings.grace_time).substring(0, 5));
    }
  }, [serverPayrollSettings]);

  // Derived effective UI state
  const effectiveState: UIState =
    uiState !== "normal"
      ? uiState
      : isQueryLoading
      ? "loading"
      : isQueryError
      ? "error"
      : "normal";

  // Helper to format 12h or 24h time strings to ISO 24h format HH:MM:SS for backend Pydantic validation
  const formatTimeTo24h = (timeStr: string): string => {
    if (!timeStr) return "16:51:00";
    const trimmed = timeStr.trim();
    if (/^\d{1,2}:\d{2}(:\d{2})?$/.test(trimmed)) {
      const parts = trimmed.split(":");
      return `${parts[0].padStart(2, "0")}:${parts[1].padStart(2, "0")}:${parts[2] ? parts[2].padStart(2, "0") : "00"}`;
    }
    const match = trimmed.match(/^(\d{1,2}):(\d{2})\s*(AM|PM)?$/i);
    if (match) {
      let hours = parseInt(match[1], 10);
      const minutes = match[2];
      const period = (match[3] || "").toUpperCase();
      if (period === "PM" && hours < 12) hours += 12;
      if (period === "AM" && hours === 12) hours = 0;
      return `${hours.toString().padStart(2, "0")}:${minutes}:00`;
    }
    return "16:51:00";
  };

  const handleSave = async () => {
    try {

      const validPassCode =
        passCode && passCode !== "********" && passCode.trim() !== ""
          ? passCode.trim()
          : undefined;

      const validSyncCode =
        syncCode && syncCode !== "********" && syncCode.trim() !== ""
          ? syncCode.trim()
          : undefined;

      const formattedTime = formatTimeTo24h(deviceSyncTime);

      // State values are already raw backend enum strings — send directly
      await updateSettingsMutation.mutateAsync({
        orgSettings: {
          advance_shift_enabled: settings.advanceShift,
          enable_regularization: settings.enableRegularization,
          enable_photo_punch: settings.enablePhotoPunch,
          device_sync_time: formattedTime,
          ...(validSyncCode ? { sync_code: validSyncCode } : {}),
          ...(validPassCode ? { pass_code: validPassCode } : {}),
        },
        salarySlipSettings: {
          company_name: salarySlipCompany || "Itcode Infotech",
          company_address: salarySlipAddress || "Surat",
          company_contact: salarySlipContact || "Contact",
          // Send website/email value as-is — field accepts both URLs and email addresses
          company_website_email: salarySlipEmail.trim() || null,
          auto_release_payslip: autoReleasePayslip,
          branch_wise_payslip: branchWisePayslip,
        },
        payrollSettings: {
          working_hour_type: workingHourType,
          full_day_working_hours: fullDayWorkingHours.length === 5 ? `${fullDayWorkingHours}:00` : fullDayWorkingHours,
          half_day_working_hours: halfDayWorkingHours.length === 5 ? `${halfDayWorkingHours}:00` : halfDayWorkingHours,
          attendance_mode: attendanceMode,
          off_day_compensation: offDayCompensation,
          off_day_wage_multiplier: parseFloat(weekOffMultiplier) || 1,
          daily_wage_formula: dailyWageCalculation,
          overtime_type: overtimeType,
          overtime_hourly_multiplier: parseFloat(overtimeMultiplier) || 0,
          overtime_buffer_period: overtimeBufferPeriod.length === 5 ? `${overtimeBufferPeriod}:00` : overtimeBufferPeriod,
          overtime_period_interval: overtimePeriod,
          full_day_penalty_enabled: fullDayPenalty,
          half_day_penalty_enabled: halfDayPenalty,
          late_coming_penalty_enabled: lateComingPenalty,
          grace_time: graceTime.length === 5 ? `${graceTime}:00` : graceTime,
        },
      });
      setIsDirty(false);
    } catch {
      // Toast notification is handled in mutation hook
    }
  };

  const handleCancel = () => {
    if (serverSettings) {
      if (serverSettings.organization) {
        setSettings((prev) => ({
          ...prev,
          advanceShift: serverSettings.organization?.advance_shift_enabled ?? prev.advanceShift,
          enableRegularization: serverSettings.organization?.enable_regularization ?? prev.enableRegularization,
          enablePhotoPunch: serverSettings.organization?.enable_photo_punch ?? prev.enablePhotoPunch,
        }));
        if (serverSettings.organization.device_sync_time) {
          setDeviceSyncTime(serverSettings.organization.device_sync_time);
        }
      }
    }
    setIsDirty(false);
    toast.info("Changes reverted");
  };

  // Keyboard navigation for sidebar tab list
  const handleKeyDownNav = (
    e: React.KeyboardEvent<HTMLButtonElement>,
    index: number
  ) => {
    let nextIndex = index;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      nextIndex = (index + 1) % SETTINGS_NAV_ITEMS.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      nextIndex =
        (index - 1 + SETTINGS_NAV_ITEMS.length) % SETTINGS_NAV_ITEMS.length;
    } else if (e.key === "Home") {
      e.preventDefault();
      nextIndex = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      nextIndex = SETTINGS_NAV_ITEMS.length - 1;
    }

    if (nextIndex !== index) {
      const nextTab = SETTINGS_NAV_ITEMS[nextIndex];
      setActiveTab(nextTab.id);
      const el = document.getElementById(`settings-tab-${nextTab.id}`);
      el?.focus();
    }
  };

  const currentNav =
    SETTINGS_NAV_ITEMS.find((item) => item.id === activeTab) ||
    SETTINGS_NAV_ITEMS[0];

  return (
    <div className="w-full space-y-4">
      {/* UI State Controls (For testing Normal, Loading, Empty, Error states) */}
      <div
        className="flex items-center justify-between bg-slate-100 dark:bg-slate-900 px-4 py-2 rounded-lg border border-slate-200 dark:border-slate-800 text-xs"
        aria-label="UI State Controller"
      >
        <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
          <Sliders className="h-3.5 w-3.5" />
          <span className="font-semibold uppercase tracking-wider text-[10px]">
            UI State Switcher:
          </span>
        </div>
        <div className="flex items-center gap-1.5" role="group" aria-label="Select UI State">
          {(["normal", "loading", "empty", "error"] as UIState[]).map((state) => (
            <button
              key={state}
              type="button"
              onClick={() => setUiState(state)}
              className={`px-2.5 py-1 rounded font-medium capitalize transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                uiState === state
                  ? "bg-blue-600 text-white shadow-xs"
                  : "bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700"
              }`}
              aria-pressed={uiState === state}
            >
              {state}
            </button>
          ))}
        </div>
      </div>

      {/* Main Settings Card Container */}
      <div className="bg-white dark:bg-slate-950 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden min-h-[580px] flex flex-col">
        {/* Settings Header */}
        <div className="px-6 py-4 border-b border-slate-200/80 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-950">
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">
              Settings
            </h1>
          </div>
        </div>

        {/* Settings Content Area (Left Nav + Right Panel) */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0">
          {/* Left Navigation Panel */}
          <nav
            aria-label="Settings navigation"
            className="w-full md:w-72 border-r-0 md:border-r border-b md:border-b-0 border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-950 p-3 shrink-0"
          >
            {uiState === "loading" ? (
              <div className="space-y-2 p-2" aria-label="Loading navigation">
                {[...Array(8)].map((_, i) => (
                  <div
                    key={i}
                    className="h-10 bg-slate-100 dark:bg-slate-850 rounded-lg animate-pulse"
                  />
                ))}
              </div>
            ) : (
              <div
                role="tablist"
                aria-orientation="vertical"
                aria-label="Settings Categories"
                className="space-y-1"
              >
                {SETTINGS_NAV_ITEMS.map((item, index) => {
                  const isActive = activeTab === item.id;
                  const Icon = item.icon;
                  return (
                    <button
                      key={item.id}
                      id={`settings-tab-${item.id}`}
                      role="tab"
                      type="button"
                      aria-selected={isActive}
                      aria-controls={`settings-panel-${item.id}`}
                      tabIndex={isActive ? 0 : -1}
                      onClick={() => setActiveTab(item.id)}
                      onKeyDown={(e) => handleKeyDownNav(e, index)}
                      className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg text-left transition-all duration-150 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                        isActive
                          ? "bg-[#eef5ff] dark:bg-blue-950/60 text-[#007bff] dark:text-blue-400 font-semibold shadow-2xs"
                          : "text-slate-700 dark:text-slate-300 hover:bg-slate-100/70 dark:hover:bg-slate-900/60 hover:text-slate-900 dark:hover:text-slate-100"
                      }`}
                    >
                      <Icon
                        className={`h-4 w-4 shrink-0 transition-colors ${
                          isActive
                            ? "text-[#007bff] dark:text-blue-400"
                            : "text-slate-400 dark:text-slate-500 group-hover:text-slate-600 dark:group-hover:text-slate-400"
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </nav>

          {/* Right Content Area */}
          <main
            id={`settings-panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`settings-tab-${activeTab}`}
            className="flex-1 flex flex-col justify-between bg-white dark:bg-slate-950 p-6 md:p-8 overflow-y-auto"
          >
            {/* UI State: LOADING */}
            {effectiveState === "loading" && (
              <div
                className="space-y-6 animate-pulse flex-1"
                aria-label="Loading settings content"
              >
                <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded-md" />
                <div className="space-y-4 pt-4">
                  <div className="flex items-center justify-between p-4 rounded-lg border border-slate-100 dark:border-slate-800">
                    <div className="space-y-2">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                      <div className="h-3 w-64 bg-slate-150 dark:bg-slate-850 rounded" />
                    </div>
                    <div className="h-6 w-11 bg-slate-200 dark:bg-slate-800 rounded-full" />
                  </div>
                </div>
              </div>
            )}

            {/* UI State: ERROR */}
            {effectiveState === "error" && (
              <div
                className="flex-1 flex flex-col items-center justify-center p-8 text-center"
                role="alert"
                aria-live="assertive"
              >
                <div className="h-12 w-12 rounded-full bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center justify-center mb-4">
                  <AlertCircle className="h-6 w-6" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">
                  Failed to Load Settings
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-5">
                  An unexpected error occurred while fetching settings configuration. Please try again.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setUiState("normal");
                    refetch();
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  Retry Loading
                </button>
              </div>
            )}

            {/* UI State: EMPTY */}
            {effectiveState === "empty" && (
              <div
                className="flex-1 flex flex-col items-center justify-center p-8 text-center"
                aria-label="Empty state"
              >
                <div className="h-12 w-12 rounded-full bg-slate-100 dark:bg-slate-900 text-slate-400 dark:text-slate-500 flex items-center justify-center mb-4">
                  <FolderOpen className="h-6 w-6" />
                </div>
                <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">
                  No Settings Available
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-5">
                  There are currently no configurable parameters under {currentNav.label}.
                </p>
                <button
                  type="button"
                  onClick={() => setUiState("normal")}
                  className="px-4 py-2 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-900 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Reset View
                </button>
              </div>
            )}

            {/* UI State: NORMAL */}
            {effectiveState === "normal" && (
              <div className="flex-1 flex flex-col justify-between">
                <div>
                  {/* Content Header Title */}
                  <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-6 border-b border-slate-100 dark:border-slate-800 pb-3">
                    {currentNav.label}
                  </h2>

                  {/* 1. SHIFTS & TIME MANAGEMENT (Primary Reference Screen) */}
                  {activeTab === "shifts" && (
                    <div className="space-y-6">
                      {/* Advance Shift Control matching reference layout */}
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 py-2">
                        <div className="space-y-1">
                          <label
                            id={advanceShiftLabelId}
                            htmlFor="advance-shift-toggle"
                            className="text-sm font-bold text-slate-900 dark:text-slate-100 cursor-pointer"
                          >
                            Advance Shift
                          </label>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            This is the main profile that will be visible for everyone.
                          </p>
                        </div>

                        <div className="flex items-center gap-3 shrink-0 pt-0.5">
                          <button
                            id="advance-shift-toggle"
                            role="switch"
                            type="button"
                            aria-checked={settings.advanceShift}
                            aria-labelledby={advanceShiftLabelId}
                            aria-describedby={advanceShiftHelpId}
                            onClick={() => handleToggle("advanceShift")}
                            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                              settings.advanceShift
                                ? "bg-[#007bff]"
                                : "bg-slate-300 dark:bg-slate-700"
                            }`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                settings.advanceShift
                                  ? "translate-x-5"
                                  : "translate-x-0"
                              }`}
                            />
                          </button>
                          <span
                            id={advanceShiftHelpId}
                            className="text-xs text-slate-500 dark:text-slate-400 font-normal"
                          >
                            (Basic shift stays active unless advanced shift is enabled)
                          </span>
                        </div>
                      </div>

                      {/* Additional Shift Settings */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 space-y-4">
                        <div className="flex items-center justify-between py-2">
                          <div>
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                              Auto-assign Shift by Roster
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                              Automatically map daily punch logs to scheduled roster shifts.
                            </p>
                          </div>
                          <button
                            role="switch"
                            type="button"
                            aria-checked={settings.autoShiftAssign}
                            aria-label="Auto-assign Shift by Roster"
                            onClick={() => handleToggle("autoShiftAssign")}
                            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                              settings.autoShiftAssign
                                ? "bg-[#007bff]"
                                : "bg-slate-300 dark:bg-slate-700"
                            }`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                settings.autoShiftAssign
                                  ? "translate-x-5"
                                  : "translate-x-0"
                              }`}
                            />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 2. ATTENDANCE MANAGEMENT */}
                  {activeTab === "attendance" && (
                    <div className="space-y-6">
                      {/* Enable Regularization */}
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 py-2">
                        <div className="space-y-1">
                          <label
                            htmlFor="enable-regularization-toggle"
                            className="text-sm font-bold text-slate-900 dark:text-slate-100 cursor-pointer"
                          >
                            Enable Regularization
                          </label>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Restrict Employees to submit attendance regularization requests to a limit
                          </p>
                        </div>

                        <div className="flex items-center gap-3 shrink-0 pt-0.5">
                          <button
                            id="enable-regularization-toggle"
                            role="switch"
                            type="button"
                            aria-checked={settings.enableRegularization}
                            aria-label="Enable Regularization"
                            onClick={() => handleToggle("enableRegularization")}
                            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                              settings.enableRegularization
                                ? "bg-[#007bff]"
                                : "bg-slate-300 dark:bg-slate-700"
                            }`}
                          >
                            <span
                              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                settings.enableRegularization
                                  ? "translate-x-5"
                                  : "translate-x-0"
                              }`}
                            />
                          </button>
                          <span className="text-xs text-slate-500 dark:text-slate-400 font-normal">
                            (When enabled, Employees can request attendance corrections to a limit for calendar month)
                          </span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 3. HARDWARE MANAGEMENT */}
                  {activeTab === "hardware" && (
                    <div className="space-y-6">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 py-2">
                        <div className="space-y-1">
                          <label
                            htmlFor="device-sync-time-input"
                            className="text-sm font-bold text-slate-900 dark:text-slate-100 cursor-pointer"
                          >
                            Device Sync Time
                          </label>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Enter the time when device syncs daily
                          </p>
                        </div>

                        <div className="relative flex items-center border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-900 text-sm font-medium text-slate-800 dark:text-slate-200 shadow-2xs">
                          <Clock className="h-4 w-4 text-slate-400 dark:text-slate-500 mr-2 shrink-0" />
                          <input
                            id="device-sync-time-input"
                            type="text"
                            value={deviceSyncTime}
                            onChange={(e) => {
                              setDeviceSyncTime(e.target.value);
                              setIsDirty(true);
                            }}
                            className="bg-transparent border-none outline-none w-28 text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 4. EMPLOYEE MANAGEMENT */}
                  {activeTab === "employee" && (
                    <div className="space-y-6">
                      {/* Manage Branch */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2">
                        <div className="space-y-1">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            Manage Branch
                          </h3>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Go to Manage Branch section
                          </p>
                        </div>

                        <a
                          href="/employees/manage-branch"
                          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 shrink-0"
                        >
                          Go To Manage Branch
                          <ExternalLink className="h-4 w-4 text-slate-500" />
                        </a>
                      </div>

                      {/* Manage Employee */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2 pt-6 border-t border-slate-100 dark:border-slate-900">
                        <div className="space-y-1">
                          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            Manage Employee
                          </h3>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Go to Manage Employee section
                          </p>
                        </div>

                        <a
                          href="/employees"
                          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 shrink-0"
                        >
                          Go To Manage Employee
                          <ExternalLink className="h-4 w-4 text-slate-500" />
                        </a>
                      </div>
                    </div>
                  )}

                  {/* 5. PAYROLL MANAGEMENT */}
                  {activeTab === "payroll" && (
                    <div className="space-y-8">
                      {/* 1. Working Hour Type */}
                      <div className="space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                          <div className="space-y-1">
                            <label htmlFor="working-hour-type-select" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                              Working Hour Type
                            </label>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                              Choose how Employee working hours are calculated for payroll processing
                            </p>
                          </div>

                          <div className="w-full sm:w-72 shrink-0">
                            <select
                              id="working-hour-type-select"
                              value={workingHourType}
                              onChange={(e) => {
                                setWorkingHourType(e.target.value);
                                setIsDirty(true);
                              }}
                              className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                            >
                              <option value="fixed">Fixed</option>
                              <option value="shift_wise">Shift Wise</option>
                            </select>
                          </div>
                        </div>

                        {workingHourType === "fixed" && (
                          <div className="flex flex-col sm:flex-row items-center gap-6 sm:justify-end pt-2">
                            <div className="w-full sm:w-auto space-y-1.5">
                              <label htmlFor="full-day-hours-input" className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                                Full Day Working Hours
                              </label>
                              <div className="relative flex items-center border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-900 text-sm font-medium text-slate-800 dark:text-slate-200 shadow-2xs w-full sm:w-48">
                                <Clock className="h-4 w-4 text-slate-400 dark:text-slate-500 mr-2 shrink-0" />
                                <input
                                  id="full-day-hours-input"
                                  type="text"
                                  value={fullDayWorkingHours}
                                  onChange={(e) => {
                                    setFullDayWorkingHours(e.target.value);
                                    setIsDirty(true);
                                  }}
                                  className="bg-transparent border-none outline-none w-full text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none"
                                />
                              </div>
                            </div>

                            <div className="w-full sm:w-auto space-y-1.5">
                              <label htmlFor="half-day-hours-input" className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                                Half Day Working Hours
                              </label>
                              <div className="relative flex items-center border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-900 text-sm font-medium text-slate-800 dark:text-slate-200 shadow-2xs w-full sm:w-48">
                                <Clock className="h-4 w-4 text-slate-400 dark:text-slate-500 mr-2 shrink-0" />
                                <input
                                  id="half-day-hours-input"
                                  type="text"
                                  value={halfDayWorkingHours}
                                  onChange={(e) => {
                                    setHalfDayWorkingHours(e.target.value);
                                    setIsDirty(true);
                                  }}
                                  className="bg-transparent border-none outline-none w-full text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none"
                                />
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* 2. Attendance Mode */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="space-y-1">
                          <label htmlFor="attendance-mode-select" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            Attendance Mode
                          </label>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Configure how attendance punches are calculated
                          </p>
                        </div>

                        <div className="w-full sm:w-72 shrink-0">
                          <select
                            id="attendance-mode-select"
                            value={attendanceMode}
                            onChange={(e) => {
                              setAttendanceMode(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                          >
                            <option value="consider_all_punch">Consider All Punch</option>
                            <option value="first_and_last_punch_only">First &amp; Last Punch Only</option>
                            <option value="full_day_on_single_punch">Full Day on Single Punch</option>
                            <option value="default_full_day">Default Full Day</option>
                          </select>
                        </div>
                      </div>

                      {/* 3. Off Day */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                          <div className="space-y-1">
                            <label htmlFor="off-day-select" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                              Off Day
                            </label>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                              Configure off day compensation settings
                            </p>
                          </div>

                          <div className="w-full sm:w-72 shrink-0">
                            <select
                              id="off-day-select"
                              value={offDayCompensation}
                              onChange={(e) => {
                                setOffDayCompensation(e.target.value);
                                setIsDirty(true);
                              }}
                              className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                            >
                              <option value="paid">Paid (Monetary Compensation)</option>
                              <option value="compensatory_off">Compensatory Off</option>
                              <option value="unpaid">Unpaid (No Compensation)</option>
                            </select>
                          </div>
                        </div>

                        {offDayCompensation === "paid" && (
                          <div className="flex flex-col sm:items-end space-y-2 pt-1">
                            <label htmlFor="week-off-multiplier-input" className="text-xs text-slate-500 dark:text-slate-400">
                              Week off working is paid out as <span className="font-bold text-slate-800 dark:text-slate-200">{weekOffMultiplier} x</span> times daily wage*
                            </label>
                            <input
                              id="week-off-multiplier-input"
                              type="text"
                              value={weekOffMultiplier}
                              onChange={(e) => {
                                setWeekOffMultiplier(e.target.value);
                                setIsDirty(true);
                              }}
                              className="w-full sm:w-28 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                            />
                          </div>
                        )}
                      </div>

                      {/* 4. Daily Wage */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                        <div className="space-y-1">
                          <label htmlFor="daily-wage-select" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                            Daily Wage
                          </label>
                          <p className="text-sm text-slate-500 dark:text-slate-400">
                            Configure daily wage calculation settings
                          </p>
                        </div>

                        <div className="w-full sm:w-72 shrink-0">
                          <select
                            id="daily-wage-select"
                            value={dailyWageCalculation}
                            onChange={(e) => {
                              setDailyWageCalculation(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                          >
                            <option value="calendar_days">Monthly Salary ÷ Calendar Days</option>
                            <option value="working_days">Monthly Salary ÷ Working Days</option>
                            <option value="present_days">Monthly Salary ÷ Present Days</option>
                          </select>
                        </div>
                      </div>

                      {/* 5. Overtime */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 space-y-4">
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                          <div className="space-y-1">
                            <label htmlFor="overtime-type-select" className="text-sm font-bold text-slate-900 dark:text-slate-100">
                              Overtime
                            </label>
                            <p className="text-sm text-slate-500 dark:text-slate-400">
                              Configure overtime settings
                            </p>
                          </div>

                          <div className="w-full sm:w-72 shrink-0">
                            <select
                              id="overtime-type-select"
                              value={overtimeType}
                              onChange={(e) => {
                                setOvertimeType(e.target.value);
                                setIsDirty(true);
                              }}
                              className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                            >
                              <option value="fixed_per_hour_pay">Fixed Per Hour Pay</option>
                              <option value="multiplier">Multiplier Based</option>
                              <option value="no_overtime">No Overtime</option>
                            </select>
                          </div>
                        </div>

                        <div className="space-y-4 sm:flex sm:flex-col sm:items-end">
                          <div className="w-full sm:w-72 space-y-1">
                            <label htmlFor="overtime-multiplier-input" className="text-xs text-slate-500 dark:text-slate-400">
                              Multiplier of Hourly Wage
                            </label>
                            <input
                              id="overtime-multiplier-input"
                              type="text"
                              value={overtimeMultiplier}
                              onChange={(e) => {
                                setOvertimeMultiplier(e.target.value);
                                setIsDirty(true);
                              }}
                              className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                            />
                          </div>

                          <div className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto">
                            <div className="w-full sm:w-auto space-y-1">
                              <label htmlFor="overtime-buffer-input" className="text-xs text-slate-500 dark:text-slate-400">
                                Buffer Period
                              </label>
                              <div className="relative flex items-center border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-900 text-sm font-medium text-slate-800 dark:text-slate-200 shadow-2xs w-full sm:w-36">
                                <Clock className="h-4 w-4 text-slate-400 dark:text-slate-500 mr-2 shrink-0" />
                                <input
                                  id="overtime-buffer-input"
                                  type="text"
                                  value={overtimeBufferPeriod}
                                  onChange={(e) => {
                                    setOvertimeBufferPeriod(e.target.value);
                                    setIsDirty(true);
                                  }}
                                  className="bg-transparent border-none outline-none w-full text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none"
                                />
                              </div>
                            </div>

                            <div className="w-full sm:w-auto space-y-1">
                              <label htmlFor="overtime-period-select" className="text-xs text-slate-500 dark:text-slate-400">
                                Overtime Period
                              </label>
                              <select
                                id="overtime-period-select"
                                value={overtimePeriod}
                                onChange={(e) => {
                                  setOvertimePeriod(e.target.value);
                                  setIsDirty(true);
                                }}
                                className="w-full sm:w-36 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 cursor-pointer shadow-2xs"
                              >
                                <option value="daily">Daily</option>
                                <option value="weekly">Weekly</option>
                                <option value="monthly">Monthly</option>
                              </select>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* 6. Penalties */}
                      <div className="pt-6 border-t border-slate-100 dark:border-slate-900 space-y-4">
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          Penalties
                        </h3>

                        <div className="border border-slate-200 dark:border-slate-800 rounded-xl p-5 bg-slate-50/40 dark:bg-slate-900/30 space-y-4">
                          {/* Full Day Penalty */}
                          <div className="flex items-center justify-between">
                            <label htmlFor="full-day-penalty-toggle" className="text-sm font-medium text-slate-800 dark:text-slate-200 cursor-pointer">
                              Full Day Penalty
                            </label>
                            <button
                              id="full-day-penalty-toggle"
                              role="switch"
                              type="button"
                              aria-checked={fullDayPenalty}
                              aria-label="Full Day Penalty"
                              onClick={() => {
                                setFullDayPenalty(!fullDayPenalty);
                                setIsDirty(true);
                              }}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                                fullDayPenalty ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  fullDayPenalty ? "translate-x-5" : "translate-x-0"
                                }`}
                              />
                            </button>
                          </div>

                          {/* Half Day Penalty */}
                          <div className="flex items-center justify-between pt-3 border-t border-slate-200/60 dark:border-slate-800">
                            <label htmlFor="half-day-penalty-toggle" className="text-sm font-medium text-slate-800 dark:text-slate-200 cursor-pointer">
                              Half Day Penalty
                            </label>
                            <button
                              id="half-day-penalty-toggle"
                              role="switch"
                              type="button"
                              aria-checked={halfDayPenalty}
                              aria-label="Half Day Penalty"
                              onClick={() => {
                                setHalfDayPenalty(!halfDayPenalty);
                                setIsDirty(true);
                              }}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                                halfDayPenalty ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  halfDayPenalty ? "translate-x-5" : "translate-x-0"
                                }`}
                              />
                            </button>
                          </div>

                          {/* Late Coming Penalty */}
                          <div className="flex items-center justify-between pt-3 border-t border-slate-200/60 dark:border-slate-800">
                            <label htmlFor="late-coming-penalty-toggle" className="text-sm font-medium text-slate-800 dark:text-slate-200 cursor-pointer">
                              Late Coming Penalty
                            </label>
                            <button
                              id="late-coming-penalty-toggle"
                              role="switch"
                              type="button"
                              aria-checked={lateComingPenalty}
                              aria-label="Late Coming Penalty"
                              onClick={() => {
                                setLateComingPenalty(!lateComingPenalty);
                                setIsDirty(true);
                              }}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                                lateComingPenalty ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  lateComingPenalty ? "translate-x-5" : "translate-x-0"
                                }`}
                              />
                            </button>
                          </div>

                          {/* Grace Time */}
                          <div className="pt-3 border-t border-slate-200/60 dark:border-slate-800 space-y-1.5">
                            <label htmlFor="grace-time-input" className="text-xs font-medium text-slate-700 dark:text-slate-300">
                              Grace Time
                            </label>
                            <div className="relative flex items-center border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 bg-white dark:bg-slate-900 text-sm font-medium text-slate-800 dark:text-slate-200 shadow-2xs w-full sm:w-48">
                              <Clock className="h-4 w-4 text-slate-400 dark:text-slate-500 mr-2 shrink-0" />
                              <input
                                id="grace-time-input"
                                type="text"
                                value={graceTime}
                                onChange={(e) => {
                                  setGraceTime(e.target.value);
                                  setIsDirty(true);
                                }}
                                className="bg-transparent border-none outline-none w-full text-sm font-medium text-slate-800 dark:text-slate-200 focus:outline-none"
                              />
                            </div>
                            <p className="text-xs text-slate-400 dark:text-slate-500">
                              Flexible window before Employees are being considered late
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 6. CONFIGURATIONS */}
                  {activeTab === "configurations" && (
                    <div className="space-y-6">
                      <div className="flex items-center justify-between py-2">
                        <div>
                          <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                            Enable Comprehensive Audit Logging
                          </p>
                          <p className="text-xs text-slate-500 dark:text-slate-400">
                            Log all system state changes, permission assignments, and logins.
                          </p>
                        </div>
                        <button
                          role="switch"
                          type="button"
                          aria-checked={settings.auditLogging}
                          aria-label="Enable Comprehensive Audit Logging"
                          onClick={() => handleToggle("auditLogging")}
                          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                            settings.auditLogging
                              ? "bg-[#007bff]"
                              : "bg-slate-300 dark:bg-slate-700"
                          }`}
                        >
                          <span
                            className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                              settings.auditLogging
                                ? "translate-x-5"
                                : "translate-x-0"
                            }`}
                          />
                        </button>
                      </div>
                    </div>
                  )}

                  {/* 7. SALARY SLIP */}
                  {activeTab === "salary-slip" && (
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                      {/* Left Column: Settings Form */}
                      <div className="lg:col-span-5 space-y-6">
                        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                          Company Details
                        </h3>

                        {/* Logo Upload */}
                        <div className="space-y-1.5">
                          <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Logo
                          </label>
                          <div className="flex items-center gap-2">
                            <label className="px-3 py-1.5 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-md text-xs font-medium text-slate-700 dark:text-slate-300 cursor-pointer transition-colors">
                              Choose File
                              <input
                                type="file"
                                accept="image/*"
                                className="hidden"
                                onChange={(e) => {
                                  if (e.target.files?.[0]) {
                                    setIsDirty(true);
                                  }
                                }}
                              />
                            </label>
                            <span className="text-xs text-slate-400">No file chosen</span>
                          </div>
                        </div>

                        {/* Name */}
                        <div className="space-y-1.5">
                          <label htmlFor="salary-slip-name" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Name <span className="text-red-500">*</span>
                          </label>
                          <input
                            id="salary-slip-name"
                            type="text"
                            value={salarySlipCompany}
                            onChange={(e) => {
                              setSalarySlipCompany(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                          />
                        </div>

                        {/* Address */}
                        <div className="space-y-1.5">
                          <label htmlFor="salary-slip-address" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Address <span className="text-red-500">*</span>
                          </label>
                          <input
                            id="salary-slip-address"
                            type="text"
                            value={salarySlipAddress}
                            onChange={(e) => {
                              setSalarySlipAddress(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                          />
                        </div>

                        {/* Contact */}
                        <div className="space-y-1.5">
                          <label htmlFor="salary-slip-contact" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Contact <span className="text-red-500">*</span>
                          </label>
                          <input
                            id="salary-slip-contact"
                            type="text"
                            value={salarySlipContact}
                            onChange={(e) => {
                              setSalarySlipContact(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                          />
                        </div>

                        {/* Website / Email */}
                        <div className="space-y-1.5">
                          <label htmlFor="salary-slip-email" className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Website / Email
                          </label>
                          <input
                            id="salary-slip-email"
                            type="text"
                            value={salarySlipEmail}
                            placeholder="e.g. https://company.com or info@company.com"
                            onChange={(e) => {
                              setSalarySlipEmail(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs placeholder:text-slate-400"
                          />
                        </div>

                        {/* Auto Release Payslip & Branch Wise Payslip Toggles */}
                        <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-900">
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                              Auto Release Payslip
                            </span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={autoReleasePayslip}
                              onClick={() => {
                                setAutoReleasePayslip(!autoReleasePayslip);
                                setIsDirty(true);
                              }}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                                autoReleasePayslip ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  autoReleasePayslip ? "translate-x-5" : "translate-x-0"
                                }`}
                              />
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                              Branch Wise Payslip
                            </span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={branchWisePayslip}
                              onClick={() => {
                                setBranchWisePayslip(!branchWisePayslip);
                                setIsDirty(true);
                              }}
                              className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 ${
                                branchWisePayslip ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"
                              }`}
                            >
                              <span
                                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  branchWisePayslip ? "translate-x-5" : "translate-x-0"
                                }`}
                              />
                            </button>
                          </div>
                        </div>

                        {/* Mandatory Phase 5 Toggles: Logo, Signature, Show PF, Show ESIC, Show Leave Balance */}
                        <div className="space-y-4 pt-4 border-t border-slate-100 dark:border-slate-900">
                          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Display & Format Controls
                          </h4>

                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Logo Toggle</span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={showLogo}
                              onClick={() => { setShowLogo(!showLogo); setIsDirty(true); }}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${showLogo ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"}`}
                            >
                              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition ${showLogo ? "translate-x-4" : "translate-x-0"}`} />
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Signature Toggle</span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={showSignature}
                              onClick={() => { setShowSignature(!showSignature); setIsDirty(true); }}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${showSignature ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"}`}
                            >
                              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition ${showSignature ? "translate-x-4" : "translate-x-0"}`} />
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Show PF</span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={showPf}
                              onClick={() => { setShowPf(!showPf); setIsDirty(true); }}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${showPf ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"}`}
                            >
                              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition ${showPf ? "translate-x-4" : "translate-x-0"}`} />
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Show ESIC</span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={showEsic}
                              onClick={() => { setShowEsic(!showEsic); setIsDirty(true); }}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${showEsic ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"}`}
                            >
                              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition ${showEsic ? "translate-x-4" : "translate-x-0"}`} />
                            </button>
                          </div>

                          <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-slate-700 dark:text-slate-300">Show Leave Balance</span>
                            <button
                              role="switch"
                              type="button"
                              aria-checked={showLeaveBalance}
                              onClick={() => { setShowLeaveBalance(!showLeaveBalance); setIsDirty(true); }}
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors ${showLeaveBalance ? "bg-[#007bff]" : "bg-slate-300 dark:bg-slate-700"}`}
                            >
                              <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow-xs transition ${showLeaveBalance ? "translate-x-4" : "translate-x-0"}`} />
                            </button>
                          </div>
                        </div>

                      </div>

                      {/* Right Column: Live Payslip Preview */}
                      <div className="lg:col-span-7 space-y-3">
                        <div className="flex items-center justify-end">
                          <button
                            type="button"
                            className="px-4 py-1.5 text-xs font-medium text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 rounded-md transition-colors shadow-2xs"
                          >
                            Preview
                          </button>
                        </div>

                        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-6 shadow-sm space-y-6 text-xs text-slate-800 dark:text-slate-200">
                          {/* Header */}
                          <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-4">
                            <div>
                              <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                                {salarySlipCompany || "Company Name"}
                              </h4>
                              <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                                {salarySlipAddress || "Company Address"}
                              </p>
                            </div>
                            <div className="text-right">
                              <span className="font-bold text-slate-700 dark:text-slate-300">Payslip from -</span>
                            </div>
                          </div>

                          {/* Employee Details Grid */}
                          <div className="space-y-2">
                            <h5 className="font-bold text-slate-900 dark:text-slate-100">Employee Details</h5>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
                              <div className="flex"><span className="w-28 text-slate-500">Employee Name</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Bank Name</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Code</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Bank A/C No.</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Designation</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">IFSC Code</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Department</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">Branch Name</span><span>:</span></div>
                              <div className="flex"><span className="w-28 text-slate-500">UAN Number</span><span>: -</span></div>
                              {showPf && <div className="flex"><span className="w-28 text-slate-500">PF Number</span><span>: -</span></div>}
                              <div className="flex"><span className="w-28 text-slate-500">Work Location</span><span>: -</span></div>
                              {showEsic && <div className="flex"><span className="w-28 text-slate-500">ESIC Number</span><span>: -</span></div>}
                            </div>
                          </div>

                          {/* Earnings & Deductions Table */}
                          <div className="border border-slate-200 dark:border-slate-800 rounded-md overflow-hidden text-[11px]">
                            <div className="grid grid-cols-4 bg-slate-100 dark:bg-slate-800 font-bold p-2 text-slate-700 dark:text-slate-300">
                              <div>Earnings</div>
                              <div>Amount (Rs.)</div>
                              <div>Deductions</div>
                              <div>Amount (Rs.)</div>
                            </div>
                            <div className="grid grid-cols-4 p-2 font-bold border-t border-slate-200 dark:border-slate-800">
                              <div>Total Gross Earnings</div>
                              <div>0.00</div>
                              <div>Total Deductions</div>
                              <div>0.00</div>
                            </div>
                          </div>

                          {/* Total Payable Days */}
                          <div className="flex items-center justify-between text-[11px] px-2 py-1.5 border border-slate-100 dark:border-slate-800 rounded-md">
                            <div className="font-bold text-slate-700 dark:text-slate-300">Total Payable Days</div>
                            <div className="flex items-center gap-6 text-slate-600 dark:text-slate-400">
                              <div>Worked Day : <span className="font-bold">0</span></div>
                              <div>Weekly Off : <span className="font-bold">0</span></div>
                              <div>Holiday : <span className="font-bold">0</span></div>
                              {showLeaveBalance && <div>Paid Leaves : <span className="font-bold">0</span></div>}
                            </div>
                          </div>

                          {/* Total Net Payable Banner */}
                          <div className="bg-[#eefbe8] dark:bg-emerald-950/40 border border-emerald-200/80 dark:border-emerald-800/80 rounded-lg p-3 space-y-1">
                            <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                              Total Net Payable :
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 font-normal">
                              Total Net Payable = Gross Earnings - Total Deductions
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 8. ORGANIZATION MANAGEMENT */}
                  {activeTab === "organization" && (
                    <div className="space-y-6 max-w-xl">
                      {/* Sync Code */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3 border-b border-slate-100 dark:border-slate-900">
                        <label
                          htmlFor="sync-code-input"
                          className="text-sm font-medium text-slate-700 dark:text-slate-300 min-w-[140px]"
                        >
                          Sync Code
                        </label>
                        <div className="w-full sm:w-64">
                          <input
                            id="sync-code-input"
                            type="text"
                            value={syncCode}
                            onChange={(e) => {
                              setSyncCode(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-3 py-1.5 text-sm text-center text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                          />
                        </div>
                      </div>

                      {/* Pass Code */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-3">
                        <label
                          htmlFor="pass-code-input"
                          className="text-sm font-medium text-slate-700 dark:text-slate-300 min-w-[140px]"
                        >
                          Pass Code
                        </label>
                        <div className="w-full sm:w-64">
                          <input
                            id="pass-code-input"
                            type="text"
                            value={passCode}
                            onChange={(e) => {
                              setPassCode(e.target.value);
                              setIsDirty(true);
                            }}
                            className="w-full bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-md px-3 py-1.5 text-sm text-center text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-2xs"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                </div>

                {/* Bottom Footer */}
                <div className="pt-6 mt-8 border-t border-slate-100 dark:border-slate-900 flex items-center justify-end gap-3">
                  <button
                    type="button"
                    onClick={handleCancel}
                    className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 cursor-pointer"
                  >
                    Cancel
                  </button>

                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={updateSettingsMutation.isPending}
                    className={`inline-flex items-center gap-2 px-5 py-2 text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                      isDirty || updateSettingsMutation.isPending
                        ? "bg-[#007bff] hover:bg-blue-600 text-white shadow-xs cursor-pointer"
                        : "bg-[#d0dce8] dark:bg-slate-800 text-slate-500 dark:text-slate-400 cursor-not-allowed"
                    }`}
                  >
                    {updateSettingsMutation.isPending ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      "Save Changes"
                    )}
                  </button>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
