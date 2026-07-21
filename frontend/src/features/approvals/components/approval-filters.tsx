"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ApprovalFiltersProps {
  typeFilter: string;
  searchQuery: string;
  onFilterChange: (type: string, query: string) => void;
  onClear: () => void;
}

export function ApprovalFilters({
  typeFilter,
  searchQuery,
  onFilterChange,
  onClear,
}: ApprovalFiltersProps) {
  const [localType, setLocalType] = useState<string>(typeFilter);
  const [localSearch, setLocalSearch] = useState<string>(searchQuery);

  const handleSearchSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    onFilterChange(localType, localSearch);
  };

  const handleClear = () => {
    setLocalType("Choose One");
    setLocalSearch("");
    onClear();
  };

  return (
    <form
      onSubmit={handleSearchSubmit}
      className="p-4 bg-white dark:bg-slate-900 flex flex-col sm:flex-row items-center gap-3 border-b border-slate-200 dark:border-slate-800"
    >
      {/* Type Dropdown */}
      <div className="w-full sm:w-48">
        <select
          value={localType}
          onChange={(e) => setLocalType(e.target.value)}
          className="w-full h-9 px-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-sky-500 cursor-pointer"
        >
          <option value="Choose One">Choose One</option>
          <option value="Leave">Leave</option>
          <option value="Attendance">Attendance</option>
          <option value="Overtime">Overtime</option>
          <option value="Comp Off">Comp Off</option>
          <option value="Short Leave">Short Leave</option>
        </select>
      </div>

      {/* Search Employee Name Input */}
      <div className="relative w-full sm:w-64">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
          <Search className="h-4 w-4" />
        </div>
        <input
          type="text"
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          placeholder="Write Employee Name"
          className="w-full h-9 pl-9 pr-3 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded-md text-slate-800 dark:text-slate-200 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500"
        />
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2 w-full sm:w-auto">
        <Button
          type="submit"
          size="sm"
          className="h-9 px-6 text-xs font-semibold bg-[#0B85C9] hover:bg-[#0974b0] text-white rounded-md cursor-pointer shadow-2xs"
        >
          Search
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleClear}
          className="h-9 px-4 text-xs font-medium bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 rounded-md cursor-pointer"
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
