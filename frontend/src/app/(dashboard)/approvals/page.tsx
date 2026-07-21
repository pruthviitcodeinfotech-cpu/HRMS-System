"use client";

import { useState, useMemo } from "react";
import { toast } from "sonner";
import { ProtectedRoute } from "@/features/auth";
import {
  ApprovalRequest,
  ApprovalStatus,
  INITIAL_APPROVAL_REQUESTS,
  ApprovalStatusTabs,
  ApprovalFilters,
  ApprovalRequestTable,
  ApprovalRequestDrawer,
  ApprovalRemarksDialog,
} from "@/features/approvals";

const STORAGE_KEY = "hrms_approval_requests";

const getSavedRequests = (): ApprovalRequest[] => {
  if (typeof window === "undefined") return INITIAL_APPROVAL_REQUESTS;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : INITIAL_APPROVAL_REQUESTS;
  } catch {
    return INITIAL_APPROVAL_REQUESTS;
  }
};

const saveRequests = (data: ApprovalRequest[]) => {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.error("Failed to save approval requests", err);
  }
};

export default function ApprovalsPage() {
  const [requests, setRequests] = useState<ApprovalRequest[]>(() => getSavedRequests());
  const [activeTab, setActiveTab] = useState<ApprovalStatus>("pending");
  const [typeFilter, setTypeFilter] = useState<string>("Choose One");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Drawer state
  const [selectedDrawerRequest, setSelectedDrawerRequest] = useState<ApprovalRequest | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Remarks dialog state
  const [selectedRemarksRequest, setSelectedRemarksRequest] = useState<ApprovalRequest | null>(
    null
  );
  const [remarksAction, setRemarksAction] = useState<"approve" | "reject">("approve");
  const [isRemarksOpen, setIsRemarksOpen] = useState<boolean>(false);

  // Compute status counts dynamically
  const counts = useMemo(() => {
    return {
      pending: requests.filter((r) => r.status === "pending").length,
      approved: requests.filter((r) => r.status === "approved").length,
      rejected: requests.filter((r) => r.status === "rejected").length,
    };
  }, [requests]);

  // Filter requests based on active tab, type filter, and search query
  const filteredRequests = useMemo(() => {
    return requests.filter((req) => {
      if (req.status !== activeTab) return false;

      if (typeFilter !== "Choose One" && req.type !== typeFilter) {
        return false;
      }

      if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase().trim();
        const empNameMatch = req.employeeName.toLowerCase().includes(query);
        const empCodeMatch = req.employeeCode.toLowerCase().includes(query);
        const typeMatch = req.type.toLowerCase().includes(query);
        if (!empNameMatch && !empCodeMatch && !typeMatch) return false;
      }

      return true;
    });
  }, [requests, activeTab, typeFilter, searchQuery]);

  const handleFilterChange = (type: string, query: string) => {
    setTypeFilter(type);
    setSearchQuery(query);
  };

  const handleClearFilters = () => {
    setTypeFilter("Choose One");
    setSearchQuery("");
  };

  // Open View Details Drawer
  const handleViewDetails = (req: ApprovalRequest) => {
    setSelectedDrawerRequest(req);
    setIsDrawerOpen(true);
  };

  // Open Remarks Dialog for Approve
  const handleOpenApprove = (req: ApprovalRequest) => {
    setSelectedRemarksRequest(req);
    setRemarksAction("approve");
    setIsRemarksOpen(true);
  };

  // Open Remarks Dialog for Reject
  const handleOpenReject = (req: ApprovalRequest) => {
    setSelectedRemarksRequest(req);
    setRemarksAction("reject");
    setIsRemarksOpen(true);
  };

  // Execute Approval or Rejection
  const handleSubmitRemarks = (remarks: string) => {
    if (!selectedRemarksRequest) return;

    const isApprove = remarksAction === "approve";
    const now = new Date();
    const formattedDate = `${now.toLocaleDateString("en-GB")} ${now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    })}`;

    const updatedRequests = requests.map((req) => {
      if (req.id === selectedRemarksRequest.id) {
        return {
          ...req,
          status: (isApprove ? "approved" : "rejected") as ApprovalStatus,
          approvedBy: isApprove ? "Balkrushn koladiya" : undefined,
          rejectedBy: !isApprove ? "Balkrushn koladiya" : undefined,
          actionDate: formattedDate,
          remarks: remarks || (isApprove ? "Approved" : "Rejected"),
        };
      }
      return req;
    });

    setRequests(updatedRequests);
    saveRequests(updatedRequests);

    if (isApprove) {
      toast.success(
        `Approval Request for ${selectedRemarksRequest.employeeName} (${selectedRemarksRequest.type}) approved successfully.`
      );
    } else {
      toast.error(
        `Approval Request for ${selectedRemarksRequest.employeeName} (${selectedRemarksRequest.type}) has been rejected.`
      );
    }

    setIsRemarksOpen(false);
    setSelectedRemarksRequest(null);
  };

  return (
    <ProtectedRoute requiredPermission={{ feature: "approvals", action: "read" }}>
      <div className="space-y-6 p-6 w-full">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
          <div>
            <h1 className="text-xl font-bold text-slate-800 dark:text-slate-100">
              Approval Requests
            </h1>
          </div>
        </div>

        {/* Main Card Container */}
        <div className="bg-white dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 shadow-2xs overflow-hidden">
          {/* Status Tabs */}
          <ApprovalStatusTabs
            activeTab={activeTab}
            counts={counts}
            onTabChange={setActiveTab}
          />

          {/* Filters Bar */}
          <ApprovalFilters
            typeFilter={typeFilter}
            searchQuery={searchQuery}
            onFilterChange={handleFilterChange}
            onClear={handleClearFilters}
          />

          {/* Requests Table */}
          <ApprovalRequestTable
            requests={filteredRequests}
            onViewDetails={handleViewDetails}
            onApprove={handleOpenApprove}
            onReject={handleOpenReject}
          />
        </div>

        {/* Drawer for View Details */}
        <ApprovalRequestDrawer
          isOpen={isDrawerOpen}
          onClose={() => setIsDrawerOpen(false)}
          request={selectedDrawerRequest}
          onApprove={handleOpenApprove}
          onReject={handleOpenReject}
        />

        {/* Remarks Dialog for Approve / Reject */}
        <ApprovalRemarksDialog
          isOpen={isRemarksOpen}
          onClose={() => setIsRemarksOpen(false)}
          request={selectedRemarksRequest}
          actionType={remarksAction}
          onSubmit={handleSubmitRemarks}
        />
      </div>
    </ProtectedRoute>
  );
}
