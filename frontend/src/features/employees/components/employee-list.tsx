"use client";

import React, { useState, useMemo, useEffect, useRef } from "react";
import {
  Plus,
  Pencil,
  Trash2,
  MoreVertical,
  Clock,
  FolderOpen,
  Fingerprint,
  ArrowUpDown,
  X,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Settings,
  AlertTriangle,
  Search,
  Calendar,
  GripVertical,
  Upload,
  Download,
  FileDown,
  FileText,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/feedback/empty-state";
import { Skeleton } from "@/components/feedback/skeleton";
import {
  Employee,
  EmployeeListParams,
  EmployeeUiStatus,
  EmploymentStatus,
  SortOrder,
} from "../types";
import { useQueryClient } from "@tanstack/react-query";
import { usePermissions } from "@/features/auth";
import {
  useActiveEmployeeCount,
  useBranchOptions,
  useDebouncedValue,
  useDepartmentOptions,
  useDesignationOptions,
  useEmployees,
  employeeKeys,
} from "../hooks";
import { SORT_FIELD_MAP, toEmployeeRow, STATUS_LABELS } from "../utils";

const UI_STATUSES: readonly EmployeeUiStatus[] = ["Active", "Inactive", "Terminated"];

const STATUS_FILTER_OPTIONS: readonly { label: EmployeeUiStatus; value: EmploymentStatus }[] = [
  { label: "Active", value: "active" },
  { label: "Inactive", value: "inactive" },
  { label: "Terminated", value: "terminated" },
];

const MONTHS_LIST = [
  { label: "Jan 2026", val: "2026-01" },
  { label: "Feb 2026", val: "2026-02" },
  { label: "Mar 2026", val: "2026-03" },
  { label: "Apr 2026", val: "2026-04" },
  { label: "May 2026", val: "2026-05" },
  { label: "Jun 2026", val: "2026-06" },
];

interface ShiftLogEntry {
  log: string;
  detail: string;
  type: string;
  oldData: string;
  modifiedBy: string;
}

// Shift logs come from the Shift module, which has no per-employee log API yet.
// The modal renders its empty state until that integration phase lands.
const SHIFT_LOGS: ShiftLogEntry[] = [];

const formatMonthYear = (monthStr: string) => {
  const [year, month] = monthStr.split("-");
  const date = new Date(parseInt(year), parseInt(month) - 1);
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
};

const REQUIRED_DOCS = [
  "Aadhar Card",
  "Driving Licence",
  "PAN Card",
  "Passport Size Photo"
];

// Cell renderer for the optional columns. Fields not present in the list API
// (salary, bank, statutory, emergency, biometric, …) render "-" until their
// owning integrations land — no fabricated values.
const renderCellContent = (emp: Employee, colKey: string) => {
  switch (colKey) {
    case "employee_id":
      return emp.employee_id;
    case "name":
      return emp.name;
    case "display_name":
      return emp.display_name;
    case "mobile_number":
      return emp.mobile_number;
    case "email":
      return emp.email;
    case "gender":
      return emp.gender;
    case "master_branch":
      return emp.master_branch;
    case "department":
      return emp.department;
    case "designation":
      return emp.designation;
    case "employee_type":
      return emp.employee_type;
    case "date_of_joining":
      return emp.date_of_joining;
    case "status":
      return emp.status;
    case "created_on":
      return emp.created_on;
    default:
      return "-";
  }
};

export const EmployeeList = () => {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { hasPermission } = usePermissions();

  const canCreateEmployee = hasPermission("employee", "create");
  const canEditEmployee = hasPermission("employee", "edit");
  const canDeleteEmployee = hasPermission("employee", "delete");

  // Search and Filters state (selects hold backend IDs as strings; "" = all)
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedBranch, setSelectedBranch] = useState("");
  const [selectedDept, setSelectedDept] = useState("");
  const [selectedDesignation, setSelectedDesignation] = useState("");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("");
  const debouncedSearch = useDebouncedValue(searchTerm);

  // Table Selection state
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  // Sorting state
  const [sortConfig, setSortConfig] = useState<{ field: string; order: SortOrder } | null>({
    field: "employee_id",
    order: "desc",
  });

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Live employee list (GET /employees) — search, filters, sorting, and
  // pagination are all applied server-side; this component renders the page.
  const listParams = useMemo<EmployeeListParams>(() => {
    const sortBy = sortConfig ? SORT_FIELD_MAP[sortConfig.field] : undefined;
    return {
      page: currentPage,
      page_size: pageSize,
      q: debouncedSearch.trim() || undefined,
      branch_id: selectedBranch ? Number(selectedBranch) : undefined,
      department_id: selectedDept ? Number(selectedDept) : undefined,
      designation_id: selectedDesignation ? Number(selectedDesignation) : undefined,
      status: selectedStatusFilter ? (selectedStatusFilter as EmploymentStatus) : undefined,
      sort_by: sortBy,
      sort_order: sortBy ? sortConfig?.order : undefined,
    };
  }, [
    currentPage,
    pageSize,
    debouncedSearch,
    selectedBranch,
    selectedDept,
    selectedDesignation,
    selectedStatusFilter,
    sortConfig,
  ]);

  const employeesQuery = useEmployees(listParams);
  const employees = useMemo(
    () => (employeesQuery.data?.items ?? []).map(toEmployeeRow),
    [employeesQuery.data]
  );
  const paginationMeta = employeesQuery.data?.pagination;
  const totalRecords = paginationMeta?.total_records ?? 0;

  // Filter dropdown sources (organization lookups) + page-heading count
  const { data: branchOptions } = useBranchOptions();
  const { data: departmentOptions } = useDepartmentOptions();
  const { data: designationOptions } = useDesignationOptions();
  const { data: activeEmployeeCount } = useActiveEmployeeCount();

  // Active Dropdowns state
  const [activeActionRowId, setActiveActionRowId] = useState<number | null>(null);
  const [activeStatusRowId, setActiveStatusRowId] = useState<number | null>(null);
  const [isActionsDropdownOpen, setIsActionsDropdownOpen] = useState(false);

  // Actions menu state
  const [isExporting, setIsExporting] = useState(false);
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isBulkUpdateModalOpen, setIsBulkUpdateModalOpen] = useState(false);
  const [isDownloadsModalOpen, setIsDownloadsModalOpen] = useState(false);
  const [importFile, setImportFile] = useState<File | null>(null);
  const [bulkUpdateFile, setBulkUpdateFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const importFileRef = useRef<HTMLInputElement>(null);
  const bulkUpdateFileRef = useRef<HTMLInputElement>(null);

  // Export Excel: calls the Reports API with format=excel and triggers a browser download
  const handleExportExcel = async () => {
    setIsActionsDropdownOpen(false);
    setIsExporting(true);
    try {
      const { axiosClient } = await import("@/lib/axios-client");
      const response = await axiosClient.get("/reports/employees/master", {
        params: { format: "excel", page_size: 200 },
        responseType: "blob",
      });

      const contentDisposition = response.headers["content-disposition"] as string | undefined;
      let filename = `employees_${new Date().toISOString().slice(0, 10)}.xlsx`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match?.[1]) filename = match[1];
      }

      const url = URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      toast.success("Employee data exported successfully!");
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Export failed. Please try again.";
      toast.error(message);
    } finally {
      setIsExporting(false);
    }
  };

  // Download Sample: generates a CSV template in the browser and triggers download
  const handleDownloadSample = () => {
    setIsActionsDropdownOpen(false);
    const headers = [
      "employee_code",
      "employee_name",
      "display_name",
      "mobile_number",
      "email",
      "gender",
      "date_of_joining",
      "employee_type",
      "department",
      "designation",
      "master_branch",
    ];
    const sampleRow = [
      "EMP001",
      "John Doe",
      "John",
      "9876543210",
      "john.doe@company.com",
      "Male",
      "2024-01-15",
      "full_time",
      "Engineering",
      "Software Engineer",
      "Head Office",
    ];
    const csvContent = [headers.join(","), sampleRow.join(",")].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "employee_import_sample.csv");
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    toast.success("Sample file downloaded.");
  };

  // Modals state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    "Basic Details": true,
  });

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isColumnsModalOpen, setIsColumnsModalOpen] = useState(false);
  const [columnsSearchQuery, setColumnsSearchQuery] = useState("");
  const [columnsList, setColumnsList] = useState([
    { key: "employee_id", label: "Emp Id", checked: true, defaultChecked: true },
    { key: "name", label: "Name", checked: true, defaultChecked: true },
    { key: "display_name", label: "Display Name", checked: false, defaultChecked: false },
    { key: "mobile_number", label: "Phone Number", checked: false, defaultChecked: false },
    { key: "email", label: "Email", checked: false, defaultChecked: false },
    { key: "gender", label: "Gender", checked: false, defaultChecked: false },
    { key: "punch_in_branch", label: "Punch In Branch", checked: false, defaultChecked: false },
    { key: "master_branch", label: "Master Branch", checked: true, defaultChecked: true },
    { key: "department", label: "Department", checked: true, defaultChecked: true },
    { key: "designation", label: "Designation", checked: true, defaultChecked: true },
    { key: "employee_type", label: "Employment Type", checked: false, defaultChecked: false },
    { key: "door_lock_permission", label: "Door Lock Permission", checked: false, defaultChecked: false },
    { key: "salary_type", label: "Salary Type", checked: false, defaultChecked: false },
    { key: "hourly_calc", label: "Hourly Salary Calculation", checked: false, defaultChecked: false },
    { key: "monthly_salary", label: "Salary", checked: false, defaultChecked: false },
    { key: "payroll_group", label: "Payroll Group", checked: false, defaultChecked: false },
    { key: "tds_type", label: "TDS Type", checked: false, defaultChecked: false },
    { key: "monthly_tds", label: "Monthly TDS", checked: false, defaultChecked: false },
    { key: "prev_employer_income", label: "Previous Employer Income", checked: false, defaultChecked: false },
    { key: "prev_tds_deducted", label: "Previous TDS Deducted", checked: false, defaultChecked: false },
    { key: "pf_number", label: "PF", checked: false, defaultChecked: false },
    { key: "uan_number", label: "UAN", checked: false, defaultChecked: false },
    { key: "esic_number", label: "ESIC", checked: false, defaultChecked: false },
    { key: "address", label: "Address", checked: false, defaultChecked: false },
    { key: "date_of_joining", label: "Date of Joining", checked: true, defaultChecked: true },
    { key: "bank_name", label: "Bank Name", checked: false, defaultChecked: false },
    { key: "branch_name", label: "Branch Name", checked: false, defaultChecked: false },
    { key: "account_no", label: "Account No", checked: false, defaultChecked: false },
    { key: "ifsc_code", label: "IFSC Code", checked: false, defaultChecked: false },
    { key: "documents", label: "Documents", checked: false, defaultChecked: false },
    { key: "photo", label: "Photo", checked: false, defaultChecked: false },
    { key: "emergency_name", label: "Emergency Contact Name", checked: false, defaultChecked: false },
    { key: "emergency_mobile", label: "Emergency Mobile", checked: false, defaultChecked: false },
    { key: "emergency_relation", label: "Emergency Relation", checked: false, defaultChecked: false },
    { key: "emergency_address", label: "Emergency Address", checked: false, defaultChecked: false },
    { key: "dob", label: "Date of Birth", checked: false, defaultChecked: false },
    { key: "reference_details", label: "Reference Details", checked: false, defaultChecked: false },
    { key: "fingerprint", label: "Fingerprint", checked: false, defaultChecked: false },
    { key: "attendance_method", label: "Attendance Method", checked: false, defaultChecked: false },
    { key: "status", label: "Tags", checked: true, defaultChecked: true },
    { key: "created_on", label: "Created On", checked: false, defaultChecked: false },
  ]);

  const handleToggleColumnByKey = (key: string) => {
    setColumnsList(prev =>
      prev.map(col => (col.key === key ? { ...col, checked: !col.checked } : col))
    );
  };

  const handleSaveColumns = () => {
    const updatedVisibleColumns = Object.fromEntries(
      Object.entries(visibleColumns).map(([key, value]) => {
        const col = columnsList.find(c => c.key === key);
        return [key, col ? col.checked : value];
      })
    ) as typeof visibleColumns;
    setVisibleColumns(updatedVisibleColumns);
    setIsColumnsModalOpen(false);
  };

  const handleResetColumns = () => {
    setColumnsList(prev => prev.map(col => ({ ...col, checked: col.defaultChecked })));
  };

  const [isAttendancePermModalOpen, setIsAttendancePermModalOpen] = useState(false);

  // Sheets / Details state
  const [isShiftLogsOpen, setIsShiftLogsOpen] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState("2026-05");
  const [isMonthPickerOpen, setIsMonthPickerOpen] = useState(false);
  const [isDocLibraryOpen, setIsDocLibraryOpen] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState<Record<string, { fileName: string; size: string; date: string }>>({});
  const [legalDocsFiles, setLegalDocsFiles] = useState<Record<string, string>>({
    "Aadhar Card": "No file chosen",
    "Driving Licence": "No file chosen",
    "PAN Card": "No file chosen",
    "Passport Size Photo": "No file chosen"
  });
  const [isPunchBranchOpen, setIsPunchBranchOpen] = useState(false);

  // Target object state for Edit / Delete / View details
  const [targetEmployee, setTargetEmployee] = useState<Employee | null>(null);

  const [formData, setFormData] = useState({
    employee_id: "",
    name: "",
    display_name: "",
    mobile_number: "",
    email: "",
    gender: "Male" as "Male" | "Female" | "Other",
    punch_in_branch: "Itcode Infotech",
    master_branch: "Itcode Infotech",
    department: "Developer",
    designation: "Full Stack",
    employee_type: "Full Time",
    door_lock_permission: "Yes" as "Yes" | "No",
    pf_number: "",
    uan_number: "",
    esic_number: "",
    address: "",
    date_of_joining: "",
    status: "Active" as EmployeeUiStatus,
    salary_type: "Monthly" as "Monthly" | "Hourly" | "Compliance",
    monthly_salary: "0",
    payroll_group: "",
    bank_name: "",
    branch_name: "",
    account_no: "",
    ifsc_code: "",
  });

  // Column Visibility state
  const [visibleColumns, setVisibleColumns] = useState({
    employee_id: true,
    name: true,
    master_branch: true,
    department: true,
    designation: true,
    date_of_joining: true,
    status: true,
  });

  // Close dropdowns on outside click
  const actionMenuRef = useRef<HTMLDivElement>(null);
  const statusMenuRef = useRef<HTMLDivElement>(null);
  const actionsButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (actionMenuRef.current && !actionMenuRef.current.contains(e.target as Node)) {
        setActiveActionRowId(null);
      }
      if (statusMenuRef.current && !statusMenuRef.current.contains(e.target as Node)) {
        setActiveStatusRowId(null);
      }
      if (actionsButtonRef.current && !actionsButtonRef.current.contains(e.target as Node)) {
        setIsActionsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  // Derived page UI state (React Query drives loading / error / empty / normal)
  const uiState: "normal" | "loading" | "empty" | "error" = employeesQuery.isError
    ? "error"
    : employeesQuery.isPending
      ? "loading"
      : employees.length === 0
        ? "empty"
        : "normal";

  const totalActiveEmployees = activeEmployeeCount ?? 0;

  // Sorting handler — server-side; only columns the backend can sort react.
  const handleSort = (field: string) => {
    if (!SORT_FIELD_MAP[field]) return;
    setCurrentPage(1);
    setSortConfig(prev => {
      if (prev && prev.field === field) {
        return {
          field,
          order: prev.order === "asc" ? "desc" : "asc",
        };
      }
      return { field, order: "asc" };
    });
  };

  const getSortIcon = (field: string) => {
    if (!SORT_FIELD_MAP[field]) return null;
    const isActive = sortConfig?.field === field;
    return (
      <ArrowUpDown
        className={`ml-1 h-3.5 w-3.5 transition-all inline ${
          isActive ? "text-primary opacity-100" : "opacity-60 hover:opacity-100"
        }`}
      />
    );
  };

  // Server-paginated rows: the current page IS the fetched page.
  const paginatedEmployees = employees;
  const totalPages = paginationMeta?.total_pages || 1;

  const clearAllFilters = () => {
    setSearchTerm("");
    setSelectedBranch("");
    setSelectedDept("");
    setSelectedDesignation("");
    setSelectedStatusFilter("");
    setCurrentPage(1);
  };

  // Selection handlers
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      const newIds = new Set(selectedIds);
      paginatedEmployees.forEach(e => newIds.add(e.id));
      setSelectedIds(newIds);
    } else {
      const newIds = new Set(selectedIds);
      paginatedEmployees.forEach(e => newIds.delete(e.id));
      setSelectedIds(newIds);
    }
  };

  const handleSelectItem = (id: number, checked: boolean) => {
    const newIds = new Set(selectedIds);
    if (checked) {
      newIds.add(id);
    } else {
      newIds.delete(id);
    }
    setSelectedIds(newIds);
  };

  const triggerFileInput = (docName: string) => {
    document.getElementById(`file-input-${docName}`)?.click();
  };

  const handleFileUpload = (docName: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUploadedDocs(prev => ({
        ...prev,
        [docName]: {
          fileName: file.name,
          size: `${(file.size / 1024 / 1024).toFixed(2)} MB`,
          date: new Date().toLocaleDateString("en-US", { day: "numeric", month: "short", year: "numeric" })
        }
      }));
      toast.success(`${docName} uploaded successfully!`);
    }
  };

  const handleFileRemove = (docName: string) => {
    setUploadedDocs(prev => {
      const copy = { ...prev };
      delete copy[docName];
      return copy;
    });
    toast.success(`${docName} removed.`);
  };

  const isAllSelected = useMemo(() => {
    if (paginatedEmployees.length === 0) return false;
    return paginatedEmployees.every(e => selectedIds.has(e.id));
  }, [paginatedEmployees, selectedIds]);

  // Quick Action menu handlers
  const handleActionClick = (action: string, emp: Employee) => {
    setTargetEmployee(emp);
    setActiveActionRowId(null);

    switch (action) {
      case "shift_logs":
        setIsShiftLogsOpen(true);
        break;
      case "document_library":
        setIsDocLibraryOpen(true);
        break;
      case "punch_branch":
        setIsPunchBranchOpen(true);
        break;
      case "edit":
        (async () => {
          const loadingToastId = toast.loading("Loading employee details...");
          try {
            const { axiosClient } = await import("@/lib/axios-client");
            const response = await axiosClient.get<{ success: boolean; data: any }>(`/employees/${emp.id}`);
            const details = response.data?.data;
            if (details) {
              setFormData({
                employee_id: String(details.employee_id),
                name: details.employee_name || "",
                display_name: details.display_name || "",
                mobile_number: details.mobile_number || "",
                email: details.email || "",
                gender: details.gender || "Male",
                punch_in_branch: details.branch?.branch_name || details.branch_name || "",
                master_branch: details.branch?.branch_name || details.branch_name || "",
                department: details.department?.dept_name || details.department_name || "",
                designation: details.designation?.designation_name || details.designation_name || "",
                employee_type: details.employee_type || "Full Time",
                door_lock_permission: details.door_lock_permission ? "Yes" : "No",
                pf_number: details.pf_account_number || "",
                uan_number: details.uan_number || "",
                esic_number: details.esic_ip_number || "",
                address: details.address || "",
                date_of_joining: details.date_of_joining || "",
                status: STATUS_LABELS[details.employment_status as EmploymentStatus] || "Active",
                salary_type: details.salary?.salary_type || "Monthly",
                monthly_salary: details.salary?.monthly_salary ? String(details.salary.monthly_salary) : "0",
                payroll_group: details.payroll_group?.group_name || "",
                bank_name: details.bank_details?.[0]?.bank_name || "",
                branch_name: details.bank_details?.[0]?.branch_name || "",
                account_no: details.bank_details?.[0]?.account_no || "",
                ifsc_code: details.bank_details?.[0]?.ifsc_code || "",
              });
              setIsEditModalOpen(true);
            }
            toast.dismiss(loadingToastId);
          } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to load employee details.";
            toast.error(message, { id: loadingToastId });
          }
        })();
        break;
      case "delete":
        setIsDeleteModalOpen(true);
        break;
      default:
        break;
    }
  };

  // Status Change handler
  const handleStatusChange = async (newStatus: EmployeeUiStatus) => {
    const employeeId = activeStatusRowId;
    setActiveStatusRowId(null);
    if (!employeeId) return;

    // Check if already in target status
    const employeesList = employeesQuery.data?.items ?? [];
    const emp = employeesList.find(e => e.employee_id === employeeId);
    if (emp) {
      const statusMap: Record<string, string> = {
        active: "Active",
        inactive: "Inactive",
        terminated: "Terminated",
      };
      if (statusMap[emp.employment_status] === newStatus) {
        toast.info(`Employee is already "${newStatus}".`);
        return;
      }
    }

    const loadingToastId = toast.loading(`Updating status to ${newStatus}...`);

    try {
      const { axiosClient } = await import("@/lib/axios-client");
      if (newStatus === "Active") {
        if (emp && emp.employment_status === "terminated") {
          await axiosClient.post(`/employees/${employeeId}/rehire`, {
            date_of_joining: new Date().toISOString().slice(0, 10),
          });
        } else {
          await axiosClient.post(`/employees/${employeeId}/activate`);
        }
      } else if (newStatus === "Inactive") {
        await axiosClient.post(`/employees/${employeeId}/deactivate`);
      } else if (newStatus === "Terminated") {
        await axiosClient.post(`/employees/${employeeId}/terminate`, {
          effective_date: new Date().toISOString().slice(0, 10),
          reason: "Status changed via UI",
        });
      }

      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      toast.success(`Employee status updated to ${newStatus}.`, { id: loadingToastId });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Status update failed.";
      toast.error(`Failed to update status: ${message}`, { id: loadingToastId });
    }
  };

  // Create Employee
  const handleCreateEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("Please fill the employee name.");
      return;
    }
    if (!formData.mobile_number.trim()) {
      toast.error("Please fill the mobile number.");
      return;
    }

    const loadingToastId = toast.loading("Adding employee...");
    try {
      const { axiosClient } = await import("@/lib/axios-client");

      // Match branch, department, designation to their database IDs
      const branchOpt = branchOptions?.find(b => b.branch_name.toLowerCase() === formData.master_branch.toLowerCase());
      const deptOpt = departmentOptions?.find(d => d.dept_name.toLowerCase() === formData.department.toLowerCase());
      const desigOpt = designationOptions?.find(d => d.designation_name.toLowerCase() === formData.designation.toLowerCase());

      const branchId = branchOpt?.branch_id || branchOptions?.[0]?.branch_id || 1;
      const deptId = deptOpt?.dept_id || departmentOptions?.[0]?.dept_id || 1;
      const desigId = desigOpt?.designation_id || designationOptions?.[0]?.designation_id || 1;

      const payload = {
        employee_name: formData.name.trim(),
        display_name: formData.display_name.trim() || formData.name.trim(),
        gender: formData.gender,
        mobile_country_code: "+91",
        mobile_number: formData.mobile_number.trim(),
        email: formData.email.trim() || null,
        address: formData.address.trim() || null,
        master_branch_id: branchId,
        dept_id: deptId,
        designation_id: desigId,
        date_of_joining: formData.date_of_joining || new Date().toISOString().slice(0, 10),
        employee_type: formData.employee_type || "Full Time",
        door_lock_permission: formData.door_lock_permission === "Yes",
        pf_account_number: formData.pf_number.trim() || null,
        uan_number: formData.uan_number.trim() || null,
        esic_ip_number: formData.esic_number.trim() || null,
        salary_type: formData.salary_type,
        monthly_salary: Number(formData.monthly_salary) || 0,
      };

      await axiosClient.post("/employees", payload);

      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      toast.success("Employee created successfully.", { id: loadingToastId });
      setIsAddModalOpen(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to create employee.";
      toast.error(`Error: ${message}`, { id: loadingToastId });
    }
  };

  // Save Edit Employee
  const handleSaveEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetEmployee) return;
    if (!formData.name.trim()) {
      toast.error("Please fill the employee name.");
      return;
    }
    if (!formData.mobile_number.trim()) {
      toast.error("Please fill the mobile number.");
      return;
    }

    const loadingToastId = toast.loading("Saving employee...");
    try {
      const { axiosClient } = await import("@/lib/axios-client");

      // Match branch, department, designation to their database IDs
      const branchOpt = branchOptions?.find(b => b.branch_name.toLowerCase() === formData.master_branch.toLowerCase());
      const deptOpt = departmentOptions?.find(d => d.dept_name.toLowerCase() === formData.department.toLowerCase());
      const desigOpt = designationOptions?.find(d => d.designation_name.toLowerCase() === formData.designation.toLowerCase());

      const branchId = branchOpt?.branch_id || branchOptions?.[0]?.branch_id || 1;
      const deptId = deptOpt?.dept_id || departmentOptions?.[0]?.dept_id || 1;
      const desigId = desigOpt?.designation_id || designationOptions?.[0]?.designation_id || 1;

      const payload = {
        employee_name: formData.name.trim(),
        display_name: formData.display_name.trim() || formData.name.trim(),
        gender: formData.gender,
        mobile_country_code: "+91",
        mobile_number: formData.mobile_number.trim(),
        email: formData.email.trim() || null,
        address: formData.address.trim() || null,
        master_branch_id: branchId,
        dept_id: deptId,
        designation_id: desigId,
        date_of_joining: formData.date_of_joining || new Date().toISOString().slice(0, 10),
        employee_type: formData.employee_type || "Full Time",
        door_lock_permission: formData.door_lock_permission === "Yes",
        pf_account_number: formData.pf_number.trim() || null,
        uan_number: formData.uan_number.trim() || null,
        esic_ip_number: formData.esic_number.trim() || null,
        salary_type: formData.salary_type,
        monthly_salary: Number(formData.monthly_salary) || 0,
      };

      await axiosClient.patch(`/employees/${targetEmployee.id}`, payload);

      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      toast.success("Employee updated successfully.", { id: loadingToastId });
      setIsEditModalOpen(false);
      setTargetEmployee(null);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update employee.";
      toast.error(`Error: ${message}`, { id: loadingToastId });
    }
  };

  // Delete Employee
  const handleDeleteEmployee = () => {
    if (!targetEmployee) return;
    setIsDeleteModalOpen(false);
    setTargetEmployee(null);
    toast.error("Hard deletion of employees is restricted for audit and payroll history compliance. Please terminate the employee instead.");
  };

  // Bulk Delete Selected
  const handleBulkDelete = () => {
    setSelectedIds(new Set());
    toast.error("Hard deletion of employees is restricted for audit and payroll history compliance. Please use 'Mark Terminated' to offboard them.");
  };

  // Bulk Status Update
  const handleBulkStatusChange = async (newStatus: EmployeeUiStatus) => {
    const ids = Array.from(selectedIds);
    setSelectedIds(new Set());
    if (ids.length === 0) return;

    // Filter out employees who are already in the target status
    const employeesList = employeesQuery.data?.items ?? [];
    const idsToUpdate = ids.filter(id => {
      const emp = employeesList.find(e => e.employee_id === id);
      if (!emp) return true;
      const statusMap: Record<string, string> = {
        active: "Active",
        inactive: "Inactive",
        terminated: "Terminated",
      };
      return statusMap[emp.employment_status] !== newStatus;
    });

    const skippedCount = ids.length - idsToUpdate.length;

    if (idsToUpdate.length === 0) {
      toast.info(`All selected employees are already "${newStatus}".`);
      return;
    }

    const loadingToastId = toast.loading(`Updating status for ${idsToUpdate.length} employees to ${newStatus}...`);

    try {
      const { axiosClient } = await import("@/lib/axios-client");
      const promises = idsToUpdate.map(async (id) => {
        const emp = employeesList.find(e => e.employee_id === id);
        if (newStatus === "Active") {
          if (emp && emp.employment_status === "terminated") {
            return axiosClient.post(`/employees/${id}/rehire`, {
              date_of_joining: new Date().toISOString().slice(0, 10),
            });
          } else {
            return axiosClient.post(`/employees/${id}/activate`);
          }
        } else if (newStatus === "Inactive") {
          return axiosClient.post(`/employees/${id}/deactivate`);
        } else if (newStatus === "Terminated") {
          return axiosClient.post(`/employees/${id}/terminate`, {
            effective_date: new Date().toISOString().slice(0, 10),
            reason: "Bulk status change via UI",
          });
        }
        return Promise.resolve();
      });

      await Promise.all(promises);
      queryClient.invalidateQueries({ queryKey: employeeKeys.all });
      
      if (skippedCount > 0) {
        toast.success(`Successfully updated status for ${idsToUpdate.length} employees (${skippedCount} were already "${newStatus}").`, { id: loadingToastId });
      } else {
        toast.success(`Successfully updated status for ${idsToUpdate.length} employees.`, { id: loadingToastId });
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Bulk status update failed.";
      toast.error(`Failed to update some employees: ${message}`, { id: loadingToastId });
    }
  };

  // Helper to parse CSV content into objects
  const parseCSVData = (text: string) => {
    const lines = text.split(/\r?\n/).map(line => line.trim()).filter(line => line !== "");
    if (lines.length < 2) return [];

    const headers = lines[0].split(",").map(h => h.trim().replace(/^["']|["']$/g, ""));
    const results: Record<string, string>[] = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i];
      const values: string[] = [];
      let currentVal = "";
      let inQuotes = false;
      for (let j = 0; j < line.length; j++) {
        const char = line[j];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          values.push(currentVal.trim().replace(/^["']|["']$/g, ""));
          currentVal = "";
        } else {
          currentVal += char;
        }
      }
      values.push(currentVal.trim().replace(/^["']|["']$/g, ""));

      const row: Record<string, string> = {};
      headers.forEach((h, index) => {
        row[h] = values[index] || "";
      });
      results.push(row);
    }
    return results;
  };

  // Client-side Import CSV handler
  const handleImportCSV = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      toast.error("Only CSV files are supported for client-side processing. Please save your spreadsheet as CSV and try again.");
      return;
    }

    return new Promise<void>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const text = e.target?.result as string;
          const rows = parseCSVData(text);
          if (rows.length === 0) {
            toast.error("No valid data found in CSV file.");
            resolve();
            return;
          }

          const { axiosClient } = await import("@/lib/axios-client");
          let successCount = 0;
          let failCount = 0;

          for (const row of rows) {
            const name = row.employee_name || row.name;
            const mobile = row.mobile_number || row.phone;
            const gender = row.gender || "Male";
            const joiningDate = row.date_of_joining || new Date().toISOString().slice(0, 10);

            if (!name || !mobile) {
              failCount++;
              continue;
            }

            const branchName = row.master_branch || row.branch || "";
            const deptName = row.department || "";
            const desigName = row.designation || "";

            const branchOpt = branchOptions?.find(b => b.branch_name.toLowerCase() === branchName.toLowerCase());
            const deptOpt = departmentOptions?.find(d => d.dept_name.toLowerCase() === deptName.toLowerCase());
            const desigOpt = designationOptions?.find(d => d.designation_name.toLowerCase() === desigName.toLowerCase());

            const branchId = branchOpt?.branch_id || (branchOptions?.[0]?.branch_id) || 1;
            const deptId = deptOpt?.dept_id || (departmentOptions?.[0]?.dept_id) || 1;
            const desigId = desigOpt?.designation_id || (designationOptions?.[0]?.designation_id) || 1;

            const payload = {
              employee_name: name,
              display_name: row.display_name || name,
              gender: gender === "Male" || gender === "Female" || gender === "Other" ? gender : "Male",
              mobile_country_code: "+91",
              mobile_number: mobile,
              email: row.email || null,
              address: row.address || null,
              master_branch_id: branchId,
              dept_id: deptId,
              designation_id: desigId,
              date_of_joining: joiningDate,
              employee_type: row.employee_type || "Full Time",
            };

            try {
              await axiosClient.post("/employees", payload);
              successCount++;
            } catch (err) {
              console.error("Failed to import row", row, err);
              failCount++;
            }
          }

          queryClient.invalidateQueries({ queryKey: employeeKeys.all });
          toast.success(`Import complete: ${successCount} imported successfully, ${failCount} failed.`);
          resolve();
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(new Error("Failed to read CSV file."));
      reader.readAsText(file);
    });
  };

  // Client-side Bulk Update CSV handler
  const handleBulkUpdateCSV = async (file: File) => {
    if (!file.name.endsWith(".csv")) {
      toast.error("Only CSV files are supported for client-side processing. Please save your spreadsheet as CSV and try again.");
      return;
    }

    return new Promise<void>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const text = e.target?.result as string;
          const rows = parseCSVData(text);
          if (rows.length === 0) {
            toast.error("No valid data found in CSV file.");
            resolve();
            return;
          }

          const { axiosClient } = await import("@/lib/axios-client");

          // Fetch existing employees to match codes (paginated to support backend page limit of 200)
          const allEmployees: any[] = [];
          let currentPage = 1;
          let hasMore = true;
          const PAGE_SIZE_LIMIT = 200;

          while (hasMore) {
            const response = await axiosClient.get<{ success: boolean; data: { items: any[]; pagination: { has_next: boolean } } }>(
              `/employees?page=${currentPage}&page_size=${PAGE_SIZE_LIMIT}`
            );
            const items = response.data?.data?.items || [];
            allEmployees.push(...items);
            
            const pagination = response.data?.data?.pagination;
            if (pagination && pagination.has_next) {
              currentPage++;
            } else {
              hasMore = false;
            }
          }

          const codeToIdMap = new Map<string, number>();
          allEmployees.forEach(emp => {
            if (emp.employee_code) {
              codeToIdMap.set(emp.employee_code.toLowerCase(), emp.employee_id);
            }
          });

          let successCount = 0;
          let failCount = 0;

          for (const row of rows) {
            const rawCode = row.employee_code || row.code;
            if (!rawCode) {
              failCount++;
              continue;
            }

            const code = rawCode.toLowerCase();
            const employeeId = codeToIdMap.get(code);

            if (!employeeId) {
              console.warn(`Employee code not found: ${rawCode}`);
              failCount++;
              continue;
            }

            const payload: Record<string, any> = {};
            if (row.employee_name || row.name) payload.employee_name = row.employee_name || row.name;
            if (row.display_name) payload.display_name = row.display_name;
            if (row.gender) payload.gender = row.gender;
            if (row.mobile_number || row.phone) payload.mobile_number = row.mobile_number || row.phone;
            if (row.email) payload.email = row.email;
            if (row.address) payload.address = row.address;
            if (row.employee_type) payload.employee_type = row.employee_type;

            const branchName = row.master_branch || row.branch;
            if (branchName) {
              const branchOpt = branchOptions?.find(b => b.branch_name.toLowerCase() === branchName.toLowerCase());
              if (branchOpt) payload.master_branch_id = branchOpt.branch_id;
            }

            const deptName = row.department;
            if (deptName) {
              const deptOpt = departmentOptions?.find(d => d.dept_name.toLowerCase() === deptName.toLowerCase());
              if (deptOpt) payload.dept_id = deptOpt.dept_id;
            }

            const desigName = row.designation;
            if (desigName) {
              const desigOpt = designationOptions?.find(d => d.designation_name.toLowerCase() === desigName.toLowerCase());
              if (desigOpt) payload.designation_id = desigOpt.designation_id;
            }

            if (Object.keys(payload).length === 0) {
              continue;
            }

            try {
              await axiosClient.patch(`/employees/${employeeId}`, payload);
              successCount++;
            } catch (err) {
              console.error("Failed to update row", row, err);
              failCount++;
            }
          }

          queryClient.invalidateQueries({ queryKey: employeeKeys.all });
          toast.success(`Bulk update complete: ${successCount} updated successfully, ${failCount} failed.`);
          resolve();
        } catch (err) {
          reject(err);
        }
      };
      reader.onerror = () => reject(new Error("Failed to read CSV file."));
      reader.readAsText(file);
    });
  };

  return (
    <div className="w-full space-y-6">
      {/* Main Title & Action Bar */}
      {uiState !== "error" && (
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex items-center space-x-2">
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Total Active Employees <span className="text-primary font-extrabold">{totalActiveEmployees}</span>
            </h1>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Bulk actions show when items are checked */}
            {selectedIds.size > 0 && uiState === "normal" && (
              <div className="flex items-center gap-2 mr-2 p-1 bg-muted/65 rounded-lg border border-border/60">
                <span className="text-[11px] font-bold px-2 text-foreground/80">
                  {selectedIds.size} Selected
                </span>
                <button
                  onClick={() => handleBulkStatusChange("Active")}
                  className="px-2 py-1 text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 rounded-md border border-emerald-500/20 transition-all cursor-pointer"
                >
                  Mark Active
                </button>
                <button
                  onClick={() => handleBulkStatusChange("Inactive")}
                  className="px-2 py-1 text-xs font-semibold bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 rounded-md border border-yellow-500/20 transition-all cursor-pointer"
                >
                  Mark Inactive
                </button>
                <button
                  onClick={() => handleBulkStatusChange("Terminated")}
                  className="px-2 py-1 text-xs font-semibold bg-orange-500/10 hover:bg-orange-500/20 text-orange-600 dark:text-orange-400 rounded-md border border-orange-500/20 transition-all cursor-pointer"
                >
                  Mark Terminated
                </button>
                <button
                  onClick={handleBulkDelete}
                  className="px-2 py-1 text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-400 rounded-md border border-rose-500/20 transition-all cursor-pointer"
                >
                  Delete Selected
                </button>
              </div>
            )}

            {canCreateEmployee && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setFormData({
                  employee_id: "",
                  name: "",
                  display_name: "",
                  mobile_number: "",
                  email: "",
                  gender: "Male",
                  punch_in_branch: branchOptions?.[0]?.branch_name || "",
                  master_branch: branchOptions?.[0]?.branch_name || "",
                  department: departmentOptions?.[0]?.dept_name || "",
                  designation: designationOptions?.[0]?.designation_name || "",
                  employee_type: "Full Time",
                  door_lock_permission: "Yes",
                  pf_number: "",
                  uan_number: "",
                  esic_number: "",
                  address: "",
                  date_of_joining: "",
                  status: "Active",
                  salary_type: "Monthly",
                  monthly_salary: "0",
                  payroll_group: "",
                  bank_name: "",
                  branch_name: "",
                  account_no: "",
                  ifsc_code: "",
                });
                setLegalDocsFiles({
                  "Aadhar Card": "No file chosen",
                  "Driving Licence": "No file chosen",
                  "PAN Card": "No file chosen",
                  "Passport Size Photo": "No file chosen"
                });
                setIsAddModalOpen(true);
              }}
              className="gap-1.5 shadow-sm shadow-primary/10"
            >
              <Plus className="h-4 w-4" />
              Add Employee
            </Button>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsColumnsModalOpen(true)}
              className="gap-1.5 text-foreground bg-card hover:bg-muted/30"
            >
              <Settings className="h-4 w-4 text-muted-foreground" />
              Edit Columns
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push("/employees/attendance-permission")}
              className="gap-1.5 text-foreground bg-card hover:bg-muted/30"
            >
              <Clock className="h-4 w-4 text-muted-foreground" />
              Attendance Permission
            </Button>

            {/* Actions dropdown */}
            {(canEditEmployee || canDeleteEmployee) && (
            <div className="relative" ref={actionsButtonRef}>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsActionsDropdownOpen(!isActionsDropdownOpen)}
                className="gap-1.5 text-foreground bg-card hover:bg-muted/30"
              >
                Actions
                <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
              </Button>

              {isActionsDropdownOpen && (
                <div className="absolute right-0 mt-1.5 w-56 bg-card border border-border rounded-lg shadow-xl py-1 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
                  {/* Import */}
                  <button
                    onClick={() => {
                      setIsActionsDropdownOpen(false);
                      setImportFile(null);
                      setIsImportModalOpen(true);
                    }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <Upload className="h-3.5 w-3.5 text-blue-500" />
                    Import Employees
                  </button>
                  {/* Download Sample */}
                  <button
                    onClick={handleDownloadSample}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <FileText className="h-3.5 w-3.5 text-green-500" />
                    Download Sample
                  </button>
                  {/* Bulk Update */}
                  <button
                    onClick={() => {
                      setIsActionsDropdownOpen(false);
                      setBulkUpdateFile(null);
                      setIsBulkUpdateModalOpen(true);
                    }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <FileDown className="h-3.5 w-3.5 text-purple-500" />
                    Bulk Update Employee
                  </button>
                  <div className="my-1 border-t border-border" />
                  {/* Export Excel */}
                  <button
                    onClick={handleExportExcel}
                    disabled={isExporting}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted/50 cursor-pointer transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                  >
                    {isExporting ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-500" />
                    ) : (
                      <Download className="h-3.5 w-3.5 text-emerald-500" />
                    )}
                    {isExporting ? "Exporting..." : "Export Excel"}
                  </button>
                  {/* View Downloads */}
                  <button
                    onClick={() => {
                      setIsActionsDropdownOpen(false);
                      setIsDownloadsModalOpen(true);
                    }}
                    className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs font-medium text-foreground hover:bg-muted/50 cursor-pointer transition-colors"
                  >
                    <FolderOpen className="h-3.5 w-3.5 text-amber-500" />
                    View Downloads
                  </button>
                </div>
              )}
            </div>
            )}
          </div>
        </div>
      )}

      {/* Advanced Filter panel (Standard in HRMS Dashboard system for ease of navigation) */}
      {uiState === "normal" && (
        <div className="p-4 bg-card border border-border rounded-xl shadow-xs grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3.5">
          <div className="relative">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <Search className="h-4 w-4 text-muted-foreground/60" />
            </span>
            <input
              type="text"
              placeholder="Search ID, name, contact..."
              value={searchTerm}
              onChange={e => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-input bg-card placeholder:text-foreground/40 focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary transition-colors"
            />
          </div>

          <div>
            <select
              value={selectedBranch}
              onChange={e => {
                setSelectedBranch(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-input bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Branches</option>
              {(branchOptions ?? []).map(b => (
                <option key={b.branch_id} value={b.branch_id}>{b.branch_name}</option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedDept}
              onChange={e => {
                setSelectedDept(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-input bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Departments</option>
              {(departmentOptions ?? []).map(d => (
                <option key={d.dept_id} value={d.dept_id}>{d.dept_name}</option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedDesignation}
              onChange={e => {
                setSelectedDesignation(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-input bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Designations</option>
              {(designationOptions ?? []).map(ds => (
                <option key={ds.designation_id} value={ds.designation_id}>{ds.designation_name}</option>
              ))}
            </select>
          </div>

          <div>
            <select
              value={selectedStatusFilter}
              onChange={e => {
                setSelectedStatusFilter(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-input bg-card text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="">All Statuses</option>
              {STATUS_FILTER_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* States Switcher rendering */}
      {(() => {
        // ERROR STATE UI
        if (uiState === "error") {
          return (
            <div className="flex flex-col items-center justify-center p-12 border border-border bg-card rounded-xl text-center shadow-xs">
              <div className="p-4 bg-rose-500/10 rounded-full mb-4 text-rose-500 dark:text-rose-400">
                <AlertTriangle className="h-10 w-10 animate-bounce" />
              </div>
              <h3 className="text-base font-bold text-foreground mb-1.5">Failed to load Employee records</h3>
              <p className="text-xs text-muted-foreground max-w-md mb-6 leading-relaxed">
                We could not fetch the employee registry from the server. Please check your connection and try again.
              </p>
              <div className="flex items-center gap-3">
                <Button variant="primary" size="sm" onClick={() => employeesQuery.refetch()}>
                  Retry Fetching
                </Button>
                <Button variant="outline" size="sm" onClick={() => toast.info("Contacting support...")}>
                  Contact Support
                </Button>
              </div>
            </div>
          );
        }

        // LOADING SKELETON UI
        if (uiState === "loading") {
          return (
            <div className="space-y-4">
              <div className="border border-border bg-card rounded-xl overflow-hidden shadow-xs">
                {/* Table Header skeleton */}
                <div className="grid grid-cols-8 gap-4 px-4 py-3 bg-muted/20 border-b border-border">
                  {[...Array(8)].map((_, i) => (
                    <Skeleton key={i} className="h-4 w-2/3" />
                  ))}
                </div>
                {/* Table Body rows skeletons */}
                <div className="divide-y divide-border">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="grid grid-cols-8 gap-4 px-4 py-4 items-center">
                      <Skeleton className="h-4 w-4" />
                      <Skeleton className="h-4 w-1/3" />
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-4 w-2/3" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-4 w-1/2" />
                      <Skeleton className="h-5 w-16" />
                      <Skeleton className="h-4 w-4 justify-self-end" />
                    </div>
                  ))}
                </div>
              </div>
              {/* Pagination skeleton */}
              <div className="flex items-center justify-between pt-2">
                <Skeleton className="h-4 w-48" />
                <div className="flex items-center space-x-2">
                  <Skeleton className="h-8 w-20" />
                  <Skeleton className="h-8 w-8" />
                  <Skeleton className="h-8 w-8" />
                  <Skeleton className="h-8 w-20" />
                </div>
              </div>
            </div>
          );
        }

        // EMPTY STATE UI
        if (uiState === "empty") {
          return (
            <EmptyState
              title="No employees found"
              description="There are no records matching your active filters or the employee directory is currently empty."
              action={
                <div className="flex items-center gap-3">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      clearAllFilters();
                      toast.success("Filters cleared.");
                    }}
                  >
                    Clear Filters
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setIsAddModalOpen(true)}
                  >
                    Add Employee
                  </Button>
                </div>
              }
            />
          );
        }

        // NORMAL DATA STATE UI
        return (
          <div className="space-y-4">
            <div className="w-full overflow-x-auto rounded-xl border border-border bg-card shadow-xs">
              <table className="w-full text-left border-collapse text-sm text-foreground">
                <thead className="bg-[#f0f4f9] dark:bg-slate-900 border-b border-border font-semibold text-xs text-muted-foreground uppercase tracking-wider">
                  <tr>
                    {(canEditEmployee || canDeleteEmployee) && (
                      <th className="px-4 py-3.5 w-12 text-center align-middle">
                        <input
                          type="checkbox"
                          checked={isAllSelected}
                          onChange={e => handleSelectAll(e.target.checked)}
                          className="h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                        />
                      </th>
                    )}
                    {columnsList.map((col) => {
                      if (!col.checked) return null;
                      return (
                        <th
                          key={col.key}
                          onClick={() => handleSort(col.key)}
                          className="px-4 py-3.5 font-bold text-slate-800 dark:text-slate-200 cursor-pointer hover:bg-muted/50 select-none transition-colors whitespace-nowrap"
                        >
                          {col.label} {getSortIcon(col.key)}
                        </th>
                      );
                    })}
                    <th className="px-4 py-3.5 font-bold text-slate-800 dark:text-slate-200 text-center w-20">
                      Action
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {paginatedEmployees.map(emp => (
                    <tr
                      key={emp.id}
                      className={`hover:bg-muted/20 transition-colors ${
                        selectedIds.has(emp.id) ? "bg-primary/5 hover:bg-primary/10" : ""
                      }`}
                    >
                      {(canEditEmployee || canDeleteEmployee) && (
                        <td className="px-4 py-3 w-12 text-center align-middle">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(emp.id)}
                            onChange={e => handleSelectItem(emp.id, e.target.checked)}
                            className="h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer"
                          />
                        </td>
                      )}

                      {columnsList.map((col) => {
                        if (!col.checked) return null;
                        if (col.key === "master_branch") {
                          return (
                            <td key={col.key} className="px-4 py-3 align-middle whitespace-nowrap">
                              <button
                                onClick={() => {
                                  toast.info(`Branch details for: ${emp.master_branch}`);
                                }}
                                className="text-primary hover:underline font-medium text-left cursor-pointer focus:outline-none"
                              >
                                {emp.master_branch}
                              </button>
                            </td>
                          );
                        }
                        if (col.key === "status") {
                          return (
                            <td key={col.key} className="px-4 py-3 align-middle relative whitespace-nowrap">
                              {!canEditEmployee ? (
                                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border border-border/40">
                                  <span
                                    className={`h-1.5 w-1.5 rounded-full ${
                                      emp.status === "Active"
                                        ? "bg-emerald-500"
                                        : emp.status === "Inactive"
                                        ? "bg-yellow-500"
                                        : "bg-orange-500"
                                    }`}
                                  />
                                  <span
                                    className={
                                      emp.status === "Active"
                                        ? "text-emerald-700 dark:text-emerald-400"
                                        : emp.status === "Inactive"
                                        ? "text-yellow-700 dark:text-yellow-400"
                                        : "text-orange-700 dark:text-orange-400"
                                    }
                                  >
                                    {emp.status}
                                  </span>
                                </span>
                              ) : (
                                <>
                                  <button
                                    onClick={e => {
                                      e.stopPropagation();
                                      setActiveStatusRowId(activeStatusRowId === emp.id ? null : emp.id);
                                      setActiveActionRowId(null);
                                    }}
                                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold transition-all hover:bg-muted focus:outline-none cursor-pointer border border-border/40"
                                  >
                                    <span
                                      className={`h-1.5 w-1.5 rounded-full ${
                                        emp.status === "Active"
                                          ? "bg-emerald-500"
                                          : emp.status === "Inactive"
                                          ? "bg-yellow-500"
                                          : "bg-orange-500"
                                      }`}
                                    />
                                    <span
                                      className={
                                        emp.status === "Active"
                                          ? "text-emerald-700 dark:text-emerald-400"
                                          : emp.status === "Inactive"
                                          ? "text-yellow-700 dark:text-yellow-400"
                                          : "text-orange-700 dark:text-orange-400"
                                      }
                                    >
                                      {emp.status}
                                    </span>
                                    <ChevronDown className="h-3.5 w-3.5 text-muted-foreground/80" />
                                  </button>

                                  {/* Status dropdown */}
                                  {activeStatusRowId === emp.id && (
                                    <div
                                      ref={statusMenuRef}
                                      className="absolute left-4 top-10 mt-1 w-44 bg-card border border-border rounded-xl shadow-lg p-1.5 z-50 animate-in fade-in duration-100 space-y-0.5"
                                    >
                                      {UI_STATUSES.map((statusVal) => {
                                        const isSelected = emp.status === statusVal;
                                        const textColors: Record<EmployeeUiStatus, string> = {
                                          Active: "text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/5",
                                          Inactive: "text-yellow-600 dark:text-yellow-400 hover:bg-yellow-500/5",
                                          Terminated: "text-orange-600 dark:text-orange-400 hover:bg-orange-500/5",
                                        };
                                        return (
                                          <button
                                            key={statusVal}
                                            onClick={() => handleStatusChange(statusVal)}
                                            className={`w-full text-left px-2.5 py-1.5 text-xs font-bold rounded-lg flex items-center transition-all cursor-pointer ${textColors[statusVal]}`}
                                          >
                                            {isSelected ? (
                                              <span className="flex items-center justify-center h-4 w-4 rounded-full border-2 border-blue-600 dark:border-blue-400 mr-2.5 shrink-0">
                                                <span className="h-1.5 w-1.5 rounded-full bg-blue-600 dark:bg-blue-400" />
                                              </span>
                                            ) : (
                                              <span className="h-4 w-4 rounded-full border-2 border-slate-200 dark:border-slate-800 mr-2.5 shrink-0" />
                                            )}
                                            {statusVal}
                                          </button>
                                        );
                                      })}
                                    </div>
                                  )}
                                </>
                              )}
                            </td>
                          );
                        }

                        // Default column rendering
                        return (
                          <td key={col.key} className="px-4 py-3 align-middle text-muted-foreground font-medium whitespace-nowrap">
                            {renderCellContent(emp, col.key)}
                          </td>
                        );
                      })}

                      <td className="px-4 py-3 align-middle text-center relative">
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            setActiveActionRowId(activeActionRowId === emp.id ? null : emp.id);
                            setActiveStatusRowId(null);
                          }}
                          className="p-1 hover:bg-muted rounded-md transition-colors text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>

                        {/* Action row dropdown */}
                        {activeActionRowId === emp.id && (
                          <div
                            ref={actionMenuRef}
                            className="absolute right-12 top-2 mt-1 w-44 bg-card border border-border rounded-lg shadow-lg py-1.5 z-50 animate-in fade-in duration-100"
                          >
                            <button
                              onClick={() => handleActionClick("shift_logs", emp)}
                              className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted/70 flex items-center gap-2 cursor-pointer"
                            >
                              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                              Shift Logs
                            </button>
                            <button
                              onClick={() => handleActionClick("document_library", emp)}
                              className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted/70 flex items-center gap-2 cursor-pointer"
                            >
                              <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                              Document Library
                            </button>
                            <button
                              onClick={() => handleActionClick("punch_branch", emp)}
                              className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted/70 flex items-center gap-2 cursor-pointer"
                            >
                              <Fingerprint className="h-3.5 w-3.5 text-muted-foreground" />
                              Punch In Branch
                            </button>
                            {(canEditEmployee || canDeleteEmployee) && <div className="border-t border-border my-1" />}
                            {canEditEmployee && (
                              <button
                                onClick={() => handleActionClick("edit", emp)}
                                className="w-full text-left px-3 py-1.5 text-xs text-foreground hover:bg-muted/70 flex items-center gap-2 cursor-pointer"
                              >
                                <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                                Edit
                              </button>
                            )}
                            {canDeleteEmployee && (
                              <button
                                onClick={() => handleActionClick("delete", emp)}
                                className="w-full text-left px-3 py-1.5 text-xs text-destructive hover:bg-rose-500/10 flex items-center gap-2 cursor-pointer"
                              >
                                <Trash2 className="h-3.5 w-3.5 text-destructive" />
                                Delete
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Table Footer / Pagination */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2.5">
              <span className="text-xs font-semibold text-muted-foreground/80">
                Showing {Math.min((currentPage - 1) * pageSize + 1, totalRecords)} to{" "}
                {Math.min(currentPage * pageSize, totalRecords)} of {totalRecords} Results
              </span>

              <div className="flex flex-wrap items-center gap-3">
                {/* Page Size select */}
                <div className="flex items-center space-x-1.5">
                  <select
                    value={pageSize}
                    onChange={e => {
                      setPageSize(Number(e.target.value));
                      setCurrentPage(1);
                    }}
                    className="px-2.5 py-1 text-xs rounded-md border border-input bg-card text-foreground font-semibold focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                  >
                    <option value={10}>10 / Page</option>
                    <option value={20}>20 / Page</option>
                    <option value={50}>50 / Page</option>
                  </select>
                </div>

                {/* Pagination Controls */}
                <div className="flex items-center space-x-1">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-1 px-2.5 text-xs font-semibold border border-border bg-card rounded-md hover:bg-muted/40 disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" />
                    Previous
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => {
                    // Show only around current page if there are many pages
                    if (totalPages > 5 && Math.abs(currentPage - p) > 1 && p !== 1 && p !== totalPages) {
                      if (p === 2 || p === totalPages - 1) {
                        return <span key={p} className="text-xs text-muted-foreground px-1">...</span>;
                      }
                      return null;
                    }
                    return (
                      <button
                        key={p}
                        onClick={() => setCurrentPage(p)}
                        className={`h-8 w-8 text-xs font-bold rounded-md transition-all cursor-pointer ${
                          currentPage === p
                            ? "bg-primary text-primary-foreground font-extrabold shadow-sm"
                            : "border border-border bg-card hover:bg-muted/40 text-foreground"
                        }`}
                      >
                        {p}
                      </button>
                    );
                  })}

                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="p-1 px-2.5 text-xs font-semibold border border-border bg-card rounded-md hover:bg-muted/40 disabled:opacity-40 disabled:pointer-events-none transition-colors cursor-pointer flex items-center gap-1"
                  >
                    Next
                    <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}

      {/* ADD EMPLOYEE DRAWER */}
      {isAddModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-[100] flex justify-end animate-in fade-in duration-300">
          <div className="bg-card w-full max-w-lg h-full border-l border-border shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-300">
            {/* Header */}
            <div className="px-6 py-4 flex items-center justify-between border-b border-border bg-slate-50 dark:bg-slate-900/60">
              <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">Add Details</h3>
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Scrollable Form Body */}
            <form
              onSubmit={handleCreateEmployee}
              className="flex-1 flex flex-col justify-between overflow-hidden"
            >
              <div className="flex-1 overflow-y-auto divide-y divide-border">
                {/* 1. Basic Details */}
                <div>
                  <div
                    onClick={() => toggleSection("Basic Details")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Basic Details</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Basic Details"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Basic Details"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      {/* Employee Code * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Employee Code <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <Input
                          required
                          value={formData.employee_id}
                          onChange={e => setFormData({ ...formData, employee_id: e.target.value })}
                        />
                      </div>

                      {/* Employee Name * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Employee Name <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <Input
                          required
                          value={formData.name}
                          onChange={e => setFormData({ ...formData, name: e.target.value })}
                          placeholder="Enter Employee Name"
                        />
                      </div>

                      {/* Display Name */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Display Name</label>
                        <Input
                          value={formData.display_name}
                          onChange={e => setFormData({ ...formData, display_name: e.target.value })}
                          placeholder="Enter Display Name"
                        />
                      </div>

                      {/* Mobile Number * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Mobile Number <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <div className="flex gap-2">
                          <select
                            value="+91"
                            onChange={() => {}}
                            className="w-20 rounded-md border border-input bg-card px-2.5 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                          >
                            <option value="+91">+91</option>
                            <option value="+1">+1</option>
                            <option value="+44">+44</option>
                          </select>
                          <Input
                            required
                            value={formData.mobile_number}
                            onChange={e => setFormData({ ...formData, mobile_number: e.target.value })}
                            placeholder="Enter Number"
                            className="flex-1"
                          />
                        </div>
                      </div>

                      {/* Email */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Email</label>
                        <Input
                          type="email"
                          value={formData.email}
                          onChange={e => setFormData({ ...formData, email: e.target.value })}
                          placeholder="Enter Employee Email"
                        />
                      </div>

                      {/* Gender * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Gender <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <div className="flex items-center gap-6 mt-1">
                          {(["Male", "Female", "Other"] as const).map((g) => (
                            <label key={g} className="flex items-center gap-2 text-xs font-semibold text-foreground/80 cursor-pointer">
                              <input
                                type="radio"
                                name="gender"
                                value={g}
                                checked={formData.gender === g}
                                onChange={() => setFormData({ ...formData, gender: g })}
                                className="h-4 w-4 text-primary border-slate-350 focus:ring-primary"
                              />
                              {g}
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Punch In Branch * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Punch In Branch <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <select
                          required
                          value={formData.punch_in_branch}
                          onChange={e => setFormData({ ...formData, punch_in_branch: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Branches</option>
                          {branchOptions?.map(b => (
                            <option key={b.branch_id} value={b.branch_name}>{b.branch_name}</option>
                          ))}
                        </select>
                      </div>

                      {/* Master Branch * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Master Branch <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <select
                          required
                          value={formData.master_branch}
                          onChange={e => setFormData({ ...formData, master_branch: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Master Branches</option>
                          {branchOptions?.map(b => (
                            <option key={b.branch_id} value={b.branch_name}>{b.branch_name}</option>
                          ))}
                        </select>
                      </div>

                      {/* Department * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Department <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <select
                          required
                          value={formData.department}
                          onChange={e => setFormData({ ...formData, department: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Department</option>
                          {departmentOptions?.map(d => (
                            <option key={d.dept_id} value={d.dept_name}>{d.dept_name}</option>
                          ))}
                        </select>
                      </div>

                      {/* Designation * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Designation <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <select
                          required
                          value={formData.designation}
                          onChange={e => setFormData({ ...formData, designation: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Designation</option>
                          {designationOptions?.map(d => (
                            <option key={d.designation_id} value={d.designation_name}>{d.designation_name}</option>
                          ))}
                        </select>
                      </div>

                      {/* Employee Type */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Employee Type</label>
                        <select
                          value={formData.employee_type}
                          onChange={e => setFormData({ ...formData, employee_type: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Employee Type</option>
                          <option value="Full Time">Full Time</option>
                          <option value="Part Time">Part Time</option>
                          <option value="Contract">Contract</option>
                          <option value="Intern">Intern</option>
                        </select>
                      </div>

                      {/* Door Lock Permission * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Door Lock Permission <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <div className="flex items-center gap-6 mt-1">
                          {(["Yes", "No"] as const).map((v) => (
                            <label key={v} className="flex items-center gap-2 text-xs font-semibold text-foreground/80 cursor-pointer">
                              <input
                                type="radio"
                                name="door_lock_permission"
                                value={v}
                                checked={formData.door_lock_permission === v}
                                onChange={() => setFormData({ ...formData, door_lock_permission: v })}
                                className="h-4 w-4 text-primary border-slate-350 focus:ring-primary"
                              />
                              {v}
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Provident Fund (PF) */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Provident Fund (PF)</label>
                        <Input
                          value={formData.pf_number}
                          onChange={e => setFormData({ ...formData, pf_number: e.target.value })}
                          placeholder="Enter PF Account Number"
                        />
                      </div>

                      {/* Universal Account Number (UAN) */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Universal Account Number (UAN)</label>
                        <Input
                          value={formData.uan_number}
                          onChange={e => setFormData({ ...formData, uan_number: e.target.value })}
                          placeholder="Enter 12-Digit UAN Number"
                        />
                      </div>

                      {/* Employee State Insurance Corporation (ESIC) */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Employee State Insurance Corporation (ESIC)
                        </label>
                        <Input
                          value={formData.esic_number}
                          onChange={e => setFormData({ ...formData, esic_number: e.target.value })}
                          placeholder="Enter 10-Digit ESIC IP Number"
                        />
                      </div>

                      {/* Address */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Address</label>
                        <textarea
                          value={formData.address}
                          onChange={e => setFormData({ ...formData, address: e.target.value })}
                          placeholder=""
                          rows={3}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary placeholder-slate-400"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* 2. Salary Details */}
                <div>
                  <div
                    onClick={() => toggleSection("Salary Details")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Salary Details</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Salary Details"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Salary Details"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      {/* Date of Joining */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Date of Joining</label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                            <Calendar className="h-4 w-4" />
                          </span>
                          <Input
                            type="date"
                            value={formData.date_of_joining}
                            onChange={e => setFormData({ ...formData, date_of_joining: e.target.value })}
                            className="pl-10 cursor-pointer"
                          />
                        </div>
                      </div>

                      {/* Salary Type * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Salary Type <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <div className="flex items-center gap-6 mt-1">
                          {(["Monthly", "Hourly", "Compliance"] as const).map((t) => (
                            <label key={t} className="flex items-center gap-2 text-xs font-semibold text-foreground/80 cursor-pointer">
                              <input
                                type="radio"
                                name="salary_type"
                                value={t}
                                checked={formData.salary_type === t}
                                onChange={() => setFormData({ ...formData, salary_type: t })}
                                className="h-4 w-4 text-primary border-slate-350 focus:ring-primary"
                              />
                              {t}
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Monthly Salary * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Monthly Salary <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <div className="relative">
                          <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500 font-medium">
                            ₹
                          </span>
                          <Input
                            required
                            type="number"
                            value={formData.monthly_salary}
                            onChange={e => setFormData({ ...formData, monthly_salary: e.target.value })}
                            className="pl-8"
                            placeholder="₹ 0"
                          />
                        </div>
                      </div>

                      {/* Payroll Group * */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">
                          Payroll Group <span className="text-red-550 dark:text-red-400">*</span>
                        </label>
                        <select
                          required
                          value={formData.payroll_group}
                          onChange={e => setFormData({ ...formData, payroll_group: e.target.value })}
                          className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary cursor-pointer"
                        >
                          <option value="">Select Payroll Group</option>
                          <option value="General Staff">General Staff</option>
                          <option value="Executive Pool">Executive Pool</option>
                          <option value="Contractors">Contractors</option>
                        </select>
                      </div>
                    </div>
                  )}
                </div>

                {/* 3. Bank Details */}
                <div>
                  <div
                    onClick={() => toggleSection("Bank Details")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Bank Details</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Bank Details"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Bank Details"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      {/* Bank Name */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Bank Name</label>
                        <Input
                          value={formData.bank_name}
                          onChange={e => setFormData({ ...formData, bank_name: e.target.value })}
                          placeholder="Enter Bank Name"
                        />
                      </div>

                      {/* Branch Name */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Branch Name</label>
                        <Input
                          value={formData.branch_name}
                          onChange={e => setFormData({ ...formData, branch_name: e.target.value })}
                          placeholder="Enter Branch Name"
                        />
                      </div>

                      {/* Account No */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Account No</label>
                        <Input
                          value={formData.account_no}
                          onChange={e => setFormData({ ...formData, account_no: e.target.value })}
                          placeholder="Enter Account No"
                        />
                      </div>

                      {/* IFSC Code */}
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">IFSC Code</label>
                        <Input
                          value={formData.ifsc_code}
                          onChange={e => setFormData({ ...formData, ifsc_code: e.target.value })}
                          placeholder="Enter IFSC Code"
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* 4. Legal Documents */}
                <div>
                  <div
                    onClick={() => toggleSection("Legal Documents")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Legal Documents</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Legal Documents"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Legal Documents"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      {[
                        { label: "Aadhar Card", key: "Aadhar Card" },
                        { label: "Driving Licence", key: "Driving Licence" },
                        { label: "PAN Card", key: "PAN Card" },
                        { label: "Passport Size Photo", key: "Passport Size Photo" }
                      ].map((doc) => {
                        return (
                          <div key={doc.key} className="space-y-1">
                            <label className="text-xs font-semibold text-foreground/80">{doc.label}</label>
                            <div
                              onClick={() => {
                                const inputEl = document.getElementById(`file-input-${doc.key}`) as HTMLInputElement;
                                inputEl?.click();
                              }}
                              className="flex items-center border border-input rounded-md bg-card shadow-sm cursor-pointer overflow-hidden text-sm"
                            >
                              <span className="bg-slate-100 dark:bg-slate-900 px-4 py-2 border-r border-input font-medium text-slate-700 dark:text-slate-350 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors">
                                Choose file
                              </span>
                              <span className="px-4 py-2 text-slate-500 dark:text-slate-400 flex-1 truncate">
                                {legalDocsFiles[doc.key]}
                              </span>
                              <input
                                id={`file-input-${doc.key}`}
                                type="file"
                                onChange={(e) => {
                                  if (e.target.files && e.target.files[0]) {
                                    setLegalDocsFiles(prev => ({
                                      ...prev,
                                      [doc.key]: e.target.files![0].name
                                    }));
                                  } else {
                                    setLegalDocsFiles(prev => ({
                                      ...prev,
                                      [doc.key]: "No file chosen"
                                    }));
                                  }
                                }}
                                className="hidden"
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* 5. Emergency Contact Information */}
                <div>
                  <div
                    onClick={() => toggleSection("Emergency Contact Information")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Emergency Contact Information</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Emergency Contact Information"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Emergency Contact Information"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-foreground/80">Contact Person</label>
                          <Input placeholder="e.g. Jane Doe" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-foreground/80">Relationship</label>
                          <Input placeholder="e.g. Spouse" />
                        </div>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Contact Number</label>
                        <Input placeholder="e.g. +1 555-0199" />
                      </div>
                    </div>
                  )}
                </div>

                {/* 6. Personal Information */}
                <div>
                  <div
                    onClick={() => toggleSection("Personal Information")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Personal Information</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Personal Information"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Personal Information"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-foreground/80">Date of Birth</label>
                          <Input type="date" />
                        </div>
                        <div className="space-y-1">
                          <label className="text-xs font-semibold text-foreground/80">Gender</label>
                          <select className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary">
                            <option>Male</option>
                            <option>Female</option>
                            <option>Other</option>
                          </select>
                        </div>
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Personal Email</label>
                        <Input type="email" placeholder="e.g. name@example.com" />
                      </div>
                    </div>
                  )}
                </div>

                {/* 7. Reference */}
                <div>
                  <div
                    onClick={() => toggleSection("Reference")}
                    className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                  >
                    <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">Reference</span>
                    <ChevronDown className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${expandedSections["Reference"] ? "rotate-180" : ""}`} />
                  </div>
                  {expandedSections["Reference"] && (
                    <div className="px-6 pb-5 space-y-4 animate-in fade-in slide-in-from-top-1 duration-150">
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Reference Name</label>
                        <Input placeholder="e.g. John Smith" />
                      </div>
                      <div className="space-y-1">
                        <label className="text-xs font-semibold text-foreground/80">Contact Details</label>
                        <Input placeholder="e.g. Email / Mobile" />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Bottom Footer Actions */}
              <div className="px-6 py-4 bg-[#f0f4f9] dark:bg-slate-900 border-t border-border flex items-center justify-between">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => toast.info("Form configuration mode...")}
                  className="h-9 px-4 text-xs font-bold bg-white dark:bg-slate-800 border-slate-200 hover:bg-slate-50 text-blue-600 dark:text-blue-400 cursor-pointer rounded-lg"
                >
                  Edit Form
                </Button>
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setIsAddModalOpen(false)}
                    className="h-9 px-4 text-xs font-bold bg-white dark:bg-slate-800 border-slate-200 hover:bg-slate-50 text-slate-700 dark:text-slate-200 cursor-pointer rounded-lg"
                  >
                    Close
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    className="h-9 px-4 text-xs font-bold cursor-pointer rounded-lg"
                  >
                    Save Details
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT EMPLOYEE MODAL */}
      {isEditModalOpen && targetEmployee && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-lg w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <h3 className="text-sm font-bold text-foreground">Edit Employee Record</h3>
              <button
                onClick={() => {
                  setIsEditModalOpen(false);
                  setTargetEmployee(null);
                }}
                className="p-1 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <form onSubmit={handleSaveEmployee} className="p-5 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Employee ID *</label>
                  <Input
                    required
                    value={formData.employee_id}
                    onChange={e => setFormData({ ...formData, employee_id: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Employee Name *</label>
                  <Input
                    required
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Master Branch</label>
                  <Input
                    value={formData.master_branch}
                    onChange={e => setFormData({ ...formData, master_branch: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Department</label>
                  <Input
                    value={formData.department}
                    onChange={e => setFormData({ ...formData, department: e.target.value })}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Designation</label>
                  <Input
                    value={formData.designation}
                    onChange={e => setFormData({ ...formData, designation: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-foreground/80">Date of Joining</label>
                  <Input
                    value={formData.date_of_joining}
                    onChange={e => setFormData({ ...formData, date_of_joining: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-foreground/80">Tags (Status)</label>
                <select
                  value={formData.status}
                  onChange={e => setFormData({ ...formData, status: e.target.value as EmployeeUiStatus })}
                  className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary"
                >
                  {UI_STATUSES.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsEditModalOpen(false);
                    setTargetEmployee(null);
                  }}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm">
                  Save Changes
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE CONFIRM MODAL */}
      {isDeleteModalOpen && targetEmployee && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-lg w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-5 flex items-start gap-4">
              <div className="p-2.5 bg-rose-500/10 rounded-full text-rose-500 shrink-0">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-foreground">Confirm Employee Deletion</h3>
                <p className="text-xs text-muted-foreground">
                  Are you sure you want to permanently delete the employee record for{" "}
                  <strong className="text-foreground">{targetEmployee.name}</strong> (ID: {targetEmployee.employee_id})? This action cannot be undone.
                </p>
              </div>
            </div>
            <div className="p-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsDeleteModalOpen(false);
                  setTargetEmployee(null);
                }}
              >
                Cancel
              </Button>
              <Button variant="destructive" size="sm" onClick={handleDeleteEmployee}>
                Delete Employee
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* EDIT COLUMNS DRAWER */}
      {isColumnsModalOpen && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-xs z-[100] flex justify-end animate-in fade-in duration-200">
          {/* Backdrop click to close */}
          <div className="absolute inset-0" onClick={() => setIsColumnsModalOpen(false)} />
          
          {/* Drawer content */}
          <div className="relative w-full max-w-sm h-full bg-background shadow-2xl flex flex-col z-10 animate-in slide-in-from-right duration-250">
            {/* Header */}
            <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-[#edf5ff] dark:bg-slate-900/60">
              <h3 className="text-base font-semibold text-slate-800 dark:text-slate-200">Edit Columns</h3>
              <button
                onClick={() => setIsColumnsModalOpen(false)}
                className="p-1 hover:bg-slate-250 dark:hover:bg-slate-800 rounded-md text-slate-500 hover:text-slate-850 dark:hover:text-slate-200 cursor-pointer focus:outline-none transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Search Input */}
            <div className="p-4 border-b border-border">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <Input
                  type="text"
                  placeholder="Search"
                  value={columnsSearchQuery}
                  onChange={(e) => setColumnsSearchQuery(e.target.value)}
                  className="pl-10 w-full"
                />
              </div>
            </div>

            {/* Scrollable Column List */}
            <div className="flex-1 overflow-y-auto divide-y divide-slate-100 dark:divide-slate-800">
              {columnsList
                .filter(col => col.label.toLowerCase().includes(columnsSearchQuery.toLowerCase()))
                .map((col) => {
                  return (
                    <div key={col.key} className="px-6 py-3.5 flex items-center justify-between hover:bg-slate-50/50 dark:hover:bg-slate-900/20 transition-colors">
                      <div className="flex items-center gap-3">
                        <GripVertical className="h-4 w-4 text-slate-350 dark:text-slate-600 cursor-grab" />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">{col.label}</span>
                      </div>
                      
                      {/* Toggle Switch */}
                      <button
                        type="button"
                        onClick={() => handleToggleColumnByKey(col.key)}
                        className={`relative inline-flex h-5.5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                          col.checked ? 'bg-[#007bff]' : 'bg-slate-300 dark:bg-slate-750'
                        }`}
                      >
                        <span
                          className={`pointer-events-none inline-block h-4.5 w-4.5 transform rounded-full bg-white shadow-md ring-0 transition duration-200 ease-in-out ${
                            col.checked ? 'translate-x-4.5' : 'translate-x-0'
                          }`}
                        />
                      </button>
                    </div>
                  );
                })}
            </div>

            {/* Footer */}
            <div className="p-4 bg-[#edf5ff] dark:bg-slate-900/40 border-t border-border flex items-center justify-between gap-4">
              <Button
                variant="outline"
                onClick={handleResetColumns}
                className="flex-1 bg-white hover:bg-slate-50 text-slate-700 border-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-300 dark:border-slate-700"
              >
                Reset To Default
              </Button>
              <Button
                onClick={handleSaveColumns}
                className="flex-1 bg-primary hover:bg-primary/95 text-white"
              >
                Save
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ATTENDANCE PERMISSION MODAL */}
      {isAttendancePermModalOpen && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-lg w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <h3 className="text-sm font-bold text-foreground">Attendance Permission Settings</h3>
              <button
                onClick={() => setIsAttendancePermModalOpen(false)}
                className="p-1 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Configure global attendance and punch overrides for all branches of <strong className="text-foreground">Itcode Infotech</strong>.
              </p>
              <div className="space-y-3">
                <Checkbox label="Enable Location-restricted Punching" defaultChecked />
                <Checkbox label="Allow Web Browser Punch-in (Standard)" defaultChecked />
                <Checkbox label="Require Biometric Fingerprint verification" />
                <Checkbox label="Enable Automatic Overtime calculation" defaultChecked />
              </div>
            </div>
            <div className="p-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <Button variant="outline" size="sm" onClick={() => setIsAttendancePermModalOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsAttendancePermModalOpen(false);
                  toast.success("Attendance Permissions updated globally.");
                }}
              >
                Apply Changes
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* SHIFT LOGS MODAL */}
      {isShiftLogsOpen && targetEmployee && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 flex items-center justify-between bg-[#f0f4f9] dark:bg-slate-900 border-b border-border">
              <div>
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Shift Logs</h3>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                  {targetEmployee.employee_id} - {targetEmployee.name}
                </p>
              </div>
              <button
                onClick={() => {
                  setIsShiftLogsOpen(false);
                  setTargetEmployee(null);
                  setSelectedMonth("2026-05"); // Reset default
                  setIsMonthPickerOpen(false);
                }}
                className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              {/* Date Filter Bar */}
              <div className="flex justify-end relative">
                <button
                  onClick={() => setIsMonthPickerOpen(!isMonthPickerOpen)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold border border-border hover:bg-muted/50 rounded-lg shadow-2xs transition-colors cursor-pointer bg-card text-foreground"
                >
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span>{formatMonthYear(selectedMonth)}</span>
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                </button>

                {/* Month Picker Dropdown */}
                {isMonthPickerOpen && (
                  <div className="absolute right-0 top-10 mt-1 bg-card border border-border rounded-lg shadow-lg p-3 z-50 grid grid-cols-3 gap-2 w-64 animate-in fade-in duration-100">
                    {MONTHS_LIST.map((m) => (
                      <button
                        key={m.val}
                        onClick={() => {
                          setSelectedMonth(m.val);
                          setIsMonthPickerOpen(false);
                        }}
                        className={`px-2 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer text-center ${
                          selectedMonth === m.val
                            ? "bg-primary text-primary-foreground"
                            : "hover:bg-muted text-foreground"
                        }`}
                      >
                        {m.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Table Container */}
              <div className="w-full overflow-hidden rounded-xl border border-border bg-card">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-900 border-b border-border text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                      <th className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">Log</th>
                      <th className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">Detail</th>
                      <th className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">Type</th>
                      <th className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">Old Data</th>
                      <th className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-200">Modified By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SHIFT_LOGS.length > 0 ? (
                      SHIFT_LOGS.map((log, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-border last:border-0 hover:bg-muted/30 transition-colors text-xs text-foreground"
                        >
                          <td className="px-4 py-3 font-medium">{log.log}</td>
                          <td className="px-4 py-3">{log.detail}</td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold ${
                              log.type === "Create"
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
                            }`}>
                              {log.type}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-muted-foreground">{log.oldData}</td>
                          <td className="px-4 py-3 font-medium">{log.modifiedBy}</td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="py-24 text-center">
                          <div className="flex flex-col items-center justify-center">
                            <div className="w-14 h-14 rounded-full bg-blue-50 dark:bg-blue-950/40 flex items-center justify-center text-blue-500 dark:text-blue-400 mb-3">
                              <Search className="h-5 w-5" />
                            </div>
                            <span className="text-sm font-semibold text-slate-700 dark:text-slate-350">
                              No Data Found
                            </span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* DOCUMENT LIBRARY MODAL */}
      {isDocLibraryOpen && targetEmployee && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-3xl overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="px-6 py-4 flex items-center justify-between bg-[#f0f4f9] dark:bg-slate-900 border-b border-border">
              <div>
                <h3 className="text-lg font-bold text-slate-800 dark:text-slate-100">Document Library</h3>
              </div>
              <button
                onClick={() => {
                  setIsDocLibraryOpen(false);
                  setTargetEmployee(null);
                }}
                className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-800 rounded-md text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer focus:outline-none"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {REQUIRED_DOCS.map((docName) => {
                  const doc = uploadedDocs[docName];
                  return (
                    <div
                      key={docName}
                      className="border border-border rounded-xl bg-card overflow-hidden shadow-xs flex flex-col transition-all hover:shadow-sm"
                    >
                      {/* Hidden File Input */}
                      <input
                        type="file"
                        id={`file-input-${docName}`}
                        className="hidden"
                        onChange={(e) => handleFileUpload(docName, e)}
                      />

                      {/* Top Half: Preview Area */}
                      <div className="flex-1 bg-slate-50/50 dark:bg-slate-900/30 p-6 flex items-center justify-center border-b border-border/60 min-h-[160px]">
                        {doc ? (
                          <div className="flex flex-col items-center text-center space-y-2">
                            <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center text-primary">
                              <FolderOpen className="h-7 w-7" />
                            </div>
                            <div className="max-w-[200px]">
                              <p className="text-xs font-bold text-foreground truncate" title={doc.fileName}>
                                {doc.fileName}
                              </p>
                              <p className="text-[10px] text-muted-foreground mt-0.5">
                                {doc.size} | {doc.date}
                              </p>
                            </div>
                          </div>
                        ) : (
                          <svg className="w-40 h-28 text-slate-100" viewBox="0 0 160 110" fill="none" xmlns="http://www.w3.org/2000/svg">
                            {/* Outer Card */}
                            <rect x="8" y="8" width="144" height="94" rx="8" fill="#f8fafc" stroke="#e2e8f0" strokeWidth="2" />
                            {/* Avatar Silhouette */}
                            <circle cx="40" cy="36" r="12" fill="#cbd5e1" />
                            <path d="M22 60 C 22 48, 58 48, 58 60 Z" fill="#cbd5e1" />
                            {/* Horizontal Fields */}
                            <rect x="74" y="28" width="56" height="5" rx="2.5" fill="#cbd5e1" />
                            <rect x="74" y="40" width="40" height="5" rx="2.5" fill="#cbd5e1" />
                            {/* Bottom Horizontal Line */}
                            <rect x="22" y="72" width="116" height="3" rx="1.5" fill="#cbd5e1" />
                            {/* "NO DATA" Overlay Text */}
                            <text
                              x="80"
                              y="58"
                              fill="#93c5fd"
                              fontSize="15"
                              fontWeight="800"
                              textAnchor="middle"
                              letterSpacing="0.05em"
                              fontFamily="sans-serif"
                            >
                              NO DATA
                            </text>
                          </svg>
                        )}
                      </div>

                      {/* Bottom Half: Footer */}
                      <div className="p-3.5 bg-card flex items-center justify-between gap-2 border-t border-border/10">
                        <span className="text-xs font-semibold text-slate-800 dark:text-slate-200">
                          {docName}
                        </span>

                        <div className="flex items-center gap-1.5">
                          {doc ? (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => toast.success(`Downloading ${doc.fileName}...`)}
                                className="h-7 text-[10px] px-2.5 cursor-pointer font-semibold border-slate-200 hover:bg-slate-50 text-slate-700"
                              >
                                Download
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleFileRemove(docName)}
                                className="h-7 text-[10px] px-2.5 cursor-pointer font-semibold text-destructive hover:bg-red-500/10 border-destructive/20"
                              >
                                Remove
                              </Button>
                            </>
                          ) : (
                            <button
                              onClick={() => triggerFileInput(docName)}
                              className="px-3.5 py-1.5 text-xs font-semibold text-white bg-[#0284c7] hover:bg-[#0284c7]/90 rounded-lg transition-colors cursor-pointer shadow-2xs"
                            >
                              Upload
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PUNCH IN BRANCH MODAL */}
      {isPunchBranchOpen && targetEmployee && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-lg w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <div>
                <h3 className="text-sm font-bold text-foreground">Punch In Branch Mapping</h3>
                <p className="text-[10px] text-muted-foreground">{targetEmployee.name} | ID: {targetEmployee.employee_id}</p>
              </div>
              <button
                onClick={() => {
                  setIsPunchBranchOpen(false);
                  setTargetEmployee(null);
                }}
                className="p-1 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted-foreground">
                Define which physical branch locations {targetEmployee.name} is authorized to register biometric punches from.
              </p>
              <div className="space-y-2.5">
                <Checkbox label="Itcode Infotech (HQ) - Surat" defaultChecked />
                <Checkbox label="Itcode Infotech - Ahmedabad branch" />
                <Checkbox label="Remote Location Allowance" defaultChecked />
              </div>
            </div>
            <div className="p-4 bg-muted/30 border-t border-border flex items-center justify-end gap-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsPunchBranchOpen(false);
                  setTargetEmployee(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsPunchBranchOpen(false);
                  setTargetEmployee(null);
                  toast.success("Punch mappings updated successfully.");
                }}
              >
                Save Mappings
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ─── IMPORT EMPLOYEES MODAL ─── */}
      {isImportModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-blue-500/10 flex items-center justify-center">
                  <Upload className="h-4.5 w-4.5 text-blue-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">Import Employees</h3>
                  <p className="text-[10px] text-muted-foreground">Upload a CSV or Excel file to import employees</p>
                </div>
              </div>
              <button
                onClick={() => { setIsImportModalOpen(false); setImportFile(null); }}
                className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {/* Body */}
            <div className="p-5 space-y-4">
              {/* Instructions */}
              <div className="bg-blue-500/5 border border-blue-500/20 rounded-lg p-3.5 space-y-2">
                <p className="text-xs font-semibold text-blue-600 dark:text-blue-400">Before you upload:</p>
                <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Use the <span className="font-medium text-foreground">Download Sample</span> option to get the correct format.</li>
                  <li>File must be <span className="font-medium text-foreground">.csv</span> or <span className="font-medium text-foreground">.xlsx</span>.</li>
                  <li>Maximum <span className="font-medium text-foreground">500 rows</span> per import.</li>
                  <li>All required columns must be filled.</li>
                </ul>
              </div>
              {/* Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
                  importFile
                    ? "border-blue-400 bg-blue-500/5"
                    : "border-border hover:border-blue-400/50 hover:bg-muted/30"
                }`}
                onClick={() => importFileRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files[0];
                  if (file) setImportFile(file);
                }}
              >
                <input
                  ref={importFileRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setImportFile(file);
                  }}
                />
                {importFile ? (
                  <div className="space-y-1">
                    <FileText className="h-8 w-8 text-blue-500 mx-auto" />
                    <p className="text-sm font-medium text-foreground">{importFile.name}</p>
                    <p className="text-xs text-muted-foreground">{(importFile.size / 1024).toFixed(1)} KB</p>
                    <button
                      className="text-xs text-red-500 hover:underline"
                      onClick={(e) => { e.stopPropagation(); setImportFile(null); if (importFileRef.current) importFileRef.current.value = ""; }}
                    >
                      Remove file
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <Upload className="h-8 w-8 text-muted-foreground mx-auto" />
                    <p className="text-sm font-medium text-foreground">Drop your file here, or <span className="text-blue-500">browse</span></p>
                    <p className="text-xs text-muted-foreground">Supports: .csv, .xlsx, .xls</p>
                  </div>
                )}
              </div>
            </div>
            {/* Footer */}
            <div className="p-4 bg-muted/20 border-t border-border flex items-center justify-between gap-3">
              <Button variant="outline" size="sm" onClick={() => { setIsImportModalOpen(false); setImportFile(null); }}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!importFile || isUploading}
                onClick={async () => {
                  if (!importFile) return;
                  setIsUploading(true);
                  try {
                    await handleImportCSV(importFile);
                  } catch (err: unknown) {
                    const message = err instanceof Error ? err.message : "Import failed.";
                    toast.error(`Import failed: ${message}`);
                  } finally {
                    setIsUploading(false);
                    setIsImportModalOpen(false);
                    setImportFile(null);
                  }
                }}
              >
                {isUploading ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />Importing...</>
                ) : (
                  <><Upload className="h-3.5 w-3.5 mr-1.5" />Import Now</>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ─── BULK UPDATE EMPLOYEES MODAL ─── */}
      {isBulkUpdateModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-lg overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-purple-500/10 flex items-center justify-center">
                  <FileDown className="h-4.5 w-4.5 text-purple-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">Bulk Update Employees</h3>
                  <p className="text-[10px] text-muted-foreground">Upload a file to update multiple employee records at once</p>
                </div>
              </div>
              <button
                onClick={() => { setIsBulkUpdateModalOpen(false); setBulkUpdateFile(null); }}
                className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {/* Body */}
            <div className="p-5 space-y-4">
              <div className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3.5 space-y-2">
                <p className="text-xs font-semibold text-purple-600 dark:text-purple-400">How to bulk update:</p>
                <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
                  <li>Export existing employees using <span className="font-medium text-foreground">Export Excel</span>.</li>
                  <li>Edit the fields you want to update in the downloaded file.</li>
                  <li>Re-upload the modified file here.</li>
                  <li><span className="font-medium text-foreground">employee_code</span> column is required and must not be changed.</li>
                </ul>
              </div>
              {/* Drop Zone */}
              <div
                className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer ${
                  bulkUpdateFile
                    ? "border-purple-400 bg-purple-500/5"
                    : "border-border hover:border-purple-400/50 hover:bg-muted/30"
                }`}
                onClick={() => bulkUpdateFileRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault();
                  const file = e.dataTransfer.files[0];
                  if (file) setBulkUpdateFile(file);
                }}
              >
                <input
                  ref={bulkUpdateFileRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) setBulkUpdateFile(file);
                  }}
                />
                {bulkUpdateFile ? (
                  <div className="space-y-1">
                    <FileText className="h-8 w-8 text-purple-500 mx-auto" />
                    <p className="text-sm font-medium text-foreground">{bulkUpdateFile.name}</p>
                    <p className="text-xs text-muted-foreground">{(bulkUpdateFile.size / 1024).toFixed(1)} KB</p>
                    <button
                      className="text-xs text-red-500 hover:underline"
                      onClick={(e) => { e.stopPropagation(); setBulkUpdateFile(null); if (bulkUpdateFileRef.current) bulkUpdateFileRef.current.value = ""; }}
                    >
                      Remove file
                    </button>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <FileDown className="h-8 w-8 text-muted-foreground mx-auto" />
                    <p className="text-sm font-medium text-foreground">Drop your updated file here, or <span className="text-purple-500">browse</span></p>
                    <p className="text-xs text-muted-foreground">Supports: .csv, .xlsx, .xls</p>
                  </div>
                )}
              </div>
            </div>
            {/* Footer */}
            <div className="p-4 bg-muted/20 border-t border-border flex items-center justify-between gap-3">
              <Button variant="outline" size="sm" onClick={() => { setIsBulkUpdateModalOpen(false); setBulkUpdateFile(null); }}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={!bulkUpdateFile || isUploading}
                onClick={async () => {
                  if (!bulkUpdateFile) return;
                  setIsUploading(true);
                  try {
                    await handleBulkUpdateCSV(bulkUpdateFile);
                  } catch (err: unknown) {
                    const message = err instanceof Error ? err.message : "Bulk update failed.";
                    toast.error(`Bulk update failed: ${message}`);
                  } finally {
                    setIsUploading(false);
                    setIsBulkUpdateModalOpen(false);
                    setBulkUpdateFile(null);
                  }
                }}
              >
                {isUploading ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />Updating...</>
                ) : (
                  <><FileDown className="h-3.5 w-3.5 mr-1.5" />Apply Updates</>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ─── VIEW DOWNLOADS MODAL ─── */}
      {isDownloadsModalOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-[100] animate-in fade-in duration-200">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="p-5 border-b border-border flex items-center justify-between bg-muted/20">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-lg bg-amber-500/10 flex items-center justify-center">
                  <FolderOpen className="h-4.5 w-4.5 text-amber-500" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">View Downloads</h3>
                  <p className="text-[10px] text-muted-foreground">Recent export history for this session</p>
                </div>
              </div>
              <button
                onClick={() => setIsDownloadsModalOpen(false)}
                className="p-1.5 hover:bg-muted rounded-md text-muted-foreground hover:text-foreground cursor-pointer focus:outline-none"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            {/* Body */}
            <div className="p-5 space-y-4">
              {/* How to export */}
              <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <Download className="h-4 w-4 text-amber-500" />
                  <p className="text-xs font-semibold text-amber-600 dark:text-amber-400">How to export employees</p>
                </div>
                <ol className="text-xs text-muted-foreground space-y-1.5 list-decimal list-inside">
                  <li>Click <span className="font-medium text-foreground">Actions → Export Excel</span> in the toolbar above.</li>
                  <li>The system generates your employee data as an <span className="font-medium text-foreground">.xlsx</span> file.</li>
                  <li>The file downloads automatically to your browser&apos;s default download folder.</li>
                  <li>For very large datasets (&gt;1,000 employees), the export runs as a background job and the file becomes available within a few minutes.</li>
                </ol>
              </div>

              {/* Session note */}
              <div className="flex items-start gap-3 bg-muted/30 rounded-lg p-3.5">
                <AlertTriangle className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Completed downloads appear directly in your browser. A dedicated download history panel with persistent job tracking is coming in a future release.
                </p>
              </div>
            </div>
            {/* Footer */}
            <div className="p-4 bg-muted/20 border-t border-border flex items-center justify-end gap-3">
              <Button variant="outline" size="sm" onClick={() => setIsDownloadsModalOpen(false)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setIsDownloadsModalOpen(false);
                  handleExportExcel();
                }}
                disabled={isExporting}
              >
                {isExporting ? (
                  <><Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" />Exporting...</>
                ) : (
                  <><Download className="h-3.5 w-3.5 mr-1.5" />Export Now</>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
