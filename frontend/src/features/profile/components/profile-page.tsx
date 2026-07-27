"use client";

import { useState } from "react";
import {
  Mail,
  Phone,
  Building2,
  ShieldCheck,
  Calendar,
  Loader2,
  AlertCircle,
  RefreshCw,
  Pencil,
  X,
  Check,
  CheckCircle2,
  XCircle,
  Briefcase,
  Hash,
  KeyRound,
  Eye,
  EyeOff,
  Camera,
  User as UserIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { usePermission } from "@/features/auth/hooks";
import { useSettings } from "@/features/settings";
import { ChangePasswordDialog } from "./change-password-dialog";
import { useProfile, useUpdateProfile, useUploadProfilePhoto } from "../hooks/use-profile";

type TabId = "user" | "organization" | "roles";

const TABS: { id: TabId; label: string }[] = [
  { id: "user", label: "User Details" },
  { id: "organization", label: "Organization Details" },
  { id: "roles", label: "Roles" },
];

function FieldCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
      <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
        <Icon className="h-3.5 w-3.5" />
        <span className="text-[11px] font-semibold text-slate-500">{label}</span>
      </div>
      <p className="font-semibold text-slate-800 dark:text-slate-200 truncate">{value ?? "-"}</p>
    </div>
  );
}

function MaskedFieldCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string | null | undefined;
}) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
      <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
        <Icon className="h-3.5 w-3.5" />
        <span className="text-[11px] font-semibold text-slate-500">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <p className="font-semibold text-slate-800 dark:text-slate-200 tracking-widest">
          {value ? (revealed ? value : "•".repeat(Math.min(value.length, 10))) : "-"}
        </p>
        {value && (
          <button
            type="button"
            onClick={() => setRevealed((prev) => !prev)}
            aria-label={revealed ? `Hide ${label}` : `Show ${label}`}
            className="text-amber-500 hover:text-amber-600 cursor-pointer"
          >
            {revealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          </button>
        )}
      </div>
    </div>
  );
}

export function ProfilePage() {
  const { data: profile, isLoading, isError, refetch } = useProfile();
  const updateProfileMutation = useUpdateProfile();
  const uploadPhotoMutation = useUploadProfilePhoto();
  const canReadSettings = usePermission("settings", "read");
  const { data: orgSettings } = useSettings({ enabled: canReadSettings });

  const [activeTab, setActiveTab] = useState<TabId>("user");
  const [isEditing, setIsEditing] = useState(false);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  const [mobileCountryCode, setMobileCountryCode] = useState("+91");
  const [mobileNumber, setMobileNumber] = useState("");

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      uploadPhotoMutation.mutate(file);
    }
  };

  const handleEdit = () => {
    if (profile) {
      setMobileCountryCode(profile.mobile_country_code);
      setMobileNumber(profile.mobile_number);
    }
    setIsEditing(true);
  };

  const handleCancel = () => {
    if (profile) {
      setMobileCountryCode(profile.mobile_country_code);
      setMobileNumber(profile.mobile_number);
    }
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!profile) return;
    const payload: { mobile_country_code?: string; mobile_number?: string } = {};
    if (mobileCountryCode.trim() !== profile.mobile_country_code) {
      payload.mobile_country_code = mobileCountryCode.trim();
    }
    if (mobileNumber.trim() !== profile.mobile_number) {
      payload.mobile_number = mobileNumber.trim();
    }

    if (Object.keys(payload).length === 0) {
      setIsEditing(false);
      return;
    }

    try {
      await updateProfileMutation.mutateAsync(payload);
      setIsEditing(false);
    } catch {
      // Error toast is handled in the mutation hook
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-24 space-y-3">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
        <p className="text-xs text-slate-500 font-medium">Loading your profile...</p>
      </div>
    );
  }

  if (isError || !profile) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <div className="h-12 w-12 rounded-full bg-red-50 dark:bg-red-950/40 text-red-600 dark:text-red-400 flex items-center justify-center mb-4">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-1">
          Failed to Load Profile
        </h3>
        <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mb-5">
          An unexpected error occurred while fetching your profile. Please try again.
        </p>
        <button
          type="button"
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          <RefreshCw className="h-4 w-4" />
          Retry Loading
        </button>
      </div>
    );
  }

  const org = profile.organization;
  const branch = profile.branch;
  const employee = profile.employee;

  return (
    <div className="w-full space-y-4">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-xl bg-linear-to-r from-slate-700 to-blue-500 text-white p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="relative group shrink-0">
            <div className="h-16 w-16 rounded-full bg-white/20 text-white flex items-center justify-center font-bold text-xl overflow-hidden border-2 border-white/40 shadow-inner">
              {profile.profile_photo_url ? (
                <img
                  src={profile.profile_photo_url}
                  alt={profile.name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <span>{profile.name.charAt(0).toUpperCase()}</span>
              )}
            </div>
            <label
              htmlFor="profile-photo-upload"
              className="absolute bottom-0 right-0 p-1.5 rounded-full bg-blue-600 text-white hover:bg-blue-700 cursor-pointer shadow-md transition-transform group-hover:scale-110"
              title="Upload profile photo"
            >
              <Camera className="h-3.5 w-3.5" />
              <input
                id="profile-photo-upload"
                type="file"
                accept="image/png,image/jpeg,image/jpg"
                onChange={handlePhotoChange}
                className="hidden"
                disabled={uploadPhotoMutation.isPending}
              />
            </label>
          </div>

          <div>
            <h1 className="text-xl font-bold">{profile.name}</h1>
            <p className="text-sm text-white/80">{org.org_name}</p>
            {(branch?.address || branch?.city) && (
              <p className="text-xs text-white/70 mt-0.5">
                {[branch?.address, branch?.city, branch?.state, branch?.country]
                  .filter(Boolean)
                  .join(", ")}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Main Card */}
      <div className="bg-white dark:bg-slate-950 rounded-xl border border-slate-200/80 dark:border-slate-800 shadow-sm overflow-hidden">
        {/* Tabs + Edit action */}
        <div className="flex items-center justify-between px-6 pt-4 border-b border-slate-200/80 dark:border-slate-800">
          <div role="tablist" aria-label="Profile sections" className="flex items-center gap-6">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                role="tab"
                type="button"
                aria-selected={activeTab === tab.id}
                onClick={() => {
                  setActiveTab(tab.id);
                  setIsEditing(false);
                }}
                className={`pb-3 text-sm font-medium border-b-2 transition-colors cursor-pointer ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600 dark:text-blue-400"
                    : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "user" && (
            <div className="pb-3">
              {isEditing ? (
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleCancel}
                    disabled={updateProfileMutation.isPending}
                  >
                    <X className="h-3.5 w-3.5 mr-1" />
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={handleSave}
                    disabled={updateProfileMutation.isPending}
                  >
                    {updateProfileMutation.isPending ? (
                      <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                    ) : (
                      <Check className="h-3.5 w-3.5 mr-1" />
                    )}
                    Save
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setIsChangePasswordOpen(true)}
                  >
                    <KeyRound className="h-3.5 w-3.5 mr-1.5" />
                    Change Password
                  </Button>
                  <Button type="button" variant="outline" size="sm" onClick={handleEdit}>
                    <Pencil className="h-3.5 w-3.5 mr-1.5" />
                    Edit
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === "user" && (
            <div className="space-y-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                User Information
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FieldCard icon={Mail} label="Email" value={profile.email} />

                <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                  <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                    <Phone className="h-3.5 w-3.5" />
                    <span className="text-[11px] font-semibold text-slate-500">Mobile Number</span>
                  </div>
                  {isEditing ? (
                    <div className="flex items-center gap-2 mt-1">
                      <Input
                        value={mobileCountryCode}
                        onChange={(e) => setMobileCountryCode(e.target.value)}
                        className="w-16 h-9 text-sm"
                        maxLength={10}
                        aria-label="Mobile country code"
                      />
                      <Input
                        value={mobileNumber}
                        onChange={(e) => setMobileNumber(e.target.value)}
                        className="h-9 text-sm"
                        maxLength={20}
                        aria-label="Mobile number"
                      />
                    </div>
                  ) : (
                    <p className="font-semibold text-slate-800 dark:text-slate-200">
                      <span className="text-blue-600 dark:text-blue-400">
                        {profile.mobile_country_code}
                      </span>{" "}
                      {profile.mobile_number}
                    </p>
                  )}
                </div>

                <FieldCard icon={UserIcon} label="Full Name" value={profile.name} />
                <FieldCard
                  icon={Calendar}
                  label="Last Login"
                  value={
                    profile.last_login_at ? new Date(profile.last_login_at).toLocaleString() : "-"
                  }
                />
              </div>
            </div>
          )}

          {activeTab === "organization" && (
            <div className="space-y-6">
              <div className="space-y-4">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Organization Information
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FieldCard icon={Building2} label="Organization Name" value={org.org_name} />
                  <FieldCard icon={Mail} label="Contact Email" value={org.contact_email} />
                  <FieldCard icon={Phone} label="Contact Phone" value={org.contact_phone} />
                  <div className="p-3 border border-slate-100 dark:border-slate-800 rounded-lg">
                    <div className="flex items-center space-x-1.5 text-slate-400 mb-1">
                      <ShieldCheck className="h-3.5 w-3.5" />
                      <span className="text-[11px] font-semibold text-slate-500">Status</span>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        org.is_active
                          ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                          : "bg-slate-200 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                      }`}
                    >
                      {org.is_active ? (
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                      ) : (
                        <XCircle className="h-3 w-3 mr-1" />
                      )}
                      {org.is_active ? "Active" : "Inactive"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-4 pt-6 border-t border-slate-100 dark:border-slate-900">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Organization IDs
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FieldCard icon={Hash} label="HO ID" value={org.org_code} />
                  <FieldCard icon={Hash} label="Org ID" value={org.org_id} />
                  {canReadSettings && (
                    <>
                      <MaskedFieldCard icon={KeyRound} label="Sync Code" value={orgSettings?.organization?.sync_code} />
                      <MaskedFieldCard icon={KeyRound} label="Pass Code" value={orgSettings?.organization?.pass_code} />
                    </>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === "roles" && (
            <div className="space-y-4">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Role &amp; Access
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FieldCard
                  icon={ShieldCheck}
                  label="Assigned Role"
                  value={profile.is_super_admin ? "Super Admin" : profile.role_name || "Not Assigned"}
                />
                {employee && (
                  <>
                    <FieldCard icon={Briefcase} label="Designation" value={employee.designation_name} />
                    <FieldCard icon={Building2} label="Department" value={employee.department_name} />
                    <FieldCard icon={UserIcon} label="Employee Code" value={employee.employee_code} />
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      <ChangePasswordDialog
        isOpen={isChangePasswordOpen}
        onClose={() => setIsChangePasswordOpen(false)}
      />
    </div>
  );
}
