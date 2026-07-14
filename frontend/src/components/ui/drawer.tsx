"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";
import { Button } from "./button";

export interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  position?: "left" | "right";
}

export const Drawer = ({
  isOpen,
  onClose,
  title,
  children,
  footer,
  position = "right",
}: DrawerProps) => {
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const positionClasses = {
    left: "left-0 h-full border-r animate-in slide-in-from-left duration-300",
    right: "right-0 h-full border-l animate-in slide-in-from-right duration-300",
  };

  return (
    <div className="fixed inset-0 z-50 flex bg-background/85 backdrop-blur-sm animate-in fade-in duration-200">
      {/* Backdrop closing click */}
      <div className="flex-1 cursor-pointer" onClick={onClose} />

      <div
        className={`fixed top-0 w-full max-w-md bg-card shadow-xl flex flex-col border-border ${positionClasses[position]}`}
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="text-base font-bold text-foreground">{title}</h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
            aria-label="Close drawer"
          >
            <X className="h-4.5 w-4.5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6 text-sm text-foreground">{children}</div>

        {/* Footer */}
        {footer ? (
          <div className="flex justify-end items-center gap-3 px-6 py-4 border-t border-border bg-muted/30">
            {footer}
          </div>
        ) : (
          <div className="flex justify-end items-center gap-3 px-6 py-4 border-t border-border bg-muted/30">
            <Button variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
