"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { ArrowLeft, CheckCircle2, ShieldAlert } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { LoginIllustration } from "@/components/ui/login-illustration";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { useLoading } from "@/providers/loading-provider";

const forgotPasswordSchema = z.object({
  email: z.string().min(1, "Email address is required").email("Please enter a valid email address"),
});

type ForgotPasswordSchemaType = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPasswordPage() {
  const { startLoading, stopLoading } = useLoading();
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordSchemaType>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = (data: ForgotPasswordSchemaType) => {
    setApiError(null);
    startLoading();

    // Mock API call
    setTimeout(() => {
      stopLoading();

      if (data.email.includes("error")) {
        setApiError("This email address is not registered in our system.");
        toast.error("Recovery email failed. Check your inputs.");
      } else {
        setIsSuccess(true);
        toast.success("Recovery reset link has been dispatched successfully!");
      }
    }, 1500);
  };

  return (
    <div className="flex-1 flex flex-col justify-between p-6 md:p-12 min-h-screen">
      {/* Top Header Logo */}
      <header className="w-full flex items-center justify-between pb-6">
        <Logo />
      </header>

      {/* Main Split Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center max-w-7xl mx-auto w-full">
        {/* Left column illustration & welcome */}
        <div className="lg:col-span-7 flex flex-col items-center justify-center text-center space-y-6">
          <LoginIllustration />
          <div className="space-y-2">
            <h1 className="text-3xl font-extrabold text-[#1E293B]">Welcome!</h1>
            <p className="text-sm font-medium text-[#475569] max-w-md">
              Managing Employee activities & attendance made simple with HRMS
            </p>
          </div>
        </div>

        {/* Right column white card */}
        <div className="lg:col-span-5 flex justify-center w-full">
          <div className="w-full max-w-[450px] bg-white rounded-2xl shadow-xl p-8 border border-slate-100 flex flex-col space-y-6">
            {!isSuccess ? (
              <>
                <div className="text-left space-y-1">
                  <h2 className="text-xl font-bold text-slate-800 tracking-tight">
                    Reset Password
                  </h2>
                  <p className="text-xs text-slate-500 font-medium leading-relaxed">
                    Provide your email address below, and we&apos;ll send a link to restore access.
                  </p>
                </div>

                {apiError && (
                  <Alert variant="destructive" className="animate-in fade-in">
                    <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
                    <div className="flex flex-col text-left">
                      <span className="font-semibold text-xs">Recovery Error</span>
                      <span className="text-[10px] opacity-90 mt-0.5">{apiError}</span>
                    </div>
                  </Alert>
                )}

                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                  {/* Email Input */}
                  <Input
                    label="Email Address"
                    type="email"
                    placeholder="name@company.com"
                    className="w-full border-slate-200 placeholder:text-slate-400 focus:border-[#0B85C9]"
                    {...register("email")}
                    error={errors.email?.message}
                  />

                  {/* Send Action Button */}
                  <Button
                    type="submit"
                    className="w-full bg-[#0B85C9] hover:bg-[#0974b0] text-white font-semibold py-2.5 rounded-lg transition-all"
                  >
                    Send Reset Link
                  </Button>
                </form>

                {/* Back to Login link */}
                <div className="flex justify-center pt-2">
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-1 text-xs font-bold text-[#0B85C9] hover:underline cursor-pointer"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                    <span>Back to Login</span>
                  </Link>
                </div>
              </>
            ) : (
              // Success Screen layout
              <div className="text-center space-y-5 py-4 animate-in zoom-in-95 duration-300">
                <div className="inline-flex items-center justify-center h-12 w-12 rounded-full bg-emerald-50 text-emerald-500">
                  <CheckCircle2 className="h-8 w-8" />
                </div>
                <div className="space-y-2">
                  <h3 className="text-lg font-bold text-slate-800">Check Your Inbox</h3>
                  <p className="text-xs text-slate-500 font-medium leading-relaxed max-w-sm mx-auto">
                    We&apos;ve emailed a password recovery link to your address. Click the link to
                    update your security credentials.
                  </p>
                </div>
                <div className="pt-2">
                  <Link href="/login" passHref legacyBehavior>
                    <Button className="w-full bg-[#0B85C9] hover:bg-[#0974b0]">
                      Return to Login
                    </Button>
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Branding line */}
      <footer className="w-full text-center py-4 text-[10px] text-slate-400 font-semibold uppercase tracking-wider select-none">
        HRMS System &copy; {new Date().getFullYear()}
      </footer>
    </div>
  );
}
