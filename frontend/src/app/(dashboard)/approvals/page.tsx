"use client";

import { useState, useMemo } from "react";
import { toast } from "sonner";
import { ProtectedRoute } from "@/features/auth";
import { useEmployees, EmployeeSummary } from "@/features/employees";
import {
  ApprovalRequest,
  ApprovalStatus,
  ApprovalStatusTabs,
  ApprovalFilters,
  ApprovalRequestTable,
  ApprovalRequestDrawer,
  ApprovalRemarksDialog,
  useApprovalsList,
  usePendingApprovalCount,
  useApproveRequest,
  useRejectRequest,
  useBulkApproveRequests,
  useBulkRejectRequests,
  mapSchemaToApprovalRequest,
  BackendRequestType,
} from "@/features/approvals";

export default function ApprovalsPage() {
  // Page controls state
  const [activeTab, setActiveTab] = useState<ApprovalStatus>("pending");
  const [typeFilter, setTypeFilter] = useState<string>("Choose One");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Drawer state
  const [selectedDrawerRequest, setSelectedDrawerRequest] = useState<ApprovalRequest | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);

  // Remarks dialog state
  const [selectedRemarksRequest, setSelectedRemarksRequest] = useState<ApprovalRequest | null>(
    null
  );
  const [remarksAction, setRemarksAction] = useState<"approve" | "reject">("approve");
  const [isRemarksOpen, setIsRemarksOpen] = useState<boolean>(false);

  // Fetch employees lookup map from Employee feature
  const { data: employeesData } = useEmployees({ page: 1, page_size: 200 });

  const employeeMap = useMemo(() => {
    const map: Record<number, EmployeeSummary> = {};
    if (employeesData?.items) {
      employeesData.items.forEach((emp) => {
        map[emp.employee_id] = emp;
      });
    }
    return map;
  }, [employeesData]);

  // Convert UI type filter to backend request_type
  const backendRequestType = useMemo<BackendRequestType | undefined>(() => {
    if (typeFilter === "Leave" || typeFilter === "Comp Off") return "leave";
    if (typeFilter === "Attendance" || typeFilter === "Overtime") return "attendance";
    if (typeFilter === "Short Leave") return "login_reset";
    return undefined;
  }, [typeFilter]);

  // Fetch approval list from live backend API for active tab table
  const {
    data: approvalsData,
    isLoading: isApprovalsLoading,
    refetch,
  } = useApprovalsList({
    status: activeTab,
    request_type: backendRequestType,
    page: currentPage,
    page_size: pageSize,
  });

  // Fetch count totals for all 3 tabs so badges always show accurate backend totals
  const { data: pendingApprovalsCountData } = useApprovalsList({
    status: "pending",
    request_type: backendRequestType,
    page: 1,
    page_size: 1,
  });

  const { data: approvedApprovalsCountData } = useApprovalsList({
    status: "approved",
    request_type: backendRequestType,
    page: 1,
    page_size: 1,
  });

  const { data: rejectedApprovalsCountData } = useApprovalsList({
    status: "rejected",
    request_type: backendRequestType,
    page: 1,
    page_size: 1,
  });

  // Fetch pending count summary from live backend API
  const { data: pendingCountData } = usePendingApprovalCount();

  // React Query Mutations with automatic cache invalidation
  const approveMutation = useApproveRequest();
  const rejectMutation = useRejectRequest();
  const bulkApproveMutation = useBulkApproveRequests();
  const bulkRejectMutation = useBulkRejectRequests();

  // Dynamic counts for tab header badges
  const counts = useMemo(() => {
    const pCount =
      activeTab === "pending"
        ? (approvalsData?.pagination.total_records ?? pendingApprovalsCountData?.pagination.total_records ?? pendingCountData?.pending_count ?? 0)
        : (pendingApprovalsCountData?.pagination.total_records ?? pendingCountData?.pending_count ?? 0);

    const aCount =
      activeTab === "approved"
        ? (approvalsData?.pagination.total_records ?? approvedApprovalsCountData?.pagination.total_records ?? 0)
        : (approvedApprovalsCountData?.pagination.total_records ?? 0);

    const rCount =
      activeTab === "rejected"
        ? (approvalsData?.pagination.total_records ?? rejectedApprovalsCountData?.pagination.total_records ?? 0)
        : (rejectedApprovalsCountData?.pagination.total_records ?? 0);

    return {
      pending: pCount,
      approved: aCount,
      rejected: rCount,
    };
  }, [
    activeTab,
    approvalsData,
    pendingCountData,
    pendingApprovalsCountData,
    approvedApprovalsCountData,
    rejectedApprovalsCountData,
  ]);

  // Map backend items to UI ApprovalRequest format
  const mappedRequests = useMemo(() => {
    if (!approvalsData?.items) return [];
    return approvalsData.items.map((schema) =>
      mapSchemaToApprovalRequest(schema, employeeMap)
    );
  }, [approvalsData, employeeMap]);

  // Client-side search and type filtering over server response
  const filteredRequests = useMemo(() => {
    let list = mappedRequests;

    if (typeFilter && typeFilter !== "Choose One") {
      list = list.filter((req) => {
        return (
          req.type.toLowerCase() === typeFilter.toLowerCase() ||
          req.subtype.toLowerCase().includes(typeFilter.toLowerCase())
        );
      });
    }

    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase().trim();
    return list.filter((req) => {
      return (
        req.employeeName.toLowerCase().includes(q) ||
        req.employeeCode.toLowerCase().includes(q) ||
        req.type.toLowerCase().includes(q) ||
        req.subtype.toLowerCase().includes(q)
      );
    });
  }, [mappedRequests, typeFilter, searchQuery]);

  const handleFilterChange = (type: string, query: string) => {
    setTypeFilter(type);
    setSearchQuery(query);
    setCurrentPage(1);
  };

  const handleClearFilters = () => {
    setTypeFilter("Choose One");
    setSearchQuery("");
    setCurrentPage(1);
  };

  const handleTabChange = (tab: ApprovalStatus) => {
    setActiveTab(tab);
    setCurrentPage(1);
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

  // Single Approve / Reject API submission
  const handleSubmitRemarks = async (remarks: string) => {
    if (!selectedRemarksRequest) return;

    const numericId = selectedRemarksRequest.numericId;
    const isApprove = remarksAction === "approve";

    try {
      if (isApprove) {
        await approveMutation.mutateAsync({
          id: numericId,
          payload: { remarks: remarks || undefined },
        });
        toast.success(
          `Request for ${selectedRemarksRequest.employeeName} approved successfully.`
        );
      } else {
        await rejectMutation.mutateAsync({
          id: numericId,
          payload: { reject_remarks: remarks || "Rejected by administrator." },
        });
        toast.success(
          `Request for ${selectedRemarksRequest.employeeName} rejected successfully.`
        );
      }
      refetch();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Action failed";
      toast.error(msg);
    }

    setIsRemarksOpen(false);
    setSelectedRemarksRequest(null);
  };

  // Bulk Approve API mutation handler
  const handleBulkApprove = async (selectedIds: string[]) => {
    const numericIds = selectedIds
      .map((id) => parseInt(id, 10))
      .filter((id) => !isNaN(id));

    if (numericIds.length === 0) return;

    try {
      const res = await bulkApproveMutation.mutateAsync({
        approval_ids: numericIds,
        remarks: "Approved via bulk action",
      });

      const successCount = res.results.filter((r) => r.success).length;
      const failCount = res.results.filter((r) => !r.success).length;

      if (successCount > 0) {
        toast.success(`Successfully approved ${successCount} request(s).`);
      }
      if (failCount > 0) {
        toast.error(`Failed to approve ${failCount} request(s).`);
      }
      refetch();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Bulk approve failed";
      toast.error(msg);
    }
  };

  // Bulk Reject API mutation handler
  const handleBulkReject = async (selectedIds: string[]) => {
    const numericIds = selectedIds
      .map((id) => parseInt(id, 10))
      .filter((id) => !isNaN(id));

    if (numericIds.length === 0) return;

    try {
      const res = await bulkRejectMutation.mutateAsync({
        approval_ids: numericIds,
        reject_remarks: "Rejected via bulk action",
      });

      const successCount = res.results.filter((r) => r.success).length;
      const failCount = res.results.filter((r) => !r.success).length;

      if (successCount > 0) {
        toast.success(`Successfully rejected ${successCount} request(s).`);
      }
      if (failCount > 0) {
        toast.error(`Failed to reject ${failCount} request(s).`);
      }
      refetch();
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : "Bulk reject failed";
      toast.error(msg);
    }
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
            onTabChange={handleTabChange}
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
            isLoading={isApprovalsLoading}
            onViewDetails={handleViewDetails}
            onApprove={handleOpenApprove}
            onReject={handleOpenReject}
            totalRecords={approvalsData?.pagination.total_records}
            currentPage={currentPage}
            pageSize={pageSize}
            onPageChange={setCurrentPage}
            onPageSizeChange={setPageSize}
            onBulkApprove={handleBulkApprove}
            onBulkReject={handleBulkReject}
          />
        </div>

        {/* Drawer for View Details & Workflow Timeline */}
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
