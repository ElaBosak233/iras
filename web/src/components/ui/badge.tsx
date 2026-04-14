import type * as React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "success" | "warning" | "destructive" | "secondary";
}

export const Badge = ({
  className,
  variant = "default",
  ...props
}: BadgeProps) => (
  <span
    className={cn(
      "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
      {
        "bg-blue-100 text-blue-800": variant === "default",
        "bg-green-100 text-green-800": variant === "success",
        "bg-yellow-100 text-yellow-800": variant === "warning",
        "bg-red-100 text-red-800": variant === "destructive",
        "bg-gray-100 text-gray-800": variant === "secondary",
      },
      className
    )}
    {...props}
  />
);
