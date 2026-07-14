"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

interface ErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorBoundary({ error, reset }: ErrorBoundaryProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-foreground font-sans text-center">
      <div className="w-full max-w-md rounded-lg border border-destructive/20 bg-card p-8 shadow-base">
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive text-xl">
          ⚠️
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground mb-2">
          Something went wrong!
        </h1>
        <p className="text-sm text-muted-foreground mb-6">
          An unexpected system error occurred. Please try reloading the view.
        </p>
        <Button onClick={() => reset()} variant="primary">
          Try Again
        </Button>
      </div>
    </div>
  );
}
