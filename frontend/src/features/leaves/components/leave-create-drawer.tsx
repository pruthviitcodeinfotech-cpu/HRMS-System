"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  LeaveTypeSchema,
  LeaveSettingsSchema,
  AllocationFrequency,
  CarryForwardFrequency,
  LeaveCycle,
} from "../types";
import {
  useCreateLeaveType,
  useUpdateLeaveType,
  useUpdateLeaveSettings,
} from "../hooks";
import { ApiError } from "@/services/api-client/error-handler";

const leaveSchema = z.object({
  leaveCycle: z.enum(["calendar_year", "financial_year"]),
  leaveName: z.string().min(1, "Leave Name is required"),
  alias: z.string().min(1, "Alias is required"),
  description: z.string().optional(),
  autoAllocationNumber: z.string().min(1, "Number Of Auto Allocation Leaves is required"),
  autoAllocationPeriod: z.enum(["every_month", "every_calendar_year"]),
  carryForwardNumber: z.string().min(1, "Carry Forward is required"),
  carryForwardPeriod: z.enum(["end_of_every_month", "end_of_every_calendar_year"]),
  encashment: z.enum(["off", "on"]),
  encashmentLimit: z.string().optional(),
});

type LeaveFormValues = z.infer<typeof leaveSchema>;

interface LeaveCreateDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  editingLeave?: LeaveTypeSchema | null;
  currentSettings?: LeaveSettingsSchema | null;
}

export function LeaveCreateDrawer({
  isOpen,
  onClose,
  editingLeave,
  currentSettings,
}: LeaveCreateDrawerProps) {
  const [step, setStep] = useState<1 | 2>(1);

  const createLeaveMutation = useCreateLeaveType();
  const updateLeaveMutation = useUpdateLeaveType();
  const updateSettingsMutation = useUpdateLeaveSettings();

  const isSubmitting =
    createLeaveMutation.isPending ||
    updateLeaveMutation.isPending ||
    updateSettingsMutation.isPending;

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    setError,
    formState: { errors },
  } = useForm<LeaveFormValues>({
    resolver: zodResolver(leaveSchema),
    defaultValues: {
      leaveCycle: currentSettings?.leave_cycle || "calendar_year",
      leaveName: "",
      alias: "",
      description: "",
      autoAllocationNumber: "0",
      autoAllocationPeriod: "every_month",
      carryForwardNumber: "0",
      carryForwardPeriod: "end_of_every_month",
      encashment: "off",
      encashmentLimit: "0",
    },
  });

  const leaveCycle = watch("leaveCycle");
  const autoAllocationPeriod = watch("autoAllocationPeriod");
  const carryForwardPeriod = watch("carryForwardPeriod");
  const encashment = watch("encashment");

  // Populate form when editing or opening
  useEffect(() => {
    if (isOpen) {
      setStep(editingLeave ? 2 : 1);
      if (editingLeave) {
        reset({
          leaveCycle: currentSettings?.leave_cycle || "calendar_year",
          leaveName: editingLeave.name || "",
          alias: editingLeave.alias || "",
          description: editingLeave.description || "",
          autoAllocationNumber: String(editingLeave.auto_allocation_count ?? 0),
          autoAllocationPeriod:
            editingLeave.allocation_frequency === "yearly"
              ? "every_calendar_year"
              : "every_month",
          carryForwardNumber: String(editingLeave.carry_forward_count ?? 0),
          carryForwardPeriod:
            editingLeave.carry_forward_frequency === "yearly"
              ? "end_of_every_calendar_year"
              : "end_of_every_month",
          encashment: editingLeave.encashment_enabled ? "on" : "off",
          encashmentLimit: String(editingLeave.encashment_limit ?? 0),
        });
      } else {
        reset({
          leaveCycle: currentSettings?.leave_cycle || "calendar_year",
          leaveName: "",
          alias: "",
          description: "",
          autoAllocationNumber: "0",
          autoAllocationPeriod: "every_month",
          carryForwardNumber: "0",
          carryForwardPeriod: "end_of_every_month",
          encashment: "off",
          encashmentLimit: "0",
        });
      }
    }
  }, [isOpen, editingLeave, currentSettings, reset]);

  // Handle ESC key press to close drawer
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const onFormSubmit = async (data: LeaveFormValues) => {
    try {
      // 1. Update Leave Settings if cycle changed
      const selectedCycle: LeaveCycle = data.leaveCycle;
      if (!currentSettings || currentSettings.leave_cycle !== selectedCycle) {
        await updateSettingsMutation.mutateAsync({
          leave_cycle: selectedCycle,
          cycle_start_month: selectedCycle === "financial_year" ? 4 : 1,
        });
      }

      const autoNum = parseFloat(data.autoAllocationNumber) || 0;
      const carryNum = parseFloat(data.carryForwardNumber) || 0;
      const encashNum = parseFloat(data.encashmentLimit || "0") || carryNum || 0;

      const allocationFreq: AllocationFrequency =
        data.autoAllocationPeriod === "every_calendar_year" ? "yearly" : "monthly";

      const carryFreq: CarryForwardFrequency =
        data.carryForwardPeriod === "end_of_every_calendar_year" ? "yearly" : "monthly";

      const isEncashmentOn = data.encashment === "on";

      if (editingLeave) {
        // Edit Leave Type
        await updateLeaveMutation.mutateAsync({
          id: editingLeave.id,
          data: {
            name: data.leaveName,
            alias: data.alias,
            description: data.description || null,
            auto_allocation_count: autoNum,
            allocation_frequency: allocationFreq,
            carry_forward_count: carryNum,
            carry_forward_frequency: carryFreq,
            encashment_enabled: isEncashmentOn,
            encashment_limit: isEncashmentOn ? encashNum : null,
            encashment_frequency: isEncashmentOn ? carryFreq : null,
          },
        });
        toast.success(`Leave policy "${data.leaveName}" updated successfully!`);
      } else {
        // Create Leave Type
        await createLeaveMutation.mutateAsync({
          name: data.leaveName,
          alias: data.alias,
          description: data.description || null,
          auto_allocation_count: autoNum,
          allocation_frequency: allocationFreq,
          carry_forward_count: carryNum,
          carry_forward_frequency: carryFreq,
          encashment_enabled: isEncashmentOn,
          encashment_limit: isEncashmentOn ? encashNum : null,
          encashment_frequency: isEncashmentOn ? carryFreq : null,
          is_active: true,
        });
        toast.success(`Leave policy "${data.leaveName}" created successfully!`);
      }

      onClose();
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.errors) {
          if (err.errors.alias) {
            setError("alias", { message: err.errors.alias.join(", ") });
          }
          if (err.errors.name || err.errors.leaveName) {
            setError("leaveName", {
              message: (err.errors.name || err.errors.leaveName).join(", "),
            });
          }
        }
        toast.error(err.message || "Failed to save leave type.");
      } else {
        toast.error("An unexpected error occurred while saving.");
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop overlay */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Slide-over Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col justify-between">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-blue-50/40 dark:bg-slate-950">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
              {editingLeave ? "Edit Leave Policy" : "Create New Leave"}
            </h2>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form Content */}
          <form
            id="leave-create-form"
            onSubmit={handleSubmit(onFormSubmit)}
            className="flex-1 overflow-y-auto p-6 space-y-5"
          >
            {step === 1 ? (
              <div className="space-y-4">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Select your preferred leave cycle for leave calculations
                </p>

                {/* Calendar Year option */}
                <label
                  onClick={() => setValue("leaveCycle", "calendar_year")}
                  className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-all ${
                    leaveCycle === "calendar_year"
                      ? "border-sky-500 bg-sky-50/40 dark:bg-sky-950/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300"
                  }`}
                >
                  <input
                    type="radio"
                    value="calendar_year"
                    {...register("leaveCycle")}
                    className="mt-0.5 h-4 w-4 text-sky-600 focus:ring-sky-500 border-slate-300"
                  />
                  <div>
                    <span className="block text-xs font-semibold text-slate-800 dark:text-slate-100">
                      Calendar Year
                    </span>
                    <span className="block text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      January to December timeframe
                    </span>
                  </div>
                </label>

                {/* Financial Year option */}
                <label
                  onClick={() => setValue("leaveCycle", "financial_year")}
                  className={`flex items-start gap-3 p-3.5 rounded-lg border cursor-pointer transition-all ${
                    leaveCycle === "financial_year"
                      ? "border-sky-500 bg-sky-50/40 dark:bg-sky-950/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-300"
                  }`}
                >
                  <input
                    type="radio"
                    value="financial_year"
                    {...register("leaveCycle")}
                    className="mt-0.5 h-4 w-4 text-sky-600 focus:ring-sky-500 border-slate-300"
                  />
                  <div>
                    <span className="block text-xs font-semibold text-slate-800 dark:text-slate-100">
                      Financial Year
                    </span>
                    <span className="block text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      Fiscal year, spanning from April to March
                    </span>
                  </div>
                </label>
              </div>
            ) : (
              <div className="space-y-4 text-xs">
                {/* Leave Name */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Leave Name <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="Leave Name"
                    {...register("leaveName")}
                    className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                  />
                  {errors.leaveName && (
                    <p className="text-[11px] text-red-500 mt-1">{errors.leaveName.message}</p>
                  )}
                </div>

                {/* Alias */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Alias <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="text"
                    placeholder="Alias"
                    {...register("alias")}
                    className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                  />
                  {errors.alias && (
                    <p className="text-[11px] text-red-500 mt-1">{errors.alias.message}</p>
                  )}
                </div>

                {/* Description */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Description
                  </label>
                  <Input
                    type="text"
                    placeholder="Description"
                    {...register("description")}
                    className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                  />
                </div>

                {/* Number Of Auto Allocation Leaves */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Number Of Auto Allocation Leaves <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="number"
                    step="any"
                    placeholder="Enter Number Of Leaves"
                    {...register("autoAllocationNumber")}
                    className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                  />
                  {errors.autoAllocationNumber && (
                    <p className="text-[11px] text-red-500 mt-1">
                      {errors.autoAllocationNumber.message}
                    </p>
                  )}

                  <div className="flex items-center gap-6 mt-2">
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="every_month"
                        checked={autoAllocationPeriod === "every_month"}
                        onChange={() => setValue("autoAllocationPeriod", "every_month")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>Every Month</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="every_calendar_year"
                        checked={autoAllocationPeriod === "every_calendar_year"}
                        onChange={() => setValue("autoAllocationPeriod", "every_calendar_year")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>Every Calendar Year</span>
                    </label>
                  </div>
                </div>

                {/* Carry Forward */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Carry Forward <span className="text-red-500">*</span>
                  </label>
                  <Input
                    type="number"
                    step="any"
                    placeholder="0"
                    {...register("carryForwardNumber")}
                    className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                  />
                  {errors.carryForwardNumber && (
                    <p className="text-[11px] text-red-500 mt-1">
                      {errors.carryForwardNumber.message}
                    </p>
                  )}

                  <div className="flex items-center gap-6 mt-2">
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="end_of_every_month"
                        checked={carryForwardPeriod === "end_of_every_month"}
                        onChange={() => setValue("carryForwardPeriod", "end_of_every_month")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>End Of Every Month</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="end_of_every_calendar_year"
                        checked={carryForwardPeriod === "end_of_every_calendar_year"}
                        onChange={() => setValue("carryForwardPeriod", "end_of_every_calendar_year")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>End Of Every Calendar Year</span>
                    </label>
                  </div>
                </div>

                {/* Encashment Of Leave */}
                <div>
                  <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                    Encashment Of Leave
                  </label>
                  <div className="flex items-center gap-6 mt-1.5">
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="off"
                        checked={encashment === "off"}
                        onChange={() => setValue("encashment", "off")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>Off</span>
                    </label>
                    <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 dark:text-slate-300">
                      <input
                        type="radio"
                        value="on"
                        checked={encashment === "on"}
                        onChange={() => setValue("encashment", "on")}
                        className="h-3.5 w-3.5 text-sky-600 focus:ring-sky-500"
                      />
                      <span>On</span>
                    </label>
                  </div>

                  {encashment === "on" && (
                    <div className="mt-3">
                      <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                        Encashment Limit
                      </label>
                      <Input
                        type="number"
                        step="any"
                        placeholder="Encashment Limit Count"
                        {...register("encashmentLimit")}
                        className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
                      />
                    </div>
                  )}
                </div>
              </div>
            )}
          </form>

          {/* Sticky Footer */}
          <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-blue-50/40 dark:bg-slate-950 flex items-center justify-between">
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={step === 1 || isSubmitting}
              onClick={() => setStep(1)}
              className="h-8 px-4 text-xs font-medium bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 cursor-pointer disabled:opacity-50"
            >
              Previous
            </Button>

            {step === 1 ? (
              <Button
                type="button"
                size="sm"
                onClick={() => setStep(2)}
                className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer"
              >
                Next
              </Button>
            ) : (
              <Button
                type="submit"
                form="leave-create-form"
                size="sm"
                disabled={isSubmitting}
                className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer flex items-center gap-1.5"
              >
                {isSubmitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                <span>{editingLeave ? "Update" : "Create"}</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
