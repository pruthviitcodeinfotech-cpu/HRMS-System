"use client";

import { useState } from "react";
import { X, Eye, EyeOff, Check, Loader2, KeyRound, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/services/api-client/error-handler";
import { useChangePassword } from "../hooks/use-profile";
import { getPasswordRequirements, isStrongPassword } from "../utils";

interface ChangePasswordDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

interface PasswordFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  visible: boolean;
  onToggleVisible: () => void;
  error?: string;
  autoFocus?: boolean;
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  visible,
  onToggleVisible,
  error,
  autoFocus,
}: PasswordFieldProps) {
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1"
      >
        {label} <span className="text-red-500">*</span>
      </label>
      <div className="relative">
        <Input
          id={id}
          type={visible ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="text-xs pr-9"
          autoFocus={autoFocus}
          autoComplete={id === "current-password" ? "current-password" : "new-password"}
          error={error}
        />
        <button
          type="button"
          onClick={onToggleVisible}
          tabIndex={-1}
          aria-label={visible ? `Hide ${label}` : `Show ${label}`}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 cursor-pointer"
        >
          {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
      </div>
    </div>
  );
}

export function ChangePasswordDialog({ isOpen, onClose }: ChangePasswordDialogProps) {
  const changePasswordMutation = useChangePassword();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [currentPasswordError, setCurrentPasswordError] = useState<string | undefined>();

  if (!isOpen) return null;

  const requirements = getPasswordRequirements(newPassword);
  const newPasswordStrong = isStrongPassword(newPassword);
  const confirmMismatch = confirmPassword.length > 0 && confirmPassword !== newPassword;
  const sameAsCurrent =
    currentPassword.length > 0 && newPassword.length > 0 && currentPassword === newPassword;

  const canSubmit =
    currentPassword.length > 0 &&
    newPasswordStrong &&
    confirmPassword.length > 0 &&
    !confirmMismatch &&
    !sameAsCurrent;

  const resetAndClose = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setShowCurrent(false);
    setShowNew(false);
    setShowConfirm(false);
    setCurrentPasswordError(undefined);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCurrentPasswordError(undefined);
    if (!canSubmit) return;

    try {
      await changePasswordMutation.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      resetAndClose();
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError?.code === "CURRENT_PASSWORD_INCORRECT") {
        setCurrentPasswordError("Incorrect current password.");
      }
      // Any other failure is already surfaced via the mutation's error toast.
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4 animate-in fade-in duration-200">
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-900 shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150"
        role="dialog"
        aria-modal="true"
        aria-labelledby="change-password-title"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
          <h2
            id="change-password-title"
            className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center gap-2"
          >
            <KeyRound className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            Change Password
          </h2>
          <button
            onClick={resetAndClose}
            aria-label="Close dialog"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          <PasswordField
            id="current-password"
            label="Current Password"
            value={currentPassword}
            onChange={(v) => {
              setCurrentPassword(v);
              setCurrentPasswordError(undefined);
            }}
            visible={showCurrent}
            onToggleVisible={() => setShowCurrent((prev) => !prev)}
            error={currentPasswordError}
            autoFocus
          />

          <div>
            <PasswordField
              id="new-password"
              label="New Password"
              value={newPassword}
              onChange={setNewPassword}
              visible={showNew}
              onToggleVisible={() => setShowNew((prev) => !prev)}
              error={sameAsCurrent ? "New password must differ from the current password." : undefined}
            />

            {/* Live strength checklist */}
            {newPassword.length > 0 && (
              <ul className="mt-2 space-y-1">
                {requirements.map((req) => (
                  <li
                    key={req.key}
                    className={`flex items-center gap-1.5 text-[11px] font-medium ${
                      req.met
                        ? "text-emerald-600 dark:text-emerald-400"
                        : "text-slate-400 dark:text-slate-500"
                    }`}
                  >
                    <Check className={`h-3 w-3 ${req.met ? "opacity-100" : "opacity-30"}`} />
                    {req.label}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <PasswordField
            id="confirm-password"
            label="Confirm New Password"
            value={confirmPassword}
            onChange={setConfirmPassword}
            visible={showConfirm}
            onToggleVisible={() => setShowConfirm((prev) => !prev)}
            error={confirmMismatch ? "Passwords do not match." : undefined}
          />

          <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-100 dark:border-amber-900 text-amber-700 dark:text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 mt-0.5 shrink-0" />
            <p className="text-[11px] leading-snug">
              For your security, changing your password will log you out of all other active
              sessions and devices.
            </p>
          </div>

          {/* Footer Buttons */}
          <div className="flex items-center justify-end space-x-3 pt-2 border-t border-slate-100 dark:border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={resetAndClose}
              disabled={changePasswordMutation.isPending}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={!canSubmit || changePasswordMutation.isPending}>
              {changePasswordMutation.isPending && (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              )}
              Change Password
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
