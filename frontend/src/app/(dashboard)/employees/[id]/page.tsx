"use client";

import { use } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/features/auth";
import { useEmployee } from "@/features/employees/hooks";
import { Skeleton } from "@/components/feedback/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  User,
  Building2,
  Calendar,
  Phone,
  Mail,
  CreditCard,
  FileText,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";

interface EmployeeDetailPageProps {
  params: Promise<{ id: string }>;
}

export default function EmployeeDetailPage({ params }: EmployeeDetailPageProps) {
  const resolvedParams = use(params);
  const employeeId = parseInt(resolvedParams.id, 10);
  const { data: employee, isLoading, isError, error } = useEmployee(employeeId, !isNaN(employeeId));

  return (
    <ProtectedRoute requiredPermission={{ feature: "employee", action: "read" }}>
      <div className="p-6 space-y-6 max-w-6xl mx-auto">
        {/* Top Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link href="/employees">
              <Button variant="outline" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back to Employees
              </Button>
            </Link>
            <h1 className="text-2xl font-bold text-slate-800 dark:text-slate-100">
              Employee Profile
            </h1>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="space-y-6">
            <div className="bg-card p-6 rounded-xl border border-border space-y-4">
              <Skeleton className="h-16 w-16 rounded-full" />
              <Skeleton className="h-6 w-1/3" />
              <Skeleton className="h-4 w-1/4" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Skeleton className="h-48 w-full rounded-xl" />
              <Skeleton className="h-48 w-full rounded-xl" />
            </div>
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl p-6 text-center space-y-3">
            <AlertTriangle className="h-8 w-8 text-rose-500 mx-auto" />
            <h3 className="text-base font-semibold text-rose-800 dark:text-rose-200">
              Failed to load employee profile
            </h3>
            <p className="text-xs text-rose-600 dark:text-rose-400">
              {error instanceof Error ? error.message : "Employee record not found or network error."}
            </p>
          </div>
        )}

        {/* Empty / Not Found State */}
        {!isLoading && !isError && !employee && (
          <EmptyState
            title="Employee Not Found"
            description="The requested employee record could not be found."
          />
        )}

        {/* Profile Content */}
        {!isLoading && !isError && employee && (
          <div className="space-y-6">
            {/* Header Card */}
            <div className="bg-card rounded-xl border border-border p-6 shadow-xs flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div className="h-16 w-16 rounded-full bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-xl border border-blue-200 dark:border-blue-800">
                  {employee.employee_name.charAt(0).toUpperCase()}
                </div>
                <div className="space-y-1">
                  <div className="flex items-center space-x-3">
                    <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">
                      {employee.employee_name}
                    </h2>
                    <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                      {employee.employee_code}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {employee.designation_name || employee.designation?.designation_name || "Employee"} •{" "}
                    {employee.department_name || employee.department?.dept_name || "Department"}
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-semibold rounded-full ${
                    employee.employment_status === "active"
                      ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                  }`}
                >
                  {employee.employment_status === "active" ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5" />
                  )}
                  <span className="capitalize">{employee.employment_status}</span>
                </span>
              </div>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Primary Info */}
              <div className="bg-card rounded-xl border border-border p-6 space-y-4 shadow-xs">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2 border-b border-border pb-2">
                  <User className="h-4 w-4 text-blue-600" />
                  Personal & Contact Information
                </h3>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Display Name</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.display_name || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Gender</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.gender || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Mobile Number</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5 flex items-center gap-1">
                      <Phone className="h-3 w-3 text-slate-400" />
                      {employee.mobile_country_code} {employee.mobile_number}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Email Address</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5 flex items-center gap-1 truncate">
                      <Mail className="h-3 w-3 text-slate-400 shrink-0" />
                      {employee.email || "-"}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-slate-400 font-medium">Address</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.address || "-"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Organization & Employment */}
              <div className="bg-card rounded-xl border border-border p-6 space-y-4 shadow-xs">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2 border-b border-border pb-2">
                  <Building2 className="h-4 w-4 text-blue-600" />
                  Organization Details
                </h3>
                <div className="grid grid-cols-2 gap-4 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">Master Branch</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.branch_name || employee.branch?.branch_name || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Department</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.department_name || employee.department?.dept_name || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Designation</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.designation_name || employee.designation?.designation_name || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Employee Type</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.employee_type || "Full Time"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Date of Joining</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5 flex items-center gap-1">
                      <Calendar className="h-3 w-3 text-slate-400" />
                      {employee.date_of_joining ? String(employee.date_of_joining) : "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">Door Lock Access</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.door_lock_permission ? "Granted" : "Not Granted"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Statutory Information */}
              <div className="bg-card rounded-xl border border-border p-6 space-y-4 shadow-xs">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2 border-b border-border pb-2">
                  <CreditCard className="h-4 w-4 text-blue-600" />
                  Statutory & Payroll Identifiers
                </h3>
                <div className="grid grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="text-slate-400 font-medium">PF Number</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.pf_account_number || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">UAN Number</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.uan_number || "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-400 font-medium">ESIC IP Number</span>
                    <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5">
                      {employee.esic_ip_number || "-"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Salary Section (Gated) */}
              <div className="bg-card rounded-xl border border-border p-6 space-y-4 shadow-xs">
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2 border-b border-border pb-2">
                  <FileText className="h-4 w-4 text-blue-600" />
                  Salary Information
                </h3>
                {employee.salary ? (
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-slate-400 font-medium">Salary Type</span>
                      <p className="font-semibold text-slate-700 dark:text-slate-300 mt-0.5 capitalize">
                        {employee.salary.salary_type || "Monthly"}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-400 font-medium">Monthly Amount</span>
                      <p className="font-semibold text-emerald-600 dark:text-emerald-400 mt-0.5">
                        {employee.salary.monthly_salary !== null && employee.salary.monthly_salary !== undefined
                          ? `₹${Number(employee.salary.monthly_salary).toLocaleString("en-IN")}`
                          : "-"}
                      </p>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400 italic">
                    Salary details are restricted or not configured for this user role.
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </ProtectedRoute>
  );
}
