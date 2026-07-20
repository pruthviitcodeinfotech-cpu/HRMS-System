"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Modal } from "@/components/ui/modal";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface AddHolidayModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddHoliday: (item: { name: string; date: string; day: string }) => void;
}

export function AddHolidayModal({ isOpen, onClose, onAddHoliday }: AddHolidayModalProps) {
  const [name, setName] = useState<string>("");
  const [date, setDate] = useState<string>("");

  const handleDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDate(e.target.value);
  };

  const calculateDay = (dateStr: string): string => {
    if (!dateStr) return "";
    const dateObj = new Date(dateStr);
    if (isNaN(dateObj.getTime())) return "";
    return dateObj.toLocaleDateString("en-US", { weekday: "long" });
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Please enter holiday name");
      return;
    }
    if (!date) {
      toast.error("Please select holiday date");
      return;
    }

    const day = calculateDay(date);
    onAddHoliday({
      name: name.trim(),
      date,
      day,
    });

    setName("");
    setDate("");
    toast.success("Holiday added to template");
    onClose();
  };

  const handleCancel = () => {
    setName("");
    setDate("");
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleCancel}
      title="Add Holiday"
      size="sm"
      footer={
        <>
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={handleCancel}
            className="h-8 px-4 text-xs font-semibold bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
          >
            Cancel
          </Button>
          <Button
            size="sm"
            type="submit"
            form="add-holiday-form"
            className="h-8 px-4 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded cursor-pointer shadow-2xs"
          >
            Add Holiday
          </Button>
        </>
      }
    >
      <form id="add-holiday-form" onSubmit={handleSave} className="space-y-4 text-xs">
        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
            Holiday Name<span className="text-red-500">*</span>
          </label>
          <Input
            placeholder="e.g. Republic Day"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
            Holiday Date<span className="text-red-500">*</span>
          </label>
          <Input
            type="date"
            value={date}
            onChange={handleDateChange}
            className="h-9 text-xs bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-700"
          />
          {date && (
            <p className="text-[11px] text-sky-600 dark:text-sky-400 mt-1 font-medium">
              Day: {calculateDay(date)}
            </p>
          )}
        </div>
      </form>
    </Modal>
  );
}
