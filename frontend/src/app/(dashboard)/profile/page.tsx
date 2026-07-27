"use client";

import { ProtectedRoute } from "@/features/auth";
import { ProfilePage } from "@/features/profile";

export default function Profile() {
  return (
    <ProtectedRoute>
      <ProfilePage />
    </ProtectedRoute>
  );
}
