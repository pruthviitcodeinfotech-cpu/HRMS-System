"use client";

import { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { HolidayTemplate } from "../types";

interface HolidayDeleteDialogProps {
  isOpen: boolean;
  onClose: () => void;
  template: HolidayTemplate | null;
  onConfirmDelete: (templateId: string) => Promise<void>;
}

export function HolidayDeleteDialog({
  isOpen,
  onClose,
  template,
  onConfirmDelete,
}: HolidayDeleteDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  if (!template) return null;

  const handleConfirm = async () => {
    setIsDeleting(true);
    try {
      await onConfirmDelete(template.id);
      // onClose is called inside onConfirmDelete on success (in page.tsx)
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isDeleting ? () => {} : onClose}
      title="Delete Holiday Template"
      size="sm"
      footer={
        <>
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isDeleting}
            className="h-8 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs disabled:opacity-50"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={handleConfirm}
            disabled={isDeleting}
            className="h-8 px-4 text-xs font-semibold bg-red-600 hover:bg-red-700 disabled:bg-red-400 text-white rounded cursor-pointer shadow-2xs"
          >
            {isDeleting ? "Deleting..." : "Delete Template"}
          </Button>
        </>
      }
    >
      <div className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
        <p>
          Are you sure you want to delete the holiday template{" "}
          <span className="font-semibold text-slate-800 dark:text-slate-200">
            &quot;{template.name}&quot;
          </span>
          ?
        </p>
        <p className="text-slate-500">
          This action cannot be undone and will remove the holiday configuration.
        </p>
      </div>
    </Modal>
  );
}
