import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
import { settingsService } from "@/features/settings/services/settings-service";

export interface GlobalPayslipData {
  employee_code: string;
  employee_name: string;
  department?: string;
  designation?: string;
  pf_number?: string;
  esic_number?: string;
  bank_name?: string;
  bank_account_no?: string;
  ifsc_code?: string;
  uan_number?: string;
  work_location?: string;
  
  // Period & Attendance
  period_label?: string; // e.g. "July 2026" or "01 Jul 2026 to 22 Jul 2026"
  full_days?: number;
  half_days?: number;
  off_days?: number;
  paid_leaves?: number;
  paid_days?: number;
  unpaid_days?: number;

  // Earnings
  gross_wages?: number;
  overtime?: number;
  extras?: number;
  arrears_addition?: number;
  gross_earnings?: number;

  // Deductions
  penalties?: number;
  loan_advance?: number;
  arrears_deduction?: number;
  total_deductions?: number;

  // Final Net
  net_payable?: number;
}

export async function generateGlobalPayslipPdf(data: GlobalPayslipData): Promise<jsPDF> {
  // Fetch live salary slip settings from Settings module (Golden Rule)
  let settings = {
    company_name: "Itcode Infotech",
    company_address: "MOJ ma rehvnau BAlko",
    company_contact: "75489768457",
    company_website_email: "abcd",
    show_pf: true,
    show_esic: true,
    show_leave_balance: true,
  };

  try {
    const res = await settingsService.getSalarySlipSettings();
    if (res?.data) {
      settings = {
        company_name: res.data.company_name || settings.company_name,
        company_address: res.data.company_address || settings.company_address,
        company_contact: res.data.company_contact || settings.company_contact,
        company_website_email: res.data.company_website_email || settings.company_website_email,
        show_pf: res.data.show_pf ?? true,
        show_esic: res.data.show_esic ?? true,
        show_leave_balance: res.data.show_leave_balance ?? true,
      };
    }
  } catch {
    // Fallback to default configured settings
  }

  const doc = new jsPDF({ orientation: "portrait", unit: "pt", format: "a4" });
  const pageWidth = doc.internal.pageSize.getWidth(); // 595.28 pt

  // Colors
  const darkBlue = [15, 23, 42]; // slate-900
  const lightBg = [248, 250, 252]; // slate-50
  const borderGray = [226, 232, 240]; // slate-200

  // 1. Outer Border Card Box
  const margin = 30;
  const contentWidth = pageWidth - margin * 2;
  let yPos = margin;

  // ── HEADER SECTION ────────────────────────────────────────────────────────
  doc.setFillColor(darkBlue[0], darkBlue[1], darkBlue[2]);
  doc.rect(margin, yPos, contentWidth, 55, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text(settings.company_name, margin + 15, yPos + 22);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(settings.company_address, margin + 15, yPos + 38);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(11);
  doc.text(`Payslip for ${data.period_label || "July 2026"}`, pageWidth - margin - 15, yPos + 30, { align: "right" });

  yPos += 65;

  // ── EMPLOYEE DETAILS SECTION ──────────────────────────────────────────────
  doc.setFillColor(lightBg[0], lightBg[1], lightBg[2]);
  doc.setDrawColor(borderGray[0], borderGray[1], borderGray[2]);
  doc.roundedRect(margin, yPos, contentWidth, 105, 4, 4, "FD");

  doc.setTextColor(darkBlue[0], darkBlue[1], darkBlue[2]);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("Employee Details", margin + 15, yPos + 18);

  doc.setFontSize(8.5);
  doc.setFont("helvetica", "normal");

  const leftX = margin + 15;
  const leftValX = margin + 100;
  const rightX = margin + 285;
  const rightValX = margin + 375;
  let empY = yPos + 34;
  const lineGap = 13;

  // Row 1
  doc.setFont("helvetica", "bold");
  doc.text("Employee Name :", leftX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.employee_name || "-", leftValX, empY);

  doc.setFont("helvetica", "bold");
  doc.text("Bank Name :", rightX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.bank_name || "-", rightValX, empY);

  // Row 2
  empY += lineGap;
  doc.setFont("helvetica", "bold");
  doc.text("Code :", leftX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.employee_code || "-", leftValX, empY);

  doc.setFont("helvetica", "bold");
  doc.text("Bank A/C No. :", rightX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.bank_account_no || "-", rightValX, empY);

  // Row 3
  empY += lineGap;
  doc.setFont("helvetica", "bold");
  doc.text("Designation :", leftX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.designation || "-", leftValX, empY);

  doc.setFont("helvetica", "bold");
  doc.text("IFSC Code :", rightX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.ifsc_code || "-", rightValX, empY);

  // Row 4
  empY += lineGap;
  doc.setFont("helvetica", "bold");
  doc.text("Department :", leftX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.department || "-", leftValX, empY);

  doc.setFont("helvetica", "bold");
  doc.text("UAN Number :", rightX, empY);
  doc.setFont("helvetica", "normal");
  doc.text(data.uan_number || "-", rightValX, empY);

  // Row 5 (PF & ESIC toggled by Settings)
  if (settings.show_pf) {
    empY += lineGap;
    doc.setFont("helvetica", "bold");
    doc.text("PF Number :", leftX, empY);
    doc.setFont("helvetica", "normal");
    doc.text(data.pf_number || "-", leftValX, empY);

    doc.setFont("helvetica", "bold");
    doc.text("Work Location :", rightX, empY);
    doc.setFont("helvetica", "normal");
    doc.text(data.work_location || "-", rightValX, empY);
  }

  if (settings.show_esic) {
    empY += lineGap;
    doc.setFont("helvetica", "bold");
    doc.text("ESIC Number :", leftX, empY);
    doc.setFont("helvetica", "normal");
    doc.text(data.esic_number || "-", leftValX, empY);
  }

  yPos += 115;

  // ── EARNINGS & DEDUCTIONS TABLE ───────────────────────────────────────────
  const grossWages = data.gross_wages || 0;
  const overtime = data.overtime || 0;
  const extras = data.extras || 0;
  const arrearsAdd = data.arrears_addition || 0;
  const totalGross = data.gross_earnings ?? (grossWages + overtime + extras + arrearsAdd);

  const penalties = data.penalties || 0;
  const loanAdvance = data.loan_advance || 0;
  const arrearsDed = data.arrears_deduction || 0;
  const totalDeductions = data.total_deductions ?? (penalties + loanAdvance + arrearsDed);

  const tableBody = [
    ["Gross Base Salary", `₹ ${grossWages.toLocaleString("en-IN")}`, "Penalties", `₹ ${penalties.toLocaleString("en-IN")}`],
    ["Overtime", `₹ ${overtime.toLocaleString("en-IN")}`, "Loan & Advance", `₹ ${loanAdvance.toLocaleString("en-IN")}`],
    ["Extras / Allowance", `₹ ${extras.toLocaleString("en-IN")}`, "Arrears Deduction", `₹ ${arrearsDed.toLocaleString("en-IN")}`],
    ["Arrears Addition", `₹ ${arrearsAdd.toLocaleString("en-IN")}`, "", ""],
  ];

  autoTable(doc, {
    startY: yPos,
    margin: { left: margin, right: margin },
    head: [["Earnings", "Amount (Rs.)", "Deductions", "Amount (Rs.)"]],
    body: tableBody,
    foot: [["Total Gross Earnings", `₹ ${totalGross.toLocaleString("en-IN")}`, "Total Deductions", `₹ ${totalDeductions.toLocaleString("en-IN")}`]],
    styles: { fontSize: 8.5, cellPadding: 5 },
    headStyles: { fillColor: [30, 41, 59], textColor: 255, fontStyle: "bold" },
    footStyles: { fillColor: [241, 245, 249], textColor: [15, 23, 42], fontStyle: "bold" },
    alternateRowStyles: { fillColor: [255, 255, 255] },
    columnStyles: {
      0: { cellWidth: 150 },
      1: { cellWidth: 110, halign: "right", fontStyle: "bold" },
      2: { cellWidth: 150 },
      3: { cellWidth: 125, halign: "right", fontStyle: "bold" },
    },
  });

  const lastTablePos = (doc as any).lastAutoTable;
  yPos = lastTablePos ? lastTablePos.finalY + 12 : yPos + 160;

  // ── ATTENDANCE SUMMARY ROW ────────────────────────────────────────────────
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(margin, yPos, contentWidth, 24, 3, 3, "F");

  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  doc.setTextColor(30, 41, 59);

  const paidDays = data.paid_days ?? 0;
  const workedDays = data.full_days ?? 0;
  const weeklyOff = data.off_days ?? 0;
  const holidays = 0;
  const paidLeaves = data.paid_leaves ?? 0;

  const attText = `Total Payable Days : ${paidDays}    |    Worked Day : ${workedDays}    |    Weekly Off : ${weeklyOff}    |    Holiday : ${holidays}    |    Paid Leaves : ${paidLeaves}`;
  doc.text(attText, margin + 15, yPos + 15);

  yPos += 34;

  // ── TOTAL NET PAYABLE HIGHLIGHT BOX ───────────────────────────────────────
  const netPayable = data.net_payable ?? Math.max(0, totalGross - totalDeductions);

  doc.setFillColor(240, 253, 244); // emerald-50
  doc.setDrawColor(167, 243, 208); // emerald-200
  doc.roundedRect(margin, yPos, contentWidth, 48, 6, 6, "FD");

  doc.setTextColor(5, 150, 105); // emerald-600
  doc.setFont("helvetica", "bold");
  doc.setFontSize(13);
  doc.text(`Total Net Payable : ₹ ${netPayable.toLocaleString("en-IN")}`, margin + 15, yPos + 22);

  doc.setFontSize(8.5);
  doc.setFont("helvetica", "normal");
  doc.setTextColor(71, 85, 105);
  doc.text("Total Net Payable = Gross Earnings - Total Deductions", margin + 15, yPos + 37);

  return doc;
}

export async function downloadGlobalPayslipPdf(data: GlobalPayslipData, filename?: string) {
  const doc = await generateGlobalPayslipPdf(data);
  const fname = filename || `SalarySlip_${data.employee_code || "EMP"}_${data.period_label || "July2026"}.pdf`;
  doc.save(fname);
}
