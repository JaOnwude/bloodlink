/**
 * A labelled multi-line text box with an optional hint and error message.
 *
 * Linked to its label, hint and error the same way as the single-line fields, so screen
 * readers announce them together.
 */

import { TriangleAlert } from "lucide-react";
import type { ComponentProps } from "react";

import { Label } from "@/components/ui/label";

interface TextareaFieldProps extends Omit<ComponentProps<"textarea">, "id" | "className"> {
  id: string;
  label: string;
  hint?: string;
  error?: string;
}

export function TextareaField({ id, label, hint, error, ...textareaProps }: TextareaFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ");

  return (
    <div className="space-y-2">
      <Label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
      </Label>
      <textarea
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy || undefined}
        className="min-h-28 w-full rounded-xl border border-input bg-surface px-4 py-3 text-base text-ink transition-[border-color,box-shadow] duration-150 outline-none placeholder:text-ink-muted/70 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/25 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20"
        {...textareaProps}
      />
      {error ? (
        <p id={errorId} className="flex items-start gap-1.5 text-sm text-danger">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
    </div>
  );
}
