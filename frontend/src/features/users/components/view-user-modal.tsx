"use client";

import { useEffect } from "react";
import { X, User, Mail, Phone, ShieldCheck, Calendar, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useUserDetail } from "../hooks/use-users";

interface ViewUserModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId?: number | null;
}

export function ViewUserModal({ isOpen, onClose, userId }: ViewUserModalProps) {
  // Live user detail fetching via GET /api/v1/users/{id}
  const { data: userDetail, isLoading, isError } = useUserDetail(userId || undefined);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !userId) return null;

  const name = userDetail?.name || "User";
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .filter(Boolean)
    .join("")
    .substring(0, 2)
    .toUpperCase();

  const isActive = userDetail?.is_active ?? true;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="view-user-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <h2 id="view-user-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
            User Details
          </h2>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 overflow-y-auto text-xs min-h-[300px]">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 space-y-3">
              <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
              <p className="text-xs text-slate-500 font-medium">Loading user profile...</p>
            </div>
          ) : isError ? (
            <div className="text-center py-12 space-y-2 text-red-600 dark:text-red-400">
              <p className="font-bold">Failed to load user details.</p>
              <p className="text-xs text-slate-500">Please try again later.</p>
            </div>
          ) : (
            <>
              {/* Avatar Header Row */}
              <div className="flex items-center space-x-4 bg-slate-50 dark:bg-slate-800/60 p-4 rounded-xl border border-slate-100 dark:border-slate-800">
                <div className="h-14 w-14 rounded-full bg-blue-600 text-white font-extrabold text-lg flex items-center justify-center shadow-md shrink-0">
                  {initials || "US"}
                </div>

                <div>
                  <h3 className="text-base font-bold text-slate-800 dark:text-slate-100">
                    {userDetail?.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-medium">
                    {userDetail?.employee_id
                      ? `Employee ID: ${userDetail.employee_id}`
                      : "User Account"}
                  </p>
                  <div className="flex items-center space-x-2 mt-1.5">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        isActive
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                      }`}
                    >
                      {isActive ? (
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                      ) : (
                        <XCircle className="h-3 w-3 mr-1" />
                      )}
                      {isActive ? "Active" : "Inactive"}
                    </span>

                    {userDetail?.is_super_admin && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300">
                        Super Admin
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* User Property Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {/* Email */}
                <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <Mail className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold text-slate-500">Email Address</span>
                  </div>
                  <p className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                    {userDetail?.email || "-"}
                  </p>
                </div>

                {/* Mobile Number */}
                <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <Phone className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold text-slate-500">Phone Number</span>
                  </div>
                  <p className="font-semibold text-slate-800 dark:text-slate-200">
                    {userDetail?.mobile_country_code
                      ? `${userDetail.mobile_country_code} ${userDetail.mobile_number}`
                      : userDetail?.mobile_number || "-"}
                  </p>
                </div>

                {/* Rights Template */}
                <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold text-slate-500">Rights Template</span>
                  </div>
                  <p className="font-bold text-blue-600 dark:text-blue-400">
                    {userDetail?.template ? userDetail.template.name : "-"}
                  </p>
                </div>

                {/* Employee ID */}
                <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <User className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold text-slate-500">Linked Employee</span>
                  </div>
                  <p className="font-semibold text-slate-800 dark:text-slate-200">
                    {userDetail?.employee_id ? `#${userDetail.employee_id}` : "Unlinked"}
                  </p>
                </div>
              </div>

              {/* Audit Timestamps */}
              <div className="grid grid-cols-2 gap-4 p-3 bg-slate-50/50 dark:bg-slate-800/40 rounded-lg border border-slate-100 dark:border-slate-800">
                <div>
                  <span className="block text-[10px] text-slate-400 font-semibold">Created Date</span>
                  <div className="flex items-center space-x-1 text-slate-600 dark:text-slate-300 font-medium mt-0.5">
                    <Calendar className="h-3 w-3 text-slate-400" />
                    <span>{userDetail?.created_at?.substring(0, 10) || "-"}</span>
                  </div>
                </div>

                <div>
                  <span className="block text-[10px] text-slate-400 font-semibold">Last Updated</span>
                  <div className="flex items-center space-x-1 text-slate-600 dark:text-slate-300 font-medium mt-0.5">
                    <Calendar className="h-3 w-3 text-slate-400" />
                    <span>{userDetail?.updated_at?.substring(0, 10) || "-"}</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-6 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <Button
            type="button"
            onClick={onClose}
            className="bg-slate-800 text-white hover:bg-slate-900 text-xs font-semibold h-8 px-4 cursor-pointer"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
