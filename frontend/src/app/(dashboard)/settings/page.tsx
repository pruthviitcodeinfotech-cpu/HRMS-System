"use client";

import { ProtectedRoute } from "@/features/auth";

export default function SettingsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "settings", action: "read" }}>
      <div>
        <h1 className="text-3xl font-bold mb-2">Global Settings</h1>
        <p className="text-sm text-foreground/75">
          Configure tenant profiles, system alerts, organization branches, and roles.
        </p>
      </div>
    </ProtectedRoute>
  );
}
