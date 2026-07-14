import React from "react";

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "success" | "warning" | "destructive" | "info";
}

export const Alert = ({ className = "", variant = "info", children, ...props }: AlertProps) => {
  const baseStyle = "flex items-start space-x-3 p-4 rounded-lg border text-sm font-sans";

  const variants = {
    success:
      "bg-[hsl(142.1,76.2%,36.3%)]/5 border-[hsl(142.1,76.2%,36.3%)]/20 text-[hsl(142.1,76.2%,36.3%)]",
    warning:
      "bg-[hsl(37.9,90.2%,49.8%)]/5 border-[hsl(37.9,90.2%,49.8%)]/20 text-[hsl(37.9,90.2%,49.8%)]",
    destructive:
      "bg-[hsl(346.8,77.2%,49.8%)]/5 border-[hsl(346.8,77.2%,49.8%)]/20 text-[hsl(346.8,77.2%,49.8%)]",
    info: "bg-[hsl(198.6,88.7%,48.4%)]/5 border-[hsl(198.6,88.7%,48.4%)]/20 text-[hsl(198.6,88.7%,48.4%)]",
  };

  const classNames = `${baseStyle} ${variants[variant]} ${className}`;

  return (
    <div className={classNames} role="alert" {...props}>
      {children}
    </div>
  );
};
