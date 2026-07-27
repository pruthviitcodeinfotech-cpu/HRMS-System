"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { Bell, CheckCheck, Trash2, ArrowRight, ShieldAlert, Clock, Info } from "lucide-react";
import {
  useMyNotifications,
  useMyNotificationCounts,
  useMarkNotificationRead,
  useBulkMarkRead,
  useDeleteNotification,
} from "../hooks/use-notifications";
import { MyNotificationSchema } from "../types";

export const NotificationDropdown: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const { data: countsData } = useMyNotificationCounts();
  const { data: notificationsData, isLoading } = useMyNotifications({ page: 1, page_size: 8 });

  const markReadMutation = useMarkNotificationRead();
  const bulkMarkReadMutation = useBulkMarkRead();
  const deleteMutation = useDeleteNotification();

  const unreadCount = countsData?.unread_count || 0;
  const notifications = notificationsData?.items || [];

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleMarkAllRead = async () => {
    await bulkMarkReadMutation.mutateAsync({ all_unread: true });
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "urgent":
      case "high":
        return "bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400";
      case "medium":
        return "bg-amber-50 text-amber-600 dark:bg-amber-950/40 dark:text-amber-400";
      default:
        return "bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400";
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button with Live Badge */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-100 transition-colors cursor-pointer relative"
        aria-label="Notifications"
        title="Notifications"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-4.5 w-4.5 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white ring-2 ring-white dark:ring-slate-900">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {/* Popover Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-border bg-card text-card-foreground shadow-2xl z-50 animate-in fade-in slide-in-from-top-2 duration-150 origin-top-right overflow-hidden dark:border-slate-800">
          {/* Panel Header */}
          <div className="p-4 border-b border-border dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-900/50">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 rounded-full">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                disabled={bulkMarkReadMutation.isPending}
                className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline font-semibold flex items-center gap-1 cursor-pointer"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          {/* List Content */}
          <div className="max-h-80 overflow-y-auto divide-y divide-border dark:divide-slate-800">
            {isLoading ? (
              <div className="p-6 text-center text-xs text-slate-400 space-y-2">
                <Clock className="h-5 w-5 mx-auto animate-spin text-blue-500" />
                <span>Loading notifications...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-400 space-y-1">
                <Bell className="h-8 w-8 mx-auto text-slate-300 dark:text-slate-600 mb-2" />
                <p className="text-xs font-semibold text-slate-600 dark:text-slate-400">All caught up!</p>
                <p className="text-[11px]">No unread notifications at the moment.</p>
              </div>
            ) : (
              notifications.map((item: MyNotificationSchema) => (
                <div
                  key={item.recipient_id}
                  className={`p-3.5 flex items-start gap-3 transition-colors hover:bg-slate-50/70 dark:hover:bg-slate-800/40 ${
                    item.status === "unread" ? "bg-blue-50/20 dark:bg-blue-950/10" : ""
                  }`}
                >
                  <div className="pt-0.5">
                    {item.priority === "urgent" || item.priority === "high" ? (
                      <ShieldAlert className="h-4.5 w-4.5 text-rose-500 shrink-0" />
                    ) : (
                      <Info className="h-4.5 w-4.5 text-blue-500 shrink-0" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2 mb-0.5">
                      <p className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">
                        {item.title}
                      </p>
                      <span className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded ${getPriorityBadge(item.priority)}`}>
                        {item.priority}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-600 dark:text-slate-400 line-clamp-2 leading-relaxed">
                      {item.message}
                    </p>

                    <div className="flex items-center justify-between mt-2 text-[10px] text-slate-400">
                      <span>{new Date(item.created_at).toLocaleDateString()}</span>
                      <div className="flex items-center gap-2">
                        {item.status === "unread" && (
                          <button
                            onClick={() => markReadMutation.mutate(item.notification_id)}
                            className="text-blue-600 dark:text-blue-400 hover:underline font-semibold"
                          >
                            Mark read
                          </button>
                        )}
                        <button
                          onClick={() => deleteMutation.mutate(item.notification_id)}
                          className="text-slate-400 hover:text-rose-500 transition-colors"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Footer View All Link */}
          <div className="p-3 border-t border-border dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50 text-center">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
            >
              View Notification Center <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
};
