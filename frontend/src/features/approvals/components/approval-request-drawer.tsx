"use client";

import { Palmtree, Calendar, User, Clock, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { Drawer } from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ApprovalRequest } from "../types";
import { useApprovalDetails, useApprovalTimeline } from "../hooks/use-approvals";

interface ApprovalRequestDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  request: ApprovalRequest | null;
  onApprove?: (request: ApprovalRequest) => void;
  onReject?: (request: ApprovalRequest) => void;
}

export function ApprovalRequestDrawer({
  isOpen,
  onClose,
  request,
  onApprove,
  onReject,
}: ApprovalRequestDrawerProps) {
  const numericId = request?.numericId ? Number(request.numericId) : null;
  const { data: detailsData, isLoading: detailsLoading } = useApprovalDetails(numericId);
  const { data: timelineData, isLoading: timelineLoading } = useApprovalTimeline(numericId);

  if (!request) return null;

  const isLeave = request.type === "Leave";

  const getStatusBadge = () => {
    switch (request.status) {
      case "approved":
        return <Badge variant="success">Approved</Badge>;
      case "rejected":
        return <Badge variant="destructive">Rejected</Badge>;
      default:
        return <Badge variant="warning">Pending</Badge>;
    }
  };

  return (
    <Drawer
      isOpen={isOpen}
      onClose={onClose}
      title="Approval Request Details"
      position="right"
      footer={
        <div className="flex items-center justify-end gap-2.5 w-full">
          {request.status === "pending" ? (
            <>
              <Button
                variant="destructive"
                size="sm"
                onClick={() => {
                  onClose();
                  if (onReject) onReject(request);
                }}
                className="h-8 px-4 text-xs font-semibold"
              >
                Reject
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  onClose();
                  if (onApprove) onApprove(request);
                }}
                className="h-8 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white"
              >
                Approve
              </Button>
            </>
          ) : null}
          <Button variant="outline" size="sm" onClick={onClose} className="h-8 px-4 text-xs">
            Close
          </Button>
        </div>
      }
    >
      <div className="space-y-6 text-xs text-slate-700 dark:text-slate-300">
        {/* Top Header Card */}
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-full flex items-center justify-center ${
                isLeave
                  ? "bg-amber-100 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400"
                  : "bg-sky-100 dark:bg-sky-950/40 text-sky-600 dark:text-sky-400"
              }`}
            >
              {isLeave ? <Palmtree className="h-5 w-5" /> : <Calendar className="h-5 w-5" />}
            </div>
            <div>
              <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                {request.type} Request
              </h4>
              <p className="text-slate-500 font-medium">{request.subtype}</p>
            </div>
          </div>
          <div>{getStatusBadge()}</div>
        </div>

        {/* Employee Info Card */}
        <div className="space-y-3">
          <h5 className="font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800 pb-1.5 flex items-center gap-2">
            <User className="h-4 w-4 text-slate-400" />
            <span>Employee Information</span>
          </h5>
          <div className="grid grid-cols-2 gap-3 bg-white dark:bg-slate-950 p-3 rounded-lg border border-slate-200 dark:border-slate-800">
            <div>
              <span className="text-slate-400 block text-[11px]">Employee Code</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {request.employeeCode}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Employee Name</span>
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                {request.employeeName}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Designation</span>
              <span className="font-medium text-slate-700 dark:text-slate-300">
                {request.designation}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[11px]">Department</span>
              <span className="font-medium text-slate-700 dark:text-slate-300">
                {request.department}
              </span>
            </div>
          </div>
        </div>

        {/* Request Details Breakdown */}
        <div className="space-y-3">
          <h5 className="font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800 pb-1.5 flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-400" />
            <span>Request Details</span>
          </h5>
          <div className="bg-white dark:bg-slate-950 p-3 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2.5">
            {detailsLoading ? (
              <div className="animate-pulse space-y-2 py-2">
                <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-1/2" />
                <div className="h-3.5 bg-slate-200 dark:bg-slate-800 rounded w-3/4" />
              </div>
            ) : (
              <>
                {isLeave ? (
                  <>
                    <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500">From Date:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {request.details.fromDate || "-"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500">To Date:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {request.details.toDate || "-"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500">Total Duration:</span>
                      <span className="font-bold text-sky-600 dark:text-sky-400">
                        {request.details.totalDays || "-"}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                      <span className="text-slate-500">Attendance Date:</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">
                        {request.details.date || "-"}
                      </span>
                    </div>
                    {request.details.inTime && (
                      <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                        <span className="text-slate-500">In Time:</span>
                        <span className="font-medium">{request.details.inTime}</span>
                      </div>
                    )}
                    {request.details.outTime && (
                      <div className="flex justify-between items-center py-1 border-b border-slate-100 dark:border-slate-800">
                        <span className="text-slate-500">Out Time:</span>
                        <span className="font-medium">{request.details.outTime}</span>
                      </div>
                    )}
                  </>
                )}

                {detailsData?.source && (
                  <div className="py-1">
                    <span className="text-slate-500 block mb-1">Source Payload:</span>
                    <pre className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[10px] overflow-x-auto text-slate-800 dark:text-slate-200">
                      {JSON.stringify(detailsData.source, null, 2)}
                    </pre>
                  </div>
                )}

                <div className="py-1">
                  <span className="text-slate-500 block mb-1">Reason / Remarks:</span>
                  <p className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 italic">
                    {request.details.reason || "No reason specified."}
                  </p>
                </div>
                <div className="flex justify-between items-center pt-2 text-[11px] text-slate-400">
                  <span>Submitted On:</span>
                  <span>{request.submittedDate}</span>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Status Activity Log & Live Timeline */}
        <div className="space-y-3">
          <h5 className="font-bold text-slate-800 dark:text-slate-200 border-b border-slate-200 dark:border-slate-800 pb-1.5 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-slate-400" />
            <span>Workflow & Activity Log</span>
          </h5>
          <div className="bg-white dark:bg-slate-950 p-3 rounded-lg border border-slate-200 dark:border-slate-800 space-y-2">
            {timelineLoading ? (
              <div className="animate-pulse space-y-2 py-2">
                <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-2/3" />
                <div className="h-3 bg-slate-200 dark:bg-slate-800 rounded w-1/3" />
              </div>
            ) : timelineData && timelineData.length > 0 ? (
              <div className="space-y-2 divide-y divide-slate-100 dark:divide-slate-800">
                {timelineData.map((ev, i) => (
                  <div key={i} className="pt-2 first:pt-0 space-y-0.5">
                    <div className="flex items-center justify-between font-semibold text-slate-800 dark:text-slate-200 text-xs">
                      <span className="capitalize">{ev.event}</span>
                      <span className="text-[10px] text-slate-400 font-normal">
                        {new Date(ev.at).toLocaleString("en-GB")}
                      </span>
                    </div>
                    {ev.by && (
                      <p className="text-[11px] text-slate-500">
                        By User ID: #{ev.by}
                      </p>
                    )}
                    {ev.remarks && (
                      <p className="text-[11px] italic text-slate-600 dark:text-slate-400">
                        &ldquo;{ev.remarks}&rdquo;
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <>
                {request.status === "pending" && (
                  <div className="flex items-center gap-2 text-amber-600 dark:text-amber-400">
                    <Clock className="h-4 w-4 shrink-0" />
                    <span>
                      Pending approval with: <strong>{request.pendingApprover}</strong>
                    </span>
                  </div>
                )}

                {request.status === "approved" && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold">
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                      <span>Approved by {request.approvedBy || "Manager"}</span>
                    </div>
                    {request.actionDate && (
                      <p className="text-[11px] text-slate-400 pl-6">On: {request.actionDate}</p>
                    )}
                    {request.remarks && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 pl-6 italic">
                        &ldquo;{request.remarks}&rdquo;
                      </p>
                    )}
                  </div>
                )}

                {request.status === "rejected" && (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-semibold">
                      <XCircle className="h-4 w-4 shrink-0" />
                      <span>Rejected by {request.rejectedBy || "Manager"}</span>
                    </div>
                    {request.actionDate && (
                      <p className="text-[11px] text-slate-400 pl-6">On: {request.actionDate}</p>
                    )}
                    {request.remarks && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 pl-6 italic">
                        &ldquo;{request.remarks}&rdquo;
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </Drawer>
  );
}
