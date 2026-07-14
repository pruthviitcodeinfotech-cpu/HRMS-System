import { LoadingSpinner } from "@/components/feedback/loading-spinner";

export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6 text-foreground font-sans">
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size="lg" />
        <p className="text-xs font-semibold text-muted-foreground animate-pulse">
          Loading system view...
        </p>
      </div>
    </div>
  );
}
