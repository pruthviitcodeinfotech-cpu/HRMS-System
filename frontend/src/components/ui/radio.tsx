import React from "react";

export interface RadioProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Radio = React.forwardRef<HTMLInputElement, RadioProps>(
  ({ label, error, className = "", ...props }, ref) => {
    return (
      <div className="space-y-1 text-left">
        <label className="flex items-center space-x-2 text-sm font-medium text-foreground cursor-pointer select-none">
          <input
            type="radio"
            ref={ref}
            className={`h-4 w-4 border-border text-primary focus:ring-primary cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
            {...props}
          />
          {label && <span>{label}</span>}
        </label>
        {error && <p className="text-[10px] font-semibold text-destructive">{error}</p>}
      </div>
    );
  }
);

Radio.displayName = "Radio";
