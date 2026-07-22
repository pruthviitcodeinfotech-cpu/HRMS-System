"use client";

import { ProtectedRoute } from "@/features/auth";
import { ArrearsView } from "@/features/settlements/components/arrears-view";

export default function ArrearsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "settlements", action: "read" }}>
      <ArrearsView />
    </ProtectedRoute>
  );
}
