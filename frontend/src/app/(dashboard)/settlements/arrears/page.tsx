"use client";

import { ProtectedRoute } from "@/features/auth";
import { ArrearsView } from "@/features/settlements/components/arrears-view";

export default function ArrearsPage() {
  return (
    <ProtectedRoute requiredPermission={{ feature: "arrears", action: "read" }}>
      <ArrearsView />
    </ProtectedRoute>
  );
}
