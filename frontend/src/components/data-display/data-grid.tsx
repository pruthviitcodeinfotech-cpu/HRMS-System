"use client";

import React from "react";
import { AgGridProvider, AgGridReact } from "ag-grid-react";
import { AllCommunityModule } from "ag-grid-community";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";
import { useTheme } from "@/providers/theme-provider";

type DataGridProps = React.ComponentProps<typeof AgGridReact>;

export const DataGrid = ({ className = "", ...props }: DataGridProps) => {
  const { theme } = useTheme();

  // Resolve theme class dynamically
  const themeClass = theme === "dark" ? "ag-theme-quartz-dark" : "ag-theme-quartz";

  return (
    <AgGridProvider modules={[AllCommunityModule]}>
      <div className={`${themeClass} w-full h-[400px] font-sans ${className}`}>
        <AgGridReact rowHeight={44} headerHeight={40} animateRows={true} {...props} />
      </div>
    </AgGridProvider>
  );
};
