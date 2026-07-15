"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
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
import { useLogin } from "@/features/auth/hooks";
import { useAuthStore } from "@/features/auth/store";
import { ApiError } from "@/services/api-client/error-handler";

const loginSchema = z.object({
  email: z.string().min(1, "Email address is required").email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginSchemaType = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const searchParams = useSearchParams();
  const { startLoading, stopLoading } = useLoading();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const { mutate: login, isPending } = useLogin();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<LoginSchemaType>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  // Sync mutation loading state to global backdrop loader
  useEffect(() => {
    if (isPending) {
      startLoading();
    } else {
      stopLoading();
    }
  }, [isPending, startLoading, stopLoading]);

  const onSubmit = (data: LoginSchemaType) => {
    setApiError(null);

    login(
      {
        payload: {
          email: data.email,
          password: data.password,
          device_info: typeof window !== "undefined" ? window.navigator.userAgent : "Web Client",
        },
        orgId: "1", // Default primary Acme tenant org ID
      },
      {
        onSuccess: async (response) => {
          const { access_token } = response.data;
          // Set standard session in auth memory store
          useAuthStore.getState().setSession(access_token);

          try {
            // Fetch complete user profile context immediately on login success
            const { fetchCurrentUser } = await import("@/features/auth/services");
            const profileRes = await fetchCurrentUser();
            if (profileRes.success && profileRes.data) {
              useAuthStore.getState().setUserProfile(profileRes.data);
            }
          } catch (err) {
            console.error("Failed to fetch user profile on login:", err);
          }

          const redirectTo = searchParams.get("redirectTo") || "/dashboard";
          const targetUrl = redirectTo.startsWith("/") ? redirectTo : "/dashboard";

          toast.success("Welcome back! Loading your dashboard workspace...");
          window.location.href = targetUrl;
        },
        onError: (err) => {
          if (err instanceof ApiError) {
            // Map validation errors directly to the respective form inputs
            if (err.errors) {
              Object.entries(err.errors).forEach(([field, messages]) => {
                setError(field as keyof LoginSchemaType, {
                  type: "server",
                  message: messages.join(", "),
                });
              });
            }
            setApiError(err.message);
            toast.error(err.message);
          } else {
            const genericMsg = err instanceof Error ? err.message : "An unexpected error occurred.";
            setApiError(genericMsg);
            toast.error(genericMsg);
          }
        },
      }
    );
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
              <p className="text-xs text-slate-500 font-medium">
                Hello there, Let&apos;s get started.
              </p>
            </div>

            {apiError && (
              <Alert variant="destructive" className="animate-in fade-in">
                <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
                <div className="flex flex-col text-left">
                  <span className="font-semibold text-xs font-sans">Authentication Error</span>
                  <span className="text-[10px] opacity-90 mt-0.5 font-sans leading-tight">
                    {apiError}
                  </span>
                </div>
              </Alert>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              {/* Email Address Input */}
              <Input
                label="Email Address"
                type="email"
                placeholder="Enter email address"
                className="w-full border-slate-200 placeholder:text-slate-400 focus:border-[#0B85C9]"
                {...register("email")}
                error={errors.email?.message}
                disabled={isPending}
              />

              {/* Password Input with show/hide toggle */}
              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? "text" : "password"}
                  placeholder="Enter your password"
                  className="w-full pr-10 border-slate-200 focus:border-[#0B85C9]"
                  {...register("password")}
                  error={errors.password?.message}
                  disabled={isPending}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-[32px] text-slate-400 hover:text-slate-600 cursor-pointer disabled:opacity-50"
                  tabIndex={-1}
                  disabled={isPending}
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

              {/* Login Action Button */}
              <Button
                type="submit"
                className="w-full bg-[#0B85C9] hover:bg-[#0974b0] text-white font-semibold py-2.5 rounded-lg transition-all"
                disabled={isPending}
              >
                {isPending ? "Authenticating..." : "Login"}
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
