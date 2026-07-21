"use client";

import React from "react";
import { ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { AttendanceRecord, SortField, SortOrder } from "../types/attendance";
import { AttendanceStatusBadge } from "./attendance-status-badge";

interface AttendanceTableProps {
  records: AttendanceRecord[];
  sortField?: SortField;
  sortOrder?: SortOrder;
  onSort?: (field: SortField) => void;
}

export const AttendanceTable: React.FC<AttendanceTableProps> = ({
  records,
  sortField,
  sortOrder,
  onSort,
}) => {
  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="h-3 w-3 text-slate-400 opacity-60 ml-1 shrink-0" />;
    }
    return sortOrder === "asc" ? (
      <ArrowUp className="h-3 w-3 text-blue-600 dark:text-blue-400 ml-1 shrink-0" />
    ) : (
      <ArrowDown className="h-3 w-3 text-blue-600 dark:text-blue-400 ml-1 shrink-0" />
    );
  };

  return (
    <div className="w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-t-xl overflow-hidden shadow-xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse min-w-[1000px]">
          {/* Sticky Table Header */}
          <thead className="bg-sky-50/70 dark:bg-slate-800/80 text-slate-700 dark:text-slate-200 font-semibold sticky top-0 z-10 border-b border-slate-200 dark:border-slate-800">
            <tr>
              <th
                scope="col"
                onClick={() => onSort && onSort("employeeId")}
                className="py-3 px-4 cursor-pointer hover:bg-sky-100/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Employee ID</span>
                  {renderSortIcon("employeeId")}
                </div>
              </th>
              <th
                scope="col"
                onClick={() => onSort && onSort("employeeName")}
                className="py-3 px-4 cursor-pointer hover:bg-sky-100/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Employee Name</span>
                  {renderSortIcon("employeeName")}
                </div>
              </th>
              <th
                scope="col"
                onClick={() => onSort && onSort("department")}
                className="py-3 px-4 cursor-pointer hover:bg-sky-100/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Department</span>
                  {renderSortIcon("department")}
                </div>
              </th>
              <th
                scope="col"
                onClick={() => onSort && onSort("designation")}
                className="py-3 px-4 cursor-pointer hover:bg-sky-100/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Designation</span>
                  {renderSortIcon("designation")}
                </div>
              </th>
              <th scope="col" className="py-3 px-4">
                Date
              </th>
              <th scope="col" className="py-3 px-4">
                Day
              </th>
              <th scope="col" className="py-3 px-4">
                First Punch
              </th>
              <th scope="col" className="py-3 px-4">
                Last Punch
              </th>
              <th scope="col" className="py-3 px-4">
                Total Working Hours
              </th>
              <th scope="col" className="py-3 px-4">
                Total Break Hours
              </th>
              <th
                scope="col"
                onClick={() => onSort && onSort("status")}
                className="py-3 px-4 cursor-pointer hover:bg-sky-100/50 dark:hover:bg-slate-700/50 transition-colors"
              >
                <div className="flex items-center space-x-1">
                  <span>Status</span>
                  {renderSortIcon("status")}
                </div>
              </th>
            </tr>
          </thead>

          {/* Table Body */}
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
            {records.map((record) => (
              <tr
                key={record.id}
                className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors duration-150"
              >
                <td className="py-3 px-4 font-semibold text-slate-800 dark:text-slate-200">
                  {record.employeeId}
                </td>
                <td className="py-3 px-4 font-medium text-slate-900 dark:text-slate-100">
                  {record.employeeName}
                </td>
                <td className="py-3 px-4">{record.department}</td>
                <td className="py-3 px-4">{record.designation}</td>
                <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                  {record.date}
                </td>
                <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                  {record.day}
                </td>
                <td className="py-3 px-4 font-mono text-slate-700 dark:text-slate-300">
                  {record.firstPunch || "-"}
                </td>
                <td className="py-3 px-4 font-mono text-slate-700 dark:text-slate-300">
                  {record.lastPunch || "-"}
                </td>
                <td className="py-3 px-4 font-medium text-slate-800 dark:text-slate-200">
                  {record.totalWorkingHours || "-"}
                </td>
                <td className="py-3 px-4 text-slate-500">
                  {record.totalBreakHours || "-"}
                </td>
                <td className="py-3 px-4">
                  <AttendanceStatusBadge
                    status={record.status}
                    hasAnomaly={record.hasAnomaly}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
