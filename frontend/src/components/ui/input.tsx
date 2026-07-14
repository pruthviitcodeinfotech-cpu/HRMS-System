import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, type = "text", ...props }, ref) => {
    const inputStyle = `flex h-10 w-full rounded-md border border-input bg-card px-3 py-2 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-foreground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:border-primary disabled:cursor-not-allowed disabled:opacity-50 ${
      error ? "border-[hsl(346.8,77.2%,49.8%)] focus-visible:ring-[hsl(346.8,77.2%,49.8%)]" : ""
    } ${className}`;

    return (
      <div className="w-full space-y-1.5">
        {label && (
          <label className="text-xs font-medium text-foreground/80 tracking-wide">{label}</label>
        )}
        <input ref={ref} type={type} className={inputStyle} {...props} />
        {error && (
          <p className="text-xs font-medium text-[hsl(346.8,77.2%,49.8%)] animate-fade-in">
            {error}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
