/**
 * The BloodLink logo: a drop mark with the wordmark.
 *
 * The mark is inline SVG so it scales without extra requests and takes its colours from
 * the design tokens. Use `tone="light"` on dark backgrounds.
 */

import { cn } from "@/lib/utils";

interface LogoProps {
  /** Hide the wordmark to show the drop alone, for example in tight spaces. */
  showWordmark?: boolean;
  /** `light` renders for use on dark backgrounds. */
  tone?: "dark" | "light";
  className?: string;
}

export function Logo({ showWordmark = true, tone = "dark", className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <svg viewBox="0 0 32 32" aria-hidden="true" className="size-8 shrink-0">
        <path
          d="M16 3c4.4 5.6 8.5 9.9 8.5 14.6a8.5 8.5 0 1 1-17 0C7.5 12.9 11.6 8.6 16 3z"
          className="fill-primary-600"
        />
        <path
          d="M12 18.5a4 4 0 0 0 4 4"
          fill="none"
          stroke="white"
          strokeWidth="1.8"
          strokeLinecap="round"
          opacity="0.85"
        />
      </svg>
      {showWordmark ? (
        <span
          className={cn(
            "font-heading text-xl font-semibold tracking-tight",
            tone === "light" ? "text-ivory" : "text-ink",
          )}
        >
          Blood<span className={tone === "light" ? "text-primary-500" : "text-primary-600"}>Link</span>
        </span>
      ) : (
        <span className="sr-only">BloodLink</span>
      )}
    </span>
  );
}
