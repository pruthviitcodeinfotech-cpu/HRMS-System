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
import { ShieldX } from "lucide-react";

export default function ForbiddenPage() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md border-amber-500/20 text-center">
        <CardHeader className="flex flex-col items-center gap-2">
          <div className="rounded-full bg-amber-500/10 p-3 text-amber-500">
            <ShieldX className="h-8 w-8" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Forbidden Access</CardTitle>
          <CardDescription>
            You do not have the required permissions to view this resource.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Your role permission credentials do not authorize access to this section.
        </CardContent>
        <CardFooter className="flex justify-center gap-4">
          <Button variant="outline" onClick={() => router.back()}>
            Go Back
          </Button>
          <Button variant="primary" onClick={() => router.push("/dashboard")}>
            Go Dashboard
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
