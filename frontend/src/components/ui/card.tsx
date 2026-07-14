import React from "react";

type CardProps = React.HTMLAttributes<HTMLDivElement>;

export const Card = ({ className = "", children, ...props }: CardProps) => {
  return (
    <div
      className={`rounded-lg border border-border bg-card p-6 shadow-base ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({ className = "", children, ...props }: CardProps) => {
  return (
    <div className={`flex flex-col space-y-1.5 pb-4 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardTitle = ({ className = "", children, ...props }: CardProps) => {
  return (
    <h3 className={`text-lg font-semibold leading-none tracking-tight ${className}`} {...props}>
      {children}
    </h3>
  );
};

export const CardDescription = ({ className = "", children, ...props }: CardProps) => {
  return (
    <p className={`text-xs text-foreground/75 ${className}`} {...props}>
      {children}
    </p>
  );
};

export const CardContent = ({ className = "", children, ...props }: CardProps) => {
  return (
    <div className={`pt-0 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardFooter = ({ className = "", children, ...props }: CardProps) => {
  return (
    <div className={`flex items-center pt-4 border-t border-border mt-4 ${className}`} {...props}>
      {children}
    </div>
  );
};
