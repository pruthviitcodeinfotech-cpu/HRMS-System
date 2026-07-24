"use client";

import { ProtectedRoute } from "@/features/auth";
import { SettingsPage } from "@/features/settings";

export default function Settings() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "settings", action: "read" }}>
      <SettingsPage />
    </ProtectedRoute>
  );
}

