"use client";

import React from "react";
import { PublicRoute } from "@/features/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <PublicRoute>
      <main className="min-h-screen bg-[#DCEFFE] text-foreground font-sans flex flex-col justify-between">
        {children}
      </main>
    </PublicRoute>
  );
}
