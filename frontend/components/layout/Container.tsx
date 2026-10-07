/**
 * Centres content and keeps line lengths and gutters consistent.
 *
 * Sizes map to the container tokens: `content` (1200px) for most pages, `wide` (1360px)
 * for full-bleed layouts, and `reading` (680px) for long-form text.
 */

import { createElement } from "react";
import type { ElementType, ReactNode } from "react";

import { cn } from "@/lib/utils";

const widths = {
  content: "max-w-content",
  wide: "max-w-wide",
  reading: "max-w-reading",
} as const;

interface ContainerProps {
  size?: keyof typeof widths;
  as?: ElementType;
  className?: string;
  children: ReactNode;
}

export function Container({ size = "content", as = "div", className, children }: ContainerProps) {
  return createElement(
    as,
    { className: cn("mx-auto w-full px-5 sm:px-8", widths[size], className) },
    children,
  );
}
