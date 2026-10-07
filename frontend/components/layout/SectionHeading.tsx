/**
 * The standard opening of a section: a small label, a title and an optional lead paragraph.
 *
 * Using one component for every section keeps the hierarchy and spacing identical across
 * the site.
 */

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

interface SectionHeadingProps {
  /** Small uppercase label above the title. */
  eyebrow?: string;
  title: ReactNode;
  lead?: ReactNode;
  align?: "left" | "center";
  className?: string;
}

export function SectionHeading({
  eyebrow,
  title,
  lead,
  align = "left",
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("max-w-2xl", align === "center" && "mx-auto text-center", className)}>
      {eyebrow ? (
        <p className="mb-3 text-sm font-semibold tracking-wider text-primary-600 uppercase">
          {eyebrow}
        </p>
      ) : null}
      <h2 className="text-title font-semibold text-ink">{title}</h2>
      {lead ? <p className="mt-4 text-lead text-ink-muted">{lead}</p> : null}
    </div>
  );
}
