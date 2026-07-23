"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, ShieldCheck, UserCheck, UserX, Trash2, X, ChevronDown, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRightsTemplates } from "../hooks/use-rights-templates";

interface BaseDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => void;
  userName?: string;
  isLoading?: boolean;
}

/* =========================================================
   1. DELETE CONFIRMATION DIALOG
   ========================================================= */
export function DeleteUserDialog({
  isOpen,
  onClose,
  onConfirm,
  userName = "User",
  isLoading = false,
}: BaseDialogProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
      >
        <div className="flex items-start space-x-3">
          <div className="p-3 bg-red-100 text-red-600 dark:bg-red-950 dark:text-red-400 rounded-full shrink-0">
            <Trash2 className="h-6 w-6" />
          </div>
          <div>
            <h3 id="delete-dialog-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
              Delete User?
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              This action cannot be undone. Are you sure you want to soft delete{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">{userName}</span>?
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="text-xs font-semibold h-8 px-3 cursor-pointer"
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={isLoading}
            onClick={() => {
              if (onConfirm) onConfirm();
            }}
            className="bg-red-600 hover:bg-red-700 text-white text-xs font-semibold h-8 px-4 shadow-2xs cursor-pointer flex items-center space-x-1.5"
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Delete</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   2. ACTIVATE / DEACTIVATE DIALOG
   ========================================================= */
interface ActivateDeactivateProps extends BaseDialogProps {
  actionType: "activate" | "deactivate";
}

export function ToggleUserStatusDialog({
  isOpen,
  onClose,
  onConfirm,
  userName = "User",
  actionType,
  isLoading = false,
}: ActivateDeactivateProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  const isActivate = actionType === "activate";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="toggle-dialog-title"
      >
        <div className="flex items-start space-x-3">
          <div
            className={`p-3 rounded-full shrink-0 ${
              isActivate
                ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-950 dark:text-emerald-400"
                : "bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400"
            }`}
          >
            {isActivate ? <UserCheck className="h-6 w-6" /> : <UserX className="h-6 w-6" />}
          </div>
          <div>
            <h3 id="toggle-dialog-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
              {isActivate ? "Activate User?" : "Deactivate User?"}
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Are you sure you want to {isActivate ? "activate" : "deactivate"}{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">{userName}</span>'s account?
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="text-xs font-semibold h-8 px-3 cursor-pointer"
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={isLoading}
            onClick={() => {
              if (onConfirm) onConfirm();
            }}
            className={`text-white text-xs font-semibold h-8 px-4 shadow-2xs cursor-pointer flex items-center space-x-1.5 ${
              isActivate ? "bg-emerald-600 hover:bg-emerald-700" : "bg-amber-600 hover:bg-amber-700"
            }`}
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Confirm</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   3. ASSIGN RIGHTS TEMPLATE DIALOG
   ========================================================= */
interface AssignTemplateProps extends BaseDialogProps {
  currentTemplate?: string;
  onAssignTemplate?: (templateId: number) => void;
}

export function AssignTemplateDialog({
  isOpen,
  onClose,
  onAssignTemplate,
  userName = "User",
  currentTemplate = "-",
  isLoading = false,
}: AssignTemplateProps) {
  // Live Rights Templates lookup from backend API
  const { data: templateData, isLoading: isTemplatesLoading } = useRightsTemplates({});
  const availableTemplates = templateData?.items || [];

  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);

  useEffect(() => {
    if (availableTemplates.length > 0 && !selectedTemplateId) {
      setSelectedTemplateId(availableTemplates[0].id);
    }
  }, [availableTemplates, selectedTemplateId]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 text-xs"
        role="dialog"
        aria-modal="true"
        aria-labelledby="assign-dialog-title"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <div className="flex items-center space-x-2">
            <ShieldCheck className="h-5 w-5 text-blue-600" />
            <h3 id="assign-dialog-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
              Assign Rights Template
            </h3>
          </div>
          <button
            onClick={onClose}
            disabled={isLoading}
            aria-label="Close dialog"
            className="p-1 rounded-lg text-slate-400 hover:text-slate-600 cursor-pointer disabled:opacity-50"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div className="p-3 bg-slate-50 dark:bg-slate-800/60 rounded-lg border border-slate-100 dark:border-slate-800 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500 font-semibold">User:</span>
              <span className="font-bold text-slate-800 dark:text-slate-100">{userName}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500 font-semibold">Current Template:</span>
              <span className="font-semibold text-blue-600 dark:text-blue-400">{currentTemplate}</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Select Rights Template <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <select
                value={selectedTemplateId || ""}
                onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
                disabled={isTemplatesLoading}
                className="w-full appearance-none bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-md px-3 py-2 pr-8 text-xs font-medium text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 h-9 cursor-pointer disabled:opacity-50"
              >
                {availableTemplates.map((tmpl) => (
                  <option key={tmpl.id} value={tmpl.id}>
                    {tmpl.name}
                  </option>
                ))}
              </select>
              {isTemplatesLoading ? (
                <Loader2 className="h-3.5 w-3.5 text-slate-400 absolute right-2.5 top-3 animate-spin" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5 text-slate-500 absolute right-2.5 top-3 pointer-events-none" />
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 px-6 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="text-xs font-semibold h-8 px-3 cursor-pointer"
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={isLoading || !selectedTemplateId}
            onClick={() => {
              if (onAssignTemplate && selectedTemplateId) {
                onAssignTemplate(selectedTemplateId);
              }
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold h-8 px-4 shadow-2xs cursor-pointer flex items-center space-x-1.5"
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Assign</span>
          </Button>
        </div>
      </div>
    </div>
  );
}

/* =========================================================
   4. REMOVE TEMPLATE DIALOG
   ========================================================= */
export function RemoveTemplateDialog({
  isOpen,
  onClose,
  onConfirm,
  userName = "User",
  isLoading = false,
}: BaseDialogProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen && !isLoading) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 p-6 space-y-4 animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="remove-dialog-title"
      >
        <div className="flex items-start space-x-3">
          <div className="p-3 bg-amber-100 text-amber-600 dark:bg-amber-950 dark:text-amber-400 rounded-full shrink-0">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <h3 id="remove-dialog-title" className="text-base font-bold text-slate-800 dark:text-slate-100">
              Remove Template?
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Remove assigned template from{" "}
              <span className="font-bold text-slate-800 dark:text-slate-200">{userName}</span>?
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
            className="text-xs font-semibold h-8 px-3 cursor-pointer"
          >
            Cancel
          </Button>
          <Button
            type="button"
            disabled={isLoading}
            onClick={() => {
              if (onConfirm) onConfirm();
            }}
            className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold h-8 px-4 shadow-2xs cursor-pointer flex items-center space-x-1.5"
          >
            {isLoading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Remove</span>
          </Button>
        </div>
      </div>
    </div>
  );
}
