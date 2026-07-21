import {
  ApprovalRequest,
  ApprovalRequestSchema,
  ApprovalRequestType,
  ApprovalStatus,
} from "./types";
import { EmployeeSummary } from "@/features/employees";

/** Maps backend request_type enum to UI ApprovalRequestType */
export const mapBackendTypeToUi = (
  type: "attendance" | "leave" | "login_reset",
  subtype?: string | null
): ApprovalRequestType => {
  const subLower = (subtype || "").toLowerCase();
  if (subLower.includes("overtime")) return "Overtime";
  if (subLower.includes("comp")) return "Comp Off";
  if (type === "leave") return "Leave";
  if (type === "login_reset") return "Short Leave";
  return "Attendance";
};

/** Formats ISO timestamp string into human-readable table date/time */
export const formatApprovalTimestamp = (isoString?: string | null): string => {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const pad = (n: number) => String(n).padStart(2, "0");
    const day = pad(d.getDate());
    const month = pad(d.getMonth() + 1);
    const year = d.getFullYear();
    let hours = d.getHours();
    const minutes = pad(d.getMinutes());
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${day}-${month}-${year} ${pad(hours)}:${minutes} ${ampm}`;
  } catch {
    return isoString;
  }
};

/** Formats ISO date into table date string (e.g. "20-07-2026") */
export const formatApprovalDate = (isoString?: string | null): string => {
  if (!isoString) return "-";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const pad = (n: number) => String(n).padStart(2, "0");
    const day = pad(d.getDate());
    const month = pad(d.getMonth() + 1);
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  } catch {
    return isoString;
  }
};

/** Adapter to convert backend ApprovalRequestSchema into UI ApprovalRequest */
export const mapSchemaToApprovalRequest = (
  schema: ApprovalRequestSchema,
  employeeMap?: Record<number, EmployeeSummary>
): ApprovalRequest => {
  const emp = employeeMap?.[schema.employee_id];
  const uiType = mapBackendTypeToUi(schema.request_type, schema.request_subtype);

  const empCode =
    emp?.employee_code ||
    schema.employee_code ||
    `EMP${String(schema.employee_id).padStart(4, "0")}`;

  const empName =
    emp?.employee_name ||
    emp?.display_name ||
    schema.employee_name ||
    `Employee #${schema.employee_id}`;

  const designation = emp?.designation_name || schema.designation_name || "Staff";
  const department = emp?.department_name || schema.department_name || "General";

  return {
    id: String(schema.id),
    numericId: schema.id,
    type: uiType,
    subtype: schema.request_subtype || (uiType === "Leave" ? "LWP" : "New Punch Added"),
    employeeCode: empCode,
    employeeName: empName,
    designation,
    department,
    details: {
      date: formatApprovalDate(schema.requested_at),
      fromDate: formatApprovalDate(schema.requested_at),
      toDate: formatApprovalDate(schema.requested_at),
      reason: schema.reject_remarks || undefined,
    },
    submittedDate: formatApprovalTimestamp(schema.requested_at),
    status: schema.status as ApprovalStatus,
    pendingApprover: schema.status === "pending" ? "HR Manager" : undefined,
    approvedBy:
      schema.status === "approved"
        ? schema.reviewed_by
          ? `Reviewer #${schema.reviewed_by}`
          : "Manager"
        : undefined,
    rejectedBy:
      schema.status === "rejected"
        ? schema.reviewed_by
          ? `Reviewer #${schema.reviewed_by}`
          : "Manager"
        : undefined,
    actionDate: formatApprovalTimestamp(schema.reviewed_at),
    remarks: schema.reject_remarks || undefined,
  };
};
