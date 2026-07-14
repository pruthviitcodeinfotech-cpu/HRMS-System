"use client";

import React from "react";
import { PublicRoute } from "@/features/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <PublicRoute>
      <main className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground font-sans">
        <div className="w-full max-w-md rounded-lg border border-border bg-card p-8 shadow-base">
          {children}
        </div>
      </main>
    </PublicRoute>
  );
}
