"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { ApprovalRequest } from "../types";

const remarksSchema = (isReject: boolean) =>
  z.object({
    remarks: isReject
      ? z
          .string()
          .trim()
          .min(3, "Remarks are required for rejection (minimum 3 characters).")
      : z.string().trim().optional(),
  });

export type RemarksFormValues = z.infer<ReturnType<typeof remarksSchema>>;

interface ApprovalRemarksDialogProps {
  isOpen: boolean;
  onClose: () => void;
  request: ApprovalRequest | null;
  actionType: "approve" | "reject";
  onSubmit: (remarks: string) => void;
}

export function ApprovalRemarksDialog({
  isOpen,
  onClose,
  request,
  actionType,
  onSubmit,
}: ApprovalRemarksDialogProps) {
  const isReject = actionType === "reject";

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RemarksFormValues>({
    resolver: zodResolver(remarksSchema(isReject)),
    defaultValues: {
      remarks: "",
    },
  });

  useEffect(() => {
    if (isOpen) {
      reset({ remarks: "" });
    }
  }, [isOpen, reset]);

  if (!request) return null;

  const handleFormSubmit = (data: RemarksFormValues) => {
    onSubmit(data.remarks || "");
    onClose();
  };

  const title = isReject ? "Reject Approval Request" : "Approve Request";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      size="md"
      footer={
        <>
          <Button variant="outline" size="sm" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant={isReject ? "destructive" : "primary"}
            size="sm"
            onClick={handleSubmit(handleFormSubmit)}
            disabled={isSubmitting}
            className={!isReject ? "bg-[#0B85C9] hover:bg-[#0974b0] text-white" : ""}
          >
            {isReject ? "Reject Request" : "Approve Request"}
          </Button>
        </>
      }
    >
      <div className="space-y-4 text-xs text-slate-700 dark:text-slate-300">
        {/* Summary Header */}
        <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-lg border border-slate-200 dark:border-slate-700 space-y-1">
          <div className="flex justify-between">
            <span className="text-slate-500">Employee:</span>
            <span className="font-semibold text-slate-800 dark:text-slate-100">
              {request.employeeCode} - {request.employeeName}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Request Type:</span>
            <span className="font-medium text-slate-700 dark:text-slate-300">
              {request.type} ({request.subtype})
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">Submitted Date:</span>
            <span>{request.submittedDate}</span>
          </div>
        </div>

        {/* Remarks Input */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
            {isReject ? "Rejection Reason / Remarks *" : "Remarks (Optional)"}
          </label>
          <textarea
            {...register("remarks")}
            rows={3}
            placeholder={
              isReject
                ? "Enter reason for rejecting this request..."
                : "Enter optional approval remarks..."
            }
            className={`w-full p-2.5 text-xs bg-white dark:bg-slate-950 border rounded-md focus:outline-none focus:ring-2 ${
              errors.remarks
                ? "border-red-500 focus:ring-red-400"
                : "border-slate-300 dark:border-slate-700 focus:ring-sky-500"
            }`}
          />
          {errors.remarks && (
            <p className="text-[11px] text-red-500 font-medium">{errors.remarks.message}</p>
          )}
        </div>
      </div>
    </Modal>
  );
}
