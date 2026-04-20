"use client";
import React, { useId } from "react";

interface TooltipProps {
  text: string;
  children: React.ReactNode;
  position?: "top" | "bottom" | "left" | "right";
}

const POSITION_CLASSES: Record<NonNullable<TooltipProps["position"]>, string> = {
  top: "bottom-full left-1/2 -translate-x-1/2 mb-1.5",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-1.5",
  left: "right-full top-1/2 -translate-y-1/2 mr-1.5",
  right: "left-full top-1/2 -translate-y-1/2 ml-1.5",
};

export function Tooltip({ text, children, position = "top" }: TooltipProps) {
  const id = useId();

  const child = React.Children.only(children) as React.ReactElement;
  const clonedChild = React.cloneElement(child, { 'aria-describedby': id });

  return (
    <span className="relative group inline-flex">
      {clonedChild}
      <span
        id={id}
        role="tooltip"
        className={[
          "absolute z-50 whitespace-nowrap rounded bg-slate-800 px-2 py-1 text-xs text-white shadow",
          "opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity pointer-events-none",
          POSITION_CLASSES[position],
        ].join(" ")}
      >
        {text}
      </span>
    </span>
  );
}
