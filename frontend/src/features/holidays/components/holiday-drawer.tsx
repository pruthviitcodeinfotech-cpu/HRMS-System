"use client";

import { useEffect, useCallback } from "react";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { X, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HolidayTemplate, holidayTemplateSchema, HolidayTemplateFormValues } from "../types";

interface HolidayDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  templateToEdit?: HolidayTemplate | null;
  onSave: (data: HolidayTemplateFormValues, editId?: string) => void;
}

export function HolidayDrawer({ isOpen, onClose, templateToEdit, onSave }: HolidayDrawerProps) {
  const isEditMode = Boolean(templateToEdit);

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<HolidayTemplateFormValues>({
    resolver: zodResolver(holidayTemplateSchema),
    defaultValues: {
      name: "",
      items: [{ name: "", startDate: "", endDate: "" }],
    },
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: "items",
  });

  const handleClose = useCallback(() => {
    reset({
      name: "",
      items: [{ name: "", startDate: "", endDate: "" }],
    });
    onClose();
  }, [reset, onClose]);

  useEffect(() => {
    if (isOpen) {
      if (templateToEdit) {
        reset({
          name: templateToEdit.name,
          items: templateToEdit.items.map((item) => ({
            name: item.name,
            startDate: item.startDate,
            endDate: item.endDate,
          })),
        });
      } else {
        reset({
          name: "",
          items: [{ name: "", startDate: "", endDate: "" }],
        });
      }
    }
  }, [isOpen, templateToEdit, reset]);

  // Handle ESC key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  const onSubmitForm = (data: HolidayTemplateFormValues) => {
    onSave(data, templateToEdit?.id);
    toast.success(
      `Holiday template "${data.name}" ${isEditMode ? "updated" : "created"} successfully!`
    );
    handleClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop Overlay */}
      <div
        className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity duration-300"
        onClick={handleClose}
      />

      {/* Slide-over Drawer Panel */}
      <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-lg bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col justify-between">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-between">
            <h2 className="text-base font-semibold text-slate-800 dark:text-slate-100">
              {isEditMode ? "Edit Holiday Template" : "Create Holiday Template"}
            </h2>
            <button
              onClick={handleClose}
              className="p-1 rounded-md text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Form Body */}
          <form
            id="holiday-template-form"
            onSubmit={handleSubmit(onSubmitForm)}
            className="flex-1 overflow-y-auto p-6 space-y-6 text-xs"
          >
            {/* Template Name */}
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                Template Name<span className="text-red-500">*</span>
              </label>
              <Input
                placeholder="e.g. Holiday 2026"
                {...register("name")}
                className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700 focus:ring-[#0B85C9]"
              />
              {errors.name && (
                <p className="text-red-500 text-[11px] mt-1">{errors.name.message}</p>
              )}
            </div>

            {/* Holiday Items Section */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-xs font-semibold text-slate-800 dark:text-slate-200">
                  Holidays List<span className="text-red-500">*</span>
                </label>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => append({ name: "", startDate: "", endDate: "" })}
                  className="h-7 px-2.5 text-[11px] bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-sky-600 hover:text-sky-700 dark:text-sky-400 cursor-pointer shadow-2xs"
                >
                  <Plus className="h-3.5 w-3.5 mr-1" />
                  Add Holiday Item
                </Button>
              </div>

              {errors.items?.root && (
                <p className="text-red-500 text-[11px]">{errors.items.root.message}</p>
              )}

              <div className="space-y-4">
                {fields.map((field, index) => (
                  <div
                    key={field.id}
                    className="p-3.5 bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-md space-y-3 relative group"
                  >
                    <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2">
                      <span className="font-semibold text-slate-700 dark:text-slate-300 text-[11px]">
                        Holiday #{index + 1}
                      </span>
                      {fields.length > 1 && (
                        <button
                          type="button"
                          onClick={() => remove(index)}
                          className="text-slate-400 hover:text-red-500 transition-colors p-1 cursor-pointer"
                          title="Remove holiday item"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>

                    {/* Holiday Name */}
                    <div>
                      <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                        Holiday Name<span className="text-red-500">*</span>
                      </label>
                      <Input
                        placeholder="e.g. Republic Day"
                        {...register(`items.${index}.name` as const)}
                        className="h-8 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                      />
                      {errors.items?.[index]?.name && (
                        <p className="text-red-500 text-[10px] mt-1">
                          {errors.items[index]?.name?.message}
                        </p>
                      )}
                    </div>

                    {/* Date Inputs */}
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                          Start Date<span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="date"
                          {...register(`items.${index}.startDate` as const)}
                          className="h-8 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                        />
                        {errors.items?.[index]?.startDate && (
                          <p className="text-red-500 text-[10px] mt-1">
                            {errors.items[index]?.startDate?.message}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-[11px] font-medium text-slate-600 dark:text-slate-400 mb-1">
                          End Date<span className="text-red-500">*</span>
                        </label>
                        <Input
                          type="date"
                          {...register(`items.${index}.endDate` as const)}
                          className="h-8 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
                        />
                        {errors.items?.[index]?.endDate && (
                          <p className="text-red-500 text-[10px] mt-1">
                            {errors.items[index]?.endDate?.message}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </form>

          {/* Sticky Footer */}
          <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-[#EBF5FF] dark:bg-slate-950 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={handleClose}
              className="text-xs font-medium text-sky-600 dark:text-sky-400 hover:text-sky-700 cursor-pointer px-3 py-1.5"
            >
              Close
            </button>
            <Button
              type="submit"
              form="holiday-template-form"
              size="sm"
              className="h-8 px-5 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded shadow-2xs cursor-pointer"
            >
              {isEditMode ? "Save Changes" : "Create Template"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
