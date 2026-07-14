"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";
import { Eye, EyeOff, ShieldAlert } from "lucide-react";
import { Logo } from "@/components/ui/logo";
import { LoginIllustration } from "@/components/ui/login-illustration";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { useLoading } from "@/providers/loading-provider";

const loginSchema = z.object({
  identifier: z
    .string()
    .min(1, "Email address or Mobile Number is required")
    .refine((val) => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      const phoneRegex = /^\d{10}$/;
      return emailRegex.test(val) || phoneRegex.test(val);
    }, "Please enter a valid email address or a 10-digit mobile number"),
  password: z.string().optional(),
});

type LoginSchemaType = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const { startLoading, stopLoading } = useLoading();
  const [showPassword, setShowPassword] = useState(false);
  const [isOTPMode, setIsOTPMode] = useState(true); // Default to OTP Mode matching the screenshot's single field
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginSchemaType>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      identifier: "",
      password: "",
    },
  });

  const onSubmit = (data: LoginSchemaType) => {
    setApiError(null);

    // If Password mode is active but password is empty, trigger manually
    if (!isOTPMode && !data.password) {
      setApiError("Password is required in Password login mode.");
      toast.error("Please enter your password.");
      return;
    }

    startLoading();

    // Mock API delay for verification of loading spinner
    setTimeout(() => {
      stopLoading();
      // Mock validation results
      if (data.identifier.includes("error")) {
        setApiError("Invalid credentials. Please verify your Email or Phone Number.");
        toast.error("Login failed. Check your inputs.");
      } else {
        toast.success("Welcome back! Loading your dashboard workspace...");
        // Mock successful login redirection path
        window.location.href = "/dashboard";
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
              Managing Employee activities & attendance made simple with HRMS System
            </p>
          </div>
        </div>

        {/* Right column white login card */}
        <div className="lg:col-span-5 flex justify-center w-full">
          <div className="w-full max-w-[450px] bg-white rounded-2xl shadow-xl p-8 border border-slate-100 flex flex-col space-y-6">
            <div className="text-left space-y-1">
              <h2 className="text-xl font-bold text-slate-800 tracking-tight">
                Login to Dashboard
              </h2>
              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-500 font-medium">
                  Hello there, Let&apos;s get started.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setIsOTPMode(!isOTPMode);
                    setApiError(null);
                  }}
                  className="text-xs text-[#0B85C9] font-bold hover:underline cursor-pointer"
                >
                  {isOTPMode ? "Use Password Login" : "Use OTP Login"}
                </button>
              </div>
            </div>

            {apiError && (
              <Alert variant="destructive" className="animate-in fade-in">
                <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
                <div className="flex flex-col text-left">
                  <span className="font-semibold text-xs">Authentication Error</span>
                  <span className="text-[10px] opacity-90 mt-0.5">{apiError}</span>
                </div>
              </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Email / Mobile input */}
              <Input
                label="Email or Phone Number"
                type="text"
                placeholder="Enter Email address OR Mobile Number"
                className="w-full border-slate-200 placeholder:text-slate-400 focus:border-[#0B85C9]"
                {...register("identifier")}
                error={errors.identifier?.message}
              />

              {/* Password field only shown in Password Mode */}
              {!isOTPMode && (
                <div className="relative">
                  <Input
                    label="Password"
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    className="w-full pr-10 border-slate-200 focus:border-[#0B85C9]"
                    {...register("password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-[32px] text-slate-400 hover:text-slate-600 cursor-pointer"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4.5 w-4.5" />
                    ) : (
                      <Eye className="h-4.5 w-4.5" />
                    )}
                  </button>
                  <div className="flex justify-end mt-1">
                    <Link
                      href="/forgot-password"
                      className="text-xs font-semibold text-[#0B85C9] hover:underline cursor-pointer"
                    >
                      Forgot Password?
                    </Link>
                  </div>
                </div>
              )}

              {/* Login Action Button */}
              <Button
                type="submit"
                className="w-full bg-[#0B85C9] hover:bg-[#0974b0] text-white font-semibold py-2.5 rounded-lg transition-all"
              >
                Login
              </Button>
            </form>

            {/* Terms Footer Text */}
            <p className="text-[10px] text-slate-500 text-center font-medium leading-relaxed">
              By logging in, you accept our{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  toast.info("Terms and conditions document is a visual demo.");
                }}
                className="text-[#0B85C9] font-bold hover:underline"
              >
                Terms & Conditions
              </a>{" "}
              &{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  toast.info("Service agreement document is a visual demo.");
                }}
                className="text-[#0B85C9] font-bold hover:underline"
              >
                Service Agreement
              </a>
            </p>
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
