import React from "react";
import { FolderOpen } from "lucide-react";

export interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}

export const EmptyState = ({
  title = "No data found",
  description = "There are no records matching the query.",
  icon = <FolderOpen className="h-10 w-10 text-muted-foreground/60" />,
  action,
}: EmptyStateProps) => {
  return (
    <div className="flex flex-col items-center justify-center p-8 py-16 border border-dashed border-border rounded-lg text-center bg-card/20">
      <div className="p-3 bg-muted/40 rounded-full mb-4">{icon}</div>
      <h3 className="text-sm font-bold text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground max-w-sm mb-5">{description}</p>
      {action && <div>{action}</div>}
    </div>
  );
};
