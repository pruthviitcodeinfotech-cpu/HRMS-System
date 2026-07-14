import React from "react";

export const TableContainer = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <div
    className={`w-full overflow-x-auto rounded-lg border border-border bg-card shadow-sm ${className}`}
  >
    <table className="w-full text-left border-collapse text-sm text-foreground">{children}</table>
  </div>
);

export const TableHead = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => (
  <thead
    className={`bg-muted/50 border-b border-border font-semibold text-xs text-muted-foreground uppercase tracking-wider ${className}`}
  >
    {children}
  </thead>
);

export const TableBody = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => <tbody className={`divide-y divide-border ${className}`}>{children}</tbody>;

export const TableRow = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => <tr className={`hover:bg-muted/30 transition-colors ${className}`}>{children}</tr>;

export const TableHeaderCell = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => <th className={`px-4 py-3 font-semibold ${className}`}>{children}</th>;

export const TableCell = ({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) => <td className={`px-4 py-3 align-middle ${className}`}>{children}</td>;
