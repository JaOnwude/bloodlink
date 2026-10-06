import type { ComponentProps } from "react"

import { cn } from "@/lib/utils"

/**
 * A pulsing placeholder shown while content loads. The pulse stops for visitors who prefer
 * reduced motion.
 */
function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      aria-hidden="true"
      className={cn("animate-pulse rounded-xl bg-muted motion-reduce:animate-none", className)}
      {...props}
    />
  )
}

export { Skeleton }
