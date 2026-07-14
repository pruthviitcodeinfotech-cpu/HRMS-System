import React from "react";

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>;

export const Skeleton = ({ className = "", ...props }: SkeletonProps) => {
  return <div className={`animate-pulse rounded-md bg-border/50 ${className}`} {...props} />;
};
