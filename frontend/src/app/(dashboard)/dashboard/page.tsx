"use client";

import { ProtectedRoute } from "@/features/auth";

export default function DashboardPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "dashboard", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Dashboard Overview</h1>
        <p className="text-sm text-foreground/75">
          Select a section from the system menu to view and manage details.
        </p>
      </div>
    </ProtectedRoute>
  );
}
