"use client";

import React, { useState, useEffect } from "react";
import {
  Bell,
  CheckCheck,
  Trash2,
  Archive,
  Plus,
  Clock,
  ShieldAlert,
  Info,
  CheckCircle2,
  AlertCircle,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/feedback/skeleton";
import { EmptyState } from "@/components/feedback/empty-state";
import {
  useMyNotifications,
  useMyNotificationCounts,
  useMarkNotificationRead,
  useMarkNotificationUnread,
  useArchiveNotification,
  useDeleteNotification,
  useBulkMarkRead,
  useCreateNotification,
} from "../hooks/use-notifications";
import { MyNotificationSchema } from "../types";

export const NotificationCenter: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"all" | "unread" | "archived">("all");
  const [typeFilter, setTypeFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize] = useState<number>(10);

  // Broadcast Modal State
  const [isBroadcastOpen, setIsBroadcastOpen] = useState<boolean>(false);
  const [broadcastForm, setBroadcastForm] = useState({
    title: "",
    message: "",
    notification_type: "announcement" as const,
    priority: "medium" as const,
  });

  // Reset pagination on filter or tab change
  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, typeFilter, priorityFilter]);

  const { data: countsData } = useMyNotificationCounts();

  const {
    data: notificationsData,
    isLoading,
    isError,
    error,
  } = useMyNotifications({
    page: currentPage,
    page_size: pageSize,
    status: activeTab === "unread" ? "unread" : undefined,
    archived: activeTab === "archived",
    notification_type: typeFilter || undefined,
    priority: priorityFilter || undefined,
  });

  const markReadMutation = useMarkNotificationRead();
  const markUnreadMutation = useMarkNotificationUnread();
  const archiveMutation = useArchiveNotification();
  const deleteMutation = useDeleteNotification();
  const bulkMarkReadMutation = useBulkMarkRead();
  const createNotificationMutation = useCreateNotification();

  const notifications = notificationsData?.items || [];
  const pagination = notificationsData?.pagination;

  const handleMarkAllRead = async () => {
    try {
      await bulkMarkReadMutation.mutateAsync({ all_unread: true });
      toast.success("All notifications marked as read.");
    } catch {
      toast.error("Failed to mark notifications as read.");
    }
  };

  const handleCreateBroadcast = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!broadcastForm.title || !broadcastForm.message) {
      toast.error("Please fill in title and message.");
      return;
    }
    try {
      await createNotificationMutation.mutateAsync(broadcastForm);
      toast.success("Broadcast notification published successfully.");
      setIsBroadcastOpen(false);
      setBroadcastForm({ title: "", message: "", notification_type: "announcement", priority: "medium" });
    } catch {
      toast.error("Failed to send broadcast notification.");
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "urgent":
      case "high":
        return "bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 border border-rose-200 dark:border-rose-800";
      case "medium":
        return "bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400 border border-amber-200 dark:border-amber-800";
      default:
        return "bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400 border border-blue-200 dark:border-blue-800";
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
            <Bell className="h-6 w-6 text-blue-600" />
            Notification Center
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Stay updated with system announcements, approval alerts, attendance reminders, and payroll updates.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleMarkAllRead}
            disabled={bulkMarkReadMutation.isPending || countsData?.unread_count === 0}
            className="gap-2 text-xs"
          >
            <CheckCheck className="h-4 w-4 text-emerald-600" />
            Mark All as Read
          </Button>

          <Button
            size="sm"
            onClick={() => setIsBroadcastOpen(true)}
            className="gap-2 text-xs bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Plus className="h-4 w-4" />
            New Broadcast
          </Button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-card p-4 rounded-xl border border-border space-y-1 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Total Notifications</span>
          <p className="text-2xl font-bold text-slate-800 dark:text-slate-100">
            {countsData?.total_count || 0}
          </p>
        </div>
        <div className="bg-card p-4 rounded-xl border border-border space-y-1 shadow-xs">
          <span className="text-xs font-semibold text-rose-500">Unread Notifications</span>
          <p className="text-2xl font-bold text-rose-600 dark:text-rose-400">
            {countsData?.unread_count || 0}
          </p>
        </div>
        <div className="bg-card p-4 rounded-xl border border-border space-y-1 shadow-xs">
          <span className="text-xs font-semibold text-slate-500">Archived Items</span>
          <p className="text-2xl font-bold text-slate-600 dark:text-slate-400">
            {countsData?.archived_count || 0}
          </p>
        </div>
      </div>

      {/* Main Panel */}
      <div className="bg-card rounded-2xl border border-border shadow-xs overflow-hidden">
        {/* Tabs & Filter Bar */}
        <div className="p-4 border-b border-border space-y-3 bg-slate-50/50 dark:bg-slate-900/50">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Status Tabs */}
            <div className="flex items-center gap-1 bg-slate-200/60 dark:bg-slate-800/60 p-1 rounded-xl w-full sm:w-auto">
              <button
                onClick={() => setActiveTab("all")}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  activeTab === "all"
                    ? "bg-white dark:bg-slate-900 text-blue-600 dark:text-blue-400 shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setActiveTab("unread")}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  activeTab === "unread"
                    ? "bg-white dark:bg-slate-900 text-rose-600 dark:text-rose-400 shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                }`}
              >
                Unread ({countsData?.unread_count || 0})
              </button>
              <button
                onClick={() => setActiveTab("archived")}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-colors ${
                  activeTab === "archived"
                    ? "bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900"
                }`}
              >
                Archived ({countsData?.archived_count || 0})
              </button>
            </div>

            {/* Dropdown Filters */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="h-9 text-xs rounded-lg border border-input bg-background px-3 py-1 font-medium text-slate-700 dark:text-slate-200"
              >
                <option value="">All Categories</option>
                <option value="system">System</option>
                <option value="announcement">Announcement</option>
                <option value="approval">Approval</option>
                <option value="attendance">Attendance</option>
                <option value="leave">Leave</option>
                <option value="payroll">Payroll</option>
              </select>

              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="h-9 text-xs rounded-lg border border-input bg-background px-3 py-1 font-medium text-slate-700 dark:text-slate-200"
              >
                <option value="">All Priorities</option>
                <option value="urgent">Urgent</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="p-6 space-y-3">
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </div>
        )}

        {/* Error State */}
        {isError && (
          <div className="p-8 text-center text-rose-500 text-xs bg-rose-50/50 dark:bg-rose-950/20">
            <AlertCircle className="h-6 w-6 mx-auto mb-2 text-rose-500" />
            {error instanceof Error ? error.message : "Failed to load notifications."}
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !isError && notifications.length === 0 && (
          <EmptyState
            title="No Notifications Found"
            description="There are no notifications matching the selected tab or filters."
          />
        )}

        {/* Notifications List */}
        {!isLoading && !isError && notifications.length > 0 && (
          <div className="divide-y divide-border dark:divide-slate-800">
            {notifications.map((item: MyNotificationSchema) => (
              <div
                key={item.recipient_id}
                className={`p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-colors hover:bg-slate-50/60 dark:hover:bg-slate-900/40 ${
                  item.status === "unread" ? "bg-blue-50/20 dark:bg-blue-950/10" : ""
                }`}
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="pt-1">
                    {item.priority === "urgent" || item.priority === "high" ? (
                      <ShieldAlert className="h-5 w-5 text-rose-500 shrink-0" />
                    ) : (
                      <Info className="h-5 w-5 text-blue-500 shrink-0" />
                    )}
                  </div>
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold text-slate-900 dark:text-slate-100">
                        {item.title}
                      </span>
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${getPriorityBadge(item.priority)}`}>
                        {item.priority}
                      </span>
                      <span className="text-[10px] font-semibold text-slate-400 capitalize">
                        • {item.notification_type}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      {item.message}
                    </p>

                    <div className="text-[11px] text-slate-400 flex items-center gap-2 pt-0.5">
                      <Clock className="h-3 w-3" />
                      <span>{new Date(item.created_at).toLocaleString()}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  {item.status === "unread" ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => markReadMutation.mutate(item.notification_id)}
                      className="text-xs gap-1.5 text-blue-600 hover:text-blue-700"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Mark Read
                    </Button>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => markUnreadMutation.mutate(item.notification_id)}
                      className="text-xs gap-1.5 text-slate-400 hover:text-slate-600"
                    >
                      Mark Unread
                    </Button>
                  )}

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => archiveMutation.mutate(item.notification_id)}
                    className="text-xs gap-1.5 text-slate-500 hover:text-slate-700"
                  >
                    <Archive className="h-3.5 w-3.5" />
                    Archive
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => deleteMutation.mutate(item.notification_id)}
                    className="text-xs gap-1.5 text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination Footer */}
        {pagination && pagination.total_pages > 1 && (
          <div className="p-4 border-t border-border flex items-center justify-between text-xs bg-slate-50/50 dark:bg-slate-900/50">
            <span className="text-slate-500">
              Page {pagination.page} of {pagination.total_pages} ({pagination.total_records} notifications)
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={!pagination.has_previous}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                className="h-8 text-xs"
              >
                Previous
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={!pagination.has_next}
                onClick={() => setCurrentPage((p) => p + 1)}
                className="h-8 text-xs"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Broadcast Modal */}
      {isBroadcastOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 backdrop-blur-xs">
          <div className="bg-card w-full max-w-lg rounded-2xl border border-border p-6 shadow-2xl space-y-4 dark:border-slate-800 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-lg font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <Plus className="h-5 w-5 text-blue-600" />
                Publish Broadcast Notification
              </h3>
              <button onClick={() => setIsBroadcastOpen(false)} className="text-slate-400 hover:text-slate-600">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleCreateBroadcast} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Notification Title *
                </label>
                <Input
                  type="text"
                  placeholder="e.g. System Maintenance Notice"
                  value={broadcastForm.title}
                  onChange={(e) => setBroadcastForm({ ...broadcastForm, title: e.target.value })}
                  className="text-xs"
                  required
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  Notification Message *
                </label>
                <textarea
                  rows={3}
                  placeholder="Enter notification details for all employees..."
                  value={broadcastForm.message}
                  onChange={(e) => setBroadcastForm({ ...broadcastForm, message: e.target.value })}
                  className="w-full text-xs rounded-md border border-input bg-background p-2.5 text-slate-800 dark:text-slate-200 focus:ring-2 focus:ring-blue-500 focus:outline-hidden"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Category
                  </label>
                  <select
                    value={broadcastForm.notification_type}
                    onChange={(e: any) => setBroadcastForm({ ...broadcastForm, notification_type: e.target.value })}
                    className="w-full h-9 text-xs rounded-md border border-input bg-background px-3 py-1 font-medium text-slate-700 dark:text-slate-200"
                  >
                    <option value="announcement">Announcement</option>
                    <option value="system">System</option>
                    <option value="alert">Alert</option>
                    <option value="reminder">Reminder</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Priority
                  </label>
                  <select
                    value={broadcastForm.priority}
                    onChange={(e: any) => setBroadcastForm({ ...broadcastForm, priority: e.target.value })}
                    className="w-full h-9 text-xs rounded-md border border-input bg-background px-3 py-1 font-medium text-slate-700 dark:text-slate-200"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-border">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsBroadcastOpen(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={createNotificationMutation.isPending}
                  className="text-xs bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {createNotificationMutation.isPending ? "Publishing..." : "Publish Notification"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
