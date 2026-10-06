/**
 * Wraps content so it fades and rises into place the first time it scrolls into view.
 *
 * Use one wrapper per block, and stagger a group by giving each item a larger `delay`
 * (about 80 ms per step). The behaviour is disabled automatically for visitors who prefer
 * reduced motion and when JavaScript is unavailable.
 */

import { createElement } from "react";
import type { CSSProperties, ElementType, ReactNode } from "react";

import { cn } from "@/lib/utils";
import { useRevealOnScroll } from "@/lib/use-reveal";

interface RevealProps {
  children: ReactNode;
  /** Delay before the transition starts, in milliseconds. */
  delay?: number;
  /** HTML element to render. Defaults to a div. */
  as?: ElementType;
  className?: string;
}

export function Reveal({ children, delay = 0, as = "div", className }: RevealProps) {
  const ref = useRevealOnScroll<HTMLElement>();
  const style = { "--reveal-delay": `${delay}ms` } as CSSProperties;

  return createElement(as, { ref, style, className: cn("reveal", className) }, children);
}
