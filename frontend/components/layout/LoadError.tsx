/**
 * Shown when a page could not load its data, with a button to try again.
 */

import { CircleAlert } from "lucide-react";

import { Button } from "@/components/ui/button";

interface LoadErrorProps {
  message: string;
  onRetry: () => void;
}

export function LoadError({ message, onRetry }: LoadErrorProps) {
  return (
    <div
      role="alert"
      className="mx-auto flex max-w-md flex-col items-center gap-4 rounded-3xl border border-border bg-surface p-8 text-center"
    >
      <CircleAlert className="size-8 text-primary-600" aria-hidden="true" />
      <p className="text-ink">{message}</p>
      <Button variant="outline" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
