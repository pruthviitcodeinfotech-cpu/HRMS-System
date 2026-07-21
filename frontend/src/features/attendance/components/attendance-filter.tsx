"use client";

import React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Calendar as CalendarIcon, Search, FileSpreadsheet, FileText, X } from "lucide-react";
import { AttendanceFilter } from "../types/attendance";

const filterSchema = z.object({
  fromDate: z.string().min(1, "From Date is required"),
  toDate: z.string().min(1, "To Date is required"),
  branchId: z.string().optional(),
});

type FilterFormValues = z.infer<typeof filterSchema>;

interface AttendanceFilterProps {
  onSearch: (filter: AttendanceFilter) => void;
  onReset?: () => void;
  onExportExcel?: () => void;
  onExportPdf?: () => void;
}

export const AttendanceFilterBar: React.FC<AttendanceFilterProps> = ({
  onSearch,
  onReset,
  onExportExcel,
  onExportPdf,
}) => {
  // Default to July 1, 2026 -> July 21, 2026 as seen in Petpooja reference image
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
  } = useForm<FilterFormValues>({
    resolver: zodResolver(filterSchema),
    defaultValues: {
      fromDate: "2026-07-01",
      toDate: "2026-07-21",
      branchId: "",
    },
  });

  const fromDateValue = watch("fromDate");
  const toDateValue = watch("toDate");
  const branchIdValue = watch("branchId");

  const onSubmit = (data: FilterFormValues) => {
    onSearch({
      fromDate: data.fromDate,
      toDate: data.toDate,
      branchId: data.branchId || "",
    });
  };

  const handleClear = () => {
    reset({
      fromDate: "2026-07-01",
      toDate: "2026-07-21",
      branchId: "",
    });
    if (onReset) onReset();
  };

  return (
    <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 mb-6">
      {/* Left Filter Form */}
      <form
        onSubmit={handleSubmit(onSubmit)}
        className="flex flex-wrap items-center gap-3"
      >
        {/* Date Range Picker Container */}
        <div className="flex items-center space-x-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-1.5 shadow-xs">
          <CalendarIcon className="h-4 w-4 text-slate-400 shrink-0" />
          <input
            type="date"
            {...register("fromDate")}
            className="text-xs font-medium bg-transparent border-none text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
          />
          <span className="text-slate-400 text-xs font-bold">→</span>
          <input
            type="date"
            {...register("toDate")}
            className="text-xs font-medium bg-transparent border-none text-slate-700 dark:text-slate-200 focus:outline-hidden cursor-pointer"
          />
          {(fromDateValue || toDateValue) && (
            <button
              type="button"
              onClick={() => {
                setValue("fromDate", "");
                setValue("toDate", "");
              }}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-0.5"
              title="Clear Dates"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Branch Dropdown */}
        <div className="relative min-w-[200px]">
          <select
            {...register("branchId")}
            className="w-full text-xs font-medium bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200 rounded-lg px-3 py-2 pr-8 shadow-xs focus:outline-hidden focus:ring-2 focus:ring-blue-500/20 cursor-pointer appearance-none"
          >
            <option value="">Choose Branch</option>
            <option value="main">Itcode Infotech (116478)</option>
            <option value="surat">Surat Head Office</option>
            <option value="ahmedabad">Ahmedabad Branch</option>
            <option value="mumbai">Mumbai Corporate</option>
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2.5 text-slate-400">
            <svg className="h-4 w-4 fill-current" viewBox="0 0 20 20">
              <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
            </svg>
          </div>
        </div>

        {/* Search Button */}
        <button
          type="submit"
          className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 active:bg-blue-800 rounded-lg shadow-xs transition-colors cursor-pointer"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search</span>
        </button>

        {branchIdValue && (
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 underline cursor-pointer"
          >
            Reset
          </button>
        )}
      </form>

      {/* Right Header Actions */}
      <div className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onExportExcel}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer active:scale-95"
          title="Export Attendance to Excel"
        >
          <FileSpreadsheet className="h-3.5 w-3.5 text-emerald-600" />
          <span>Export Excel</span>
        </button>
        <button
          type="button"
          onClick={onExportPdf}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg shadow-xs hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer active:scale-95"
          title="Export Attendance to PDF"
        >
          <FileText className="h-3.5 w-3.5 text-rose-600" />
          <span>Export PDF</span>
        </button>
      </div>
    </div>
  );
};
