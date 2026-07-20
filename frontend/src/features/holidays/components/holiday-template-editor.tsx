"use client";

import { useState } from "react";
import { ChevronLeft, ArrowUpDown, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AddHolidayModal } from "./add-holiday-modal";
import { HolidayTemplate, HolidayItem } from "../types";

interface HolidayTemplateEditorProps {
  onBack: () => void;
  onSave: (templateName: string, items: HolidayItem[]) => void;
  initialTemplate?: HolidayTemplate | null;
  existingTemplateNames?: string[];
}

export function HolidayTemplateEditor({
  onBack,
  onSave,
  initialTemplate,
  existingTemplateNames = [],
}: HolidayTemplateEditorProps) {
  const [templateName, setTemplateName] = useState<string>(initialTemplate?.name || "");
  const [holidayItems, setHolidayItems] = useState<HolidayItem[]>(initialTemplate?.items || []);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);

  const [sortField, setSortField] = useState<"date" | "day" | "name">("date");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const trimmedName = templateName.trim();
  const isNameDuplicate = existingTemplateNames.some(
    (name) =>
      name.toLowerCase() === trimmedName.toLowerCase() &&
      name.toLowerCase() !== initialTemplate?.name.toLowerCase()
  );

  const handleAddHoliday = (item: { name: string; date: string; day: string }) => {
    const newItem: HolidayItem = {
      id: `h_${Date.now()}`,
      name: item.name,
      startDate: item.date,
      endDate: item.date,
      durationDays: 1,
    };
    setHolidayItems((prev) => [...prev, newItem]);
  };

  const handleRemoveHoliday = (id?: string, index?: number) => {
    setHolidayItems((prev) => prev.filter((item, idx) => (id ? item.id !== id : idx !== index)));
    toast.info("Holiday removed");
  };

  const handleSort = (field: "date" | "day" | "name") => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  const sortedItems = [...holidayItems].sort((a, b) => {
    let valA = "";
    let valB = "";

    if (sortField === "date") {
      valA = a.startDate || "";
      valB = b.startDate || "";
    } else if (sortField === "day") {
      valA = a.startDate
        ? new Date(a.startDate).toLocaleDateString("en-US", { weekday: "long" })
        : "";
      valB = b.startDate
        ? new Date(b.startDate).toLocaleDateString("en-US", { weekday: "long" })
        : "";
    } else {
      valA = a.name || "";
      valB = b.name || "";
    }

    valA = valA.toLowerCase();
    valB = valB.toLowerCase();

    if (valA < valB) return sortOrder === "asc" ? -1 : 1;
    if (valA > valB) return sortOrder === "asc" ? 1 : -1;
    return 0;
  });

  const handleSaveDetails = () => {
    if (!trimmedName) {
      toast.error("Please enter a template name");
      return;
    }
    if (isNameDuplicate) {
      toast.error(`A holiday template named "${trimmedName}" already exists.`);
      return;
    }
    if (holidayItems.length === 0) {
      toast.error("Please add at least one holiday to the template");
      return;
    }

    onSave(trimmedName, holidayItems);
  };

  return (
    <div className="space-y-6">
      {/* Top Header with Back Navigation */}
      <div className="flex items-center gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-slate-700 dark:text-slate-200 hover:text-[#0B85C9] font-semibold text-base transition-colors cursor-pointer"
        >
          <ChevronLeft className="h-5 w-5 text-slate-500" />
          <span>{initialTemplate ? "Edit Template" : "Create Template"}</span>
        </button>
      </div>

      {/* Main Form Box */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs p-6 space-y-6">
        {/* Top Controls: Template Name & Add Holiday Button */}
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div className="flex flex-col gap-1 w-full sm:w-auto">
            <div className="flex items-center gap-3">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 whitespace-nowrap">
                Template Name<span className="text-red-500">*</span>
              </label>
              <Input
                placeholder="Write Template Name Here"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                className={`h-9 w-full sm:w-72 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700 focus:ring-[#0B85C9] ${
                  isNameDuplicate ? "border-red-500 focus:ring-red-500" : ""
                }`}
              />
            </div>
            {isNameDuplicate && (
              <p className="text-[11px] text-red-500 font-medium ml-[110px]">
                Template name already exists. Please choose a different name.
              </p>
            )}
          </div>

          <Button
            size="sm"
            onClick={() => setIsAddModalOpen(true)}
            className="h-9 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs self-start"
          >
            Add Holiday
          </Button>
        </div>

        {/* Holiday Items Table Container */}
        <div className="border border-slate-200 dark:border-slate-800 rounded-lg overflow-hidden">
          <table className="w-full text-left border-collapse text-xs select-none">
            <thead>
              <tr className="bg-slate-50/70 dark:bg-slate-950/60 border-b border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                <th
                  onClick={() => handleSort("date")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="flex items-center gap-1">
                    <span>Date</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort("day")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="flex items-center gap-1">
                    <span>Day</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort("name")}
                  className="px-4 py-3 cursor-pointer hover:bg-slate-100/50 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <div className="flex items-center gap-1">
                    <span>Name</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </div>
                </th>
                <th className="px-4 py-3 text-center w-24">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800 text-slate-700 dark:text-slate-200">
              {sortedItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-400 dark:text-slate-500">
                    No holidays added yet. Click &quot;Add Holiday&quot; to begin.
                  </td>
                </tr>
              ) : (
                sortedItems.map((item, index) => {
                  const dayName = item.startDate
                    ? new Date(item.startDate).toLocaleDateString("en-US", { weekday: "long" })
                    : "-";

                  return (
                    <tr
                      key={item.id || index}
                      className="hover:bg-slate-50/50 dark:hover:bg-slate-900/40 transition-colors"
                    >
                      <td className="px-4 py-3 font-medium">{item.startDate}</td>
                      <td className="px-4 py-3 text-slate-500 dark:text-slate-400">{dayName}</td>
                      <td className="px-4 py-3 font-semibold text-slate-800 dark:text-slate-100">
                        {item.name}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => handleRemoveHoliday(item.id, index)}
                          className="p-1 text-slate-400 hover:text-red-500 transition-colors cursor-pointer rounded"
                          title="Delete Holiday"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Bottom Save Action Button */}
        <div className="flex justify-end pt-4">
          <Button
            size="sm"
            onClick={handleSaveDetails}
            disabled={isNameDuplicate}
            className="h-9 px-6 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] disabled:bg-slate-400 text-white rounded cursor-pointer shadow-2xs"
          >
            Save Details
          </Button>
        </div>
      </div>

      {/* Add Holiday Modal */}
      <AddHolidayModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAddHoliday={handleAddHoliday}
      />
    </div>
  );
}
