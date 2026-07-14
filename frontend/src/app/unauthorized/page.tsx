"use client";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { useRouter } from "next/navigation";
import { ShieldAlert } from "lucide-react";

export default function UnauthorizedPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md border-destructive/20 text-center">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="rounded-full bg-destructive/10 p-3 text-destructive">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Access Denied</CardTitle>
          <CardDescription>
            You are not authenticated to access this page. Please sign in first.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          If you believe this is an error, please contact your organization administrator.
        </CardContent>
        <CardFooter className="flex justify-center gap-4">
          <Button variant="primary" onClick={() => router.push("/login")}>
            Sign In
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
