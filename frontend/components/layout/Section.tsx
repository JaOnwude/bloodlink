/**
 * A full-width band of a page with consistent vertical rhythm and a background tone.
 *
 * Tones: `canvas` (default page colour), `surface` (white), `tint` (soft crimson wash) and
 * `night` (dark, with light text). Alternating tones is the main way pages are paced.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

const tones = {
  canvas: "bg-canvas text-foreground",
  surface: "bg-surface text-foreground",
  tint: "bg-primary-50 text-foreground",
  night: "bg-night text-ivory",
} as const;

interface SectionProps {
  tone?: keyof typeof tones;
  id?: string;
  className?: string;
  children: ReactNode;
}

export function Section({ tone = "canvas", id, className, children }: SectionProps) {
  return (
    <section id={id} className={cn("py-section", tones[tone], className)}>
      {children}
    </section>
  );
}
