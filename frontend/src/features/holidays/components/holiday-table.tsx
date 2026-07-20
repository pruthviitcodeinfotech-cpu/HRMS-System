"use client";

import { useState, useMemo } from "react";
import { ArrowUpDown, MoreVertical, Edit2, Trash2, Eye, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { HolidayTemplate } from "../types";

interface HolidayTableProps {
  templates: HolidayTemplate[];
  isLoading?: boolean;
  totalRecords?: number;
  currentPage?: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
  onPageSizeChange?: (size: number) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
  onViewTemplate: (template: HolidayTemplate) => void;
  onEditTemplate: (template: HolidayTemplate) => void;
  onDeleteTemplate: (template: HolidayTemplate) => void;
}

export function HolidayTable({
  templates,
  isLoading = false,
  totalRecords: externalTotalRecords,
  currentPage: externalCurrentPage,
  pageSize: externalPageSize,
  onPageChange,
  onPageSizeChange,
  searchQuery: externalSearchQuery,
  onSearchChange,
  onViewTemplate,
  onEditTemplate,
  onDeleteTemplate,
}: HolidayTableProps) {
  const [internalSearchQuery, setInternalSearchQuery] = useState<string>("");
  const [activeMenuId, setActiveMenuId] = useState<string | null>(null);
  const [sortField, setSortField] = useState<
    "name" | "holidayCount" | "assignedEmployeesCount" | "createdOn" | "lastModified"
  >("name");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");
  const [internalCurrentPage, setInternalCurrentPage] = useState<number>(1);
  const [internalPageSize, setInternalPageSize] = useState<number>(10);

  const searchQuery = externalSearchQuery !== undefined ? externalSearchQuery : internalSearchQuery;
  const currentPage = externalCurrentPage !== undefined ? externalCurrentPage : internalCurrentPage;
  const pageSize = externalPageSize !== undefined ? externalPageSize : internalPageSize;

  const handleSearchChange = (val: string) => {
    if (onSearchChange) {
      onSearchChange(val);
    } else {
      setInternalSearchQuery(val);
      setInternalCurrentPage(1);
    }
  };

  const handlePageChange = (p: number) => {
    if (onPageChange) {
      onPageChange(p);
    } else {
      setInternalCurrentPage(p);
    }
  };

  const handlePageSizeChange = (sz: number) => {
    if (onPageSizeChange) {
      onPageSizeChange(sz);
    } else {
      setInternalPageSize(sz);
      setInternalCurrentPage(1);
    }
  };

  // Filter templates by search query locally if server search is not used
  const filteredTemplates = useMemo(() => {
    if (externalSearchQuery !== undefined || !searchQuery.trim()) return templates;
    const q = searchQuery.toLowerCase();
    return templates.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.createdBy.toLowerCase().includes(q) ||
        t.lastModifiedBy.toLowerCase().includes(q)
    );
  }, [templates, searchQuery, externalSearchQuery]);

  // Sort templates locally
  const sortedTemplates = useMemo(() => {
    return [...filteredTemplates].sort((a, b) => {
      let valA: string | number = a[sortField];
      let valB: string | number = b[sortField];

      if (typeof valA === "string") valA = valA.toLowerCase();
      if (typeof valB === "string") valB = valB.toLowerCase();

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });
  }, [filteredTemplates, sortField, sortOrder]);

  const handleSort = (
    field: "name" | "holidayCount" | "assignedEmployeesCount" | "createdOn" | "lastModified"
  ) => {
    if (sortField === field) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortOrder("asc");
    }
  };

  // Pagination totals
  const totalRecords =
    externalTotalRecords !== undefined ? externalTotalRecords : sortedTemplates.length;
  const totalPages = Math.ceil(totalRecords / pageSize) || 1;
  const startIndex = (currentPage - 1) * pageSize;
  const displayTemplates =
    externalTotalRecords !== undefined
      ? sortedTemplates
      : sortedTemplates.slice(startIndex, startIndex + pageSize);

  return (
    <div className="space-y-4">
      {/* Top Filter & Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search template name..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9 h-9 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700"
          />
        </div>
      </div>

      {/* Main Table Container */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-2xs overflow-hidden flex flex-col">
        <div className="w-full overflow-x-auto min-h-[350px]">
          <table className="w-full text-left border-collapse text-xs select-none">
            <thead className="bg-[#EBF5FF] dark:bg-slate-950 text-slate-700 dark:text-slate-300 font-semibold border-b border-slate-200 dark:border-slate-800">
              <tr>
                <th className="px-4 py-3 min-w-[180px]">
                  <button
                    onClick={() => handleSort("name")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Template Name</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[140px]">
                  <button
                    onClick={() => handleSort("holidayCount")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Holiday Count</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[190px]">
                  <button
                    onClick={() => handleSort("assignedEmployeesCount")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>No. Of Assigned Employee</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[220px]">
                  <button
                    onClick={() => handleSort("createdOn")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Created On</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[220px]">
                  <button
                    onClick={() => handleSort("lastModified")}
                    className="flex items-center gap-1.5 font-bold hover:text-sky-600 dark:hover:text-sky-400 transition-colors cursor-pointer"
                  >
                    <span>Last Modified</span>
                    <ArrowUpDown className="h-3 w-3 text-slate-400" />
                  </button>
                </th>

                <th className="px-4 py-3 min-w-[140px] text-center font-bold">Action</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100 dark:divide-slate-800/60">
              {isLoading ? (
                Array.from({ length: pageSize }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-32 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-12 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-16 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-40 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="h-4 w-40 bg-slate-200 dark:bg-slate-800 rounded" />
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <div className="h-6 w-20 bg-slate-200 dark:bg-slate-800 rounded mx-auto" />
                    </td>
                  </tr>
                ))
              ) : totalRecords === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                    No holiday templates found.
                  </td>
                </tr>
              ) : (
                displayTemplates.map((template) => (
                  <tr
                    key={template.id}
                    className="hover:bg-slate-50/70 dark:hover:bg-slate-800/40 transition-colors text-slate-700 dark:text-slate-300"
                  >
                    <td className="px-4 py-3.5 font-semibold text-slate-800 dark:text-slate-100">
                      {template.name}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {template.holidayCount}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {template.assignedEmployeesCount}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {template.createdOn} by {template.createdBy}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 dark:text-slate-400">
                      {template.lastModified} by {template.lastModifiedBy}
                    </td>
                    <td className="px-4 py-3.5 relative">
                      <div className="flex items-center justify-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onViewTemplate(template)}
                          className="h-7 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-50 cursor-pointer shadow-2xs"
                        >
                          View Template
                        </Button>

                        <button
                          onClick={() =>
                            setActiveMenuId(activeMenuId === template.id ? null : template.id)
                          }
                          className="h-7 w-7 flex items-center justify-center rounded border border-slate-300 dark:border-slate-700 text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer"
                        >
                          <MoreVertical className="h-4 w-4" />
                        </button>
                      </div>

                      {/* Dropdown Menu */}
                      {activeMenuId === template.id && (
                        <div className="absolute right-4 top-11 z-20 w-36 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-md shadow-lg py-1">
                          <button
                            onClick={() => {
                              onViewTemplate(template);
                              setActiveMenuId(null);
                            }}
                            className="w-full px-3 py-1.5 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer"
                          >
                            <Eye className="h-3.5 w-3.5 text-slate-400" />
                            <span>View Items</span>
                          </button>
                          <button
                            onClick={() => {
                              onEditTemplate(template);
                              setActiveMenuId(null);
                            }}
                            className="w-full px-3 py-1.5 text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2 cursor-pointer"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                            <span>Edit</span>
                          </button>
                          <button
                            onClick={() => {
                              onDeleteTemplate(template);
                              setActiveMenuId(null);
                            }}
                            className="w-full px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 flex items-center gap-2 cursor-pointer"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-red-500" />
                            <span>Delete</span>
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Server-ready Pagination Footer */}
        <div className="px-4 py-3 border-t border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-600 dark:text-slate-400">
          <div>
            Showing{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {totalRecords === 0 ? 0 : startIndex + 1}
            </span>{" "}
            to{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              {Math.min(startIndex + pageSize, totalRecords)}
            </span>{" "}
            of{" "}
            <span className="font-semibold text-slate-800 dark:text-slate-200">{totalRecords}</span>{" "}
            Results
          </div>

          <div className="flex items-center gap-3">
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="h-8 px-2 text-xs bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-700 rounded cursor-pointer focus:outline-none"
            >
              <option value={10}>10 / Page</option>
              <option value={20}>20 / Page</option>
              <option value={50}>50 / Page</option>
            </select>

            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                disabled={currentPage <= 1}
                onClick={() => handlePageChange(Math.max(1, currentPage - 1))}
                className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
              >
                Previous
              </Button>

              {Array.from({ length: totalPages }).map((_, idx) => {
                const pageNum = idx + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => handlePageChange(pageNum)}
                    className={`h-8 w-8 text-xs font-medium rounded transition-colors cursor-pointer ${
                      currentPage === pageNum
                        ? "bg-[#0B85C9] text-white"
                        : "bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}

              <Button
                variant="outline"
                size="sm"
                disabled={currentPage >= totalPages}
                onClick={() => handlePageChange(Math.min(totalPages, currentPage + 1))}
                className="h-8 px-3 text-xs bg-white dark:bg-slate-900 border-slate-300 dark:border-slate-700 cursor-pointer disabled:opacity-50"
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
