import React from "react";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "destructive" | "info" | "default";
}

export const Badge = ({ className = "", variant = "default", children, ...props }: BadgeProps) => {
  const baseStyle =
    "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2";

  const variants = {
    default: "bg-primary/10 text-primary border border-primary/20",
    success:
      "bg-[hsl(142.1,76.2%,36.3%)]/10 text-[hsl(142.1,76.2%,36.3%)] border border-[hsl(142.1,76.2%,36.3%)]/20",
    warning:
      "bg-[hsl(37.9,90.2%,49.8%)]/10 text-[hsl(37.9,90.2%,49.8%)] border border-[hsl(37.9,90.2%,49.8%)]/20",
    destructive:
      "bg-[hsl(346.8,77.2%,49.8%)]/10 text-[hsl(346.8,77.2%,49.8%)] border border-[hsl(346.8,77.2%,49.8%)]/20",
    info: "bg-[hsl(198.6,88.7%,48.4%)]/10 text-[hsl(198.6,88.7%,48.4%)] border border-[hsl(198.6,88.7%,48.4%)]/20",
  };

  const classNames = `${baseStyle} ${variants[variant]} ${className}`;

  return (
    <span className={classNames} {...props}>
      {children}
    </span>
  );
};
