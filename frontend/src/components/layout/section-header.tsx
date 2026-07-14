import React from "react";

export interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export const SectionHeader = ({ title, description, action }: SectionHeaderProps) => {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-4 border-b border-border">
      <div className="text-left">
        <h3 className="text-base font-bold tracking-tight text-foreground">{title}</h3>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      {action && classNameAction(action)}
    </div>
  );
};

// Helper function to render action wrapper safely
function classNameAction(action: React.ReactNode) {
  return <div className="flex items-center gap-3 shrink-0">{action}</div>;
}
