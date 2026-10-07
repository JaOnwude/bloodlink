import * as React from "react"

import { cn } from "@/lib/utils"

/**
 * Text input styled with the BloodLink tokens.
 *
 * Tall (48px) with a clearly visible border, because form controls need stronger contrast
 * than decorative lines and are used on touch screens. Errors are shown by setting
 * `aria-invalid` on the input, which turns the border and focus ring red.
 */
function Input({ className, type = "text", ...props }: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-12 w-full min-w-0 rounded-xl border border-input bg-surface px-4 text-base text-ink transition-[border-color,box-shadow] duration-150 outline-none placeholder:text-ink-muted/70 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/25 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20",
        className
      )}
      {...props}
    />
  )
}

export { Input }
