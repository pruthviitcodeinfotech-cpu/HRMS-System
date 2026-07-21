"use client";

import React, { useState } from "react";
import * as XLSX from "xlsx";
import { toast } from "sonner";
import {
  AttendanceRecord,
  AttendanceFilter,
  AttendancePagination,
  SortField,
  SortOrder,
} from "../types/attendance";
import { AttendanceFilterBar } from "./attendance-filter";
import { AttendanceTable } from "./attendance-table";
import { AttendancePaginationFooter } from "./attendance-pagination";
import { AttendanceEmptyState } from "./attendance-empty";
import { AttendanceLoadingSkeleton } from "./attendance-loading";

// Helper to convert DD-MM-YYYY to YYYY-MM-DD ISO for date comparisons
const toIsoDate = (dateStr: string): string => {
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    const [day, month, year] = parts;
    return `${year}-${month.padStart(2, "0")}-${day.padStart(2, "0")}`;
  }
  return dateStr;
};

// Base Master Employee List (All 10 employees from Petpooja reference)
const EMPLOYEES = [
  { id: "57", name: "Tulsi baladhiya", dept: "Marketing", desig: "Graphic Designer", punchIn: "09:15 AM", punchOut: "06:32 PM", hrs: "9h 17m", status: "FD" as const },
  { id: "56", name: "Hetal Gohil", dept: "Marketing", desig: "marketing", punchIn: "08:53 AM", punchOut: "06:49 PM", hrs: "9h 55m", status: "FD" as const },
  { id: "55", name: "Mansi Baghre", dept: "Developer", desig: "Python", punchIn: "09:08 AM", punchOut: "06:34 PM", hrs: "9h 25m", status: "FD" as const },
  { id: "54", name: "Divyesh Pipaliya", dept: "Marketing", desig: "marketing", punchIn: "10:35 AM", punchOut: "-", hrs: "-", status: "Absent" as const, anomaly: true },
  { id: "53", name: "Pratik raval", dept: "Marketing", desig: "marketing", punchIn: "09:36 AM", punchOut: "05:41 PM", hrs: "8h 5m", status: "FD" as const },
  { id: "52", name: "Krishna Chodvadiya", dept: "BDM", desig: "BDM", punchIn: "-", punchOut: "-", hrs: "-", status: "Absent" as const },
  { id: "51", name: "Kunal Kikani", dept: "video editing", desig: "video editing", punchIn: "09:28 AM", punchOut: "06:32 PM", hrs: "9h 4m", status: "FD" as const },
  { id: "50", name: "Vivek Rathod", dept: "Graphic Designer", desig: "Graphic Designer", punchIn: "09:27 AM", punchOut: "06:39 PM", hrs: "9h 12m", status: "FD" as const },
  { id: "49", name: "Rahi Patel", dept: "video editing", desig: "video editing", punchIn: "-", punchOut: "-", hrs: "-", status: "Absent" as const },
  { id: "48", name: "Jay Surani", dept: "Marketing", desig: "marketing", punchIn: "09:15 AM", punchOut: "06:46 PM", hrs: "9h 31m", status: "FD" as const },
];

const DATES_CONFIG = [
  { date: "01-07-2026", day: "Wednesday" },
  { date: "02-07-2026", day: "Thursday" },
  { date: "03-07-2026", day: "Friday" },
  { date: "04-07-2026", day: "Saturday" },
  { date: "05-07-2026", day: "Sunday" },
  { date: "06-07-2026", day: "Monday" },
  { date: "07-07-2026", day: "Tuesday" },
  { date: "08-07-2026", day: "Wednesday" },
  { date: "09-07-2026", day: "Thursday" },
  { date: "10-07-2026", day: "Friday" },
  { date: "11-07-2026", day: "Saturday" },
  { date: "12-07-2026", day: "Sunday" },
  { date: "13-07-2026", day: "Monday" },
  { date: "14-07-2026", day: "Tuesday" },
  { date: "15-07-2026", day: "Wednesday" },
  { date: "16-07-2026", day: "Thursday" },
  { date: "17-07-2026", day: "Friday" },
  { date: "18-07-2026", day: "Saturday" },
  { date: "19-07-2026", day: "Sunday" },
  { date: "20-07-2026", day: "Monday" },
  { date: "21-07-2026", day: "Tuesday" },
];

// Generate full records so all 10 employees have complete records for every single date in the range
const generateFullAttendanceRecords = (): AttendanceRecord[] => {
  const records: AttendanceRecord[] = [];
  let recordIdCounter = 1;

  DATES_CONFIG.forEach(({ date, day }) => {
    EMPLOYEES.forEach((emp) => {
      const isSunday = day === "Sunday";
      records.push({
        id: String(recordIdCounter++),
        employeeId: emp.id,
        employeeName: emp.name,
        department: emp.dept,
        designation: emp.desig,
        date,
        day,
        firstPunch: isSunday ? "-" : emp.punchIn,
        lastPunch: isSunday ? "-" : emp.punchOut,
        totalWorkingHours: isSunday ? "-" : emp.hrs,
        totalBreakHours: "-",
        status: isSunday ? "Weekly Off" : emp.status,
        hasAnomaly: isSunday ? false : emp.anomaly,
      });
    });
  });

  return records;
};

const ALL_MASTER_RECORDS = generateFullAttendanceRecords();

export const AttendanceMasterView: React.FC = () => {
  // Local state for UI only
  const [isLoading] = useState<boolean>(false);
  const [records, setRecords] = useState<AttendanceRecord[]>(ALL_MASTER_RECORDS);
  const [sortField, setSortField] = useState<SortField>("employeeId");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);

  // Sorting Handler
  const handleSort = (field: SortField) => {
    let newOrder: SortOrder = "asc";
    if (sortField === field && sortOrder === "asc") {
      newOrder = "desc";
    }
    setSortField(field);
    setSortOrder(newOrder);

    const sorted = [...records].sort((a, b) => {
      const valA = a[field] || "";
      const valB = b[field] || "";

      if (field === "employeeId") {
        return newOrder === "asc"
          ? Number(valA) - Number(valB)
          : Number(valB) - Number(valA);
      }

      if (field === "date") {
        const isoA = toIsoDate(valA);
        const isoB = toIsoDate(valB);
        return newOrder === "asc"
          ? isoA.localeCompare(isoB)
          : isoB.localeCompare(isoA);
      }

      if (valA < valB) return newOrder === "asc" ? -1 : 1;
      if (valA > valB) return newOrder === "asc" ? 1 : -1;
      return 0;
    });

    setRecords(sorted);
  };

  // Date Range & Branch Filter Search Handler
  const handleSearch = (filter: AttendanceFilter) => {
    const filtered = ALL_MASTER_RECORDS.filter((record) => {
      const recordIsoDate = toIsoDate(record.date);

      // Check From Date filter
      if (filter.fromDate && recordIsoDate < filter.fromDate) {
        return false;
      }

      // Check To Date filter
      if (filter.toDate && recordIsoDate > filter.toDate) {
        return false;
      }

      return true;
    });

    setRecords(filtered);
    setCurrentPage(1);
  };

  const handleResetFilters = () => {
    setRecords(ALL_MASTER_RECORDS);
    setCurrentPage(1);
  };

  // Export Excel Functionality
  const handleExportExcel = () => {
    if (records.length === 0) {
      toast.error("No attendance records to export.");
      return;
    }

    const exportData = records.map((r) => ({
      "Employee ID": r.employeeId,
      "Employee Name": r.employeeName,
      Department: r.department,
      Designation: r.designation,
      Date: r.date,
      Day: r.day,
      "First Punch": r.firstPunch,
      "Last Punch": r.lastPunch,
      "Total Working Hours": r.totalWorkingHours,
      "Total Break Hours": r.totalBreakHours,
      Status: r.status,
    }));

    const worksheet = XLSX.utils.json_to_sheet(exportData);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Attendance Master");

    const fileName = `Attendance_Master_${new Date().toISOString().slice(0, 10)}.xlsx`;
    XLSX.writeFile(workbook, fileName);
    toast.success("Attendance Master exported to Excel successfully!");
  };

  // Export PDF Functionality (Printable window / PDF Download)
  const handleExportPdf = () => {
    if (records.length === 0) {
      toast.error("No attendance records to export.");
      return;
    }

    const printWindow = window.open("", "_blank");
    if (!printWindow) {
      toast.error("Please allow popups to export PDF.");
      return;
    }

    const tableRowsHtml = records
      .map(
        (r) => `
      <tr>
        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">${r.employeeId}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.employeeName}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.department}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.designation}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.date}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.day}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.firstPunch}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.lastPunch}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.totalWorkingHours}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0;">${r.totalBreakHours}</td>
        <td style="padding: 8px; border: 1px solid #e2e8f0; font-weight: bold;">${r.status}</td>
      </tr>
    `
      )
      .join("");

    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Attendance Master Report</title>
          <style>
            body { font-family: Arial, sans-serif; padding: 20px; color: #1e293b; }
            h1 { text-align: center; color: #0284c7; margin-bottom: 5px; }
            p.meta { text-align: center; font-size: 12px; color: #64748b; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; font-size: 11px; }
            th { background-color: #f0f9ff; padding: 10px 8px; border: 1px solid #cbd5e1; text-align: left; font-weight: bold; color: #0f172a; }
            @media print {
              body { padding: 0; }
              @page { size: landscape; margin: 10mm; }
            }
          </style>
        </head>
        <body>
          <h1>Attendance Master Report</h1>
          <p class="meta">Generated on ${new Date().toLocaleString()} | Total Records: ${records.length}</p>
          <table>
            <thead>
              <tr>
                <th>Emp ID</th>
                <th>Employee Name</th>
                <th>Department</th>
                <th>Designation</th>
                <th>Date</th>
                <th>Day</th>
                <th>First Punch</th>
                <th>Last Punch</th>
                <th>Working Hours</th>
                <th>Break Hours</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${tableRowsHtml}
            </tbody>
          </table>
          <script>
            window.onload = function() {
              window.print();
            };
          </script>
        </body>
      </html>
    `;

    printWindow.document.write(htmlContent);
    printWindow.document.close();
    toast.success("Attendance Master PDF print preview opened!");
  };

  // Dynamic pagination calculation based on filtered records
  const totalRecords = records.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const paginatedRecords = records.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  );

  const paginationInfo: AttendancePagination = {
    currentPage,
    pageSize,
    totalRecords,
    totalPages,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header Title */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
          Attendance Master
        </h1>
      </div>

      {/* Filter Bar */}
      <AttendanceFilterBar
        onSearch={handleSearch}
        onReset={handleResetFilters}
        onExportExcel={handleExportExcel}
        onExportPdf={handleExportPdf}
      />

      {/* Main Content Area: Table / Loading / Empty */}
      {isLoading ? (
        <AttendanceLoadingSkeleton rows={pageSize} />
      ) : records.length === 0 ? (
        <AttendanceEmptyState onReset={handleResetFilters} />
      ) : (
        <div className="space-y-0">
          <AttendanceTable
            records={paginatedRecords}
            sortField={sortField}
            sortOrder={sortOrder}
            onSort={handleSort}
          />
          <AttendancePaginationFooter
            pagination={paginationInfo}
            onPageChange={(page) => setCurrentPage(page)}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setCurrentPage(1);
            }}
          />
        </div>
      )}
    </div>
  );
};
