import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background p-6 text-foreground font-sans text-center">
      <div className="w-full max-w-md rounded-lg border border-border bg-card p-8 shadow-base">
        <h1 className="text-4xl font-extrabold text-primary mb-2">404</h1>
        <h2 className="text-xl font-bold mb-2">Page Not Found</h2>
        <p className="text-sm text-muted-foreground mb-6">
          The page you are looking for does not exist or has been moved.
        </p>
        <Link href="/dashboard">
          <Button size="md">Return Home</Button>
        </Link>
      </div>
    </div>
  );
}
