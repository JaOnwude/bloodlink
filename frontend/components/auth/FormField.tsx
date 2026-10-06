/**
 * A labelled form field with an optional hint and error message.
 *
 * The label is always visible and linked to the input. The error and the hint are linked
 * with `aria-describedby`, so screen readers announce them with the field, and the error
 * also flips `aria-invalid` so the input is styled as invalid.
 */

import { TriangleAlert } from "lucide-react";
import type { ComponentProps, ReactNode } from "react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface FormFieldProps extends Omit<ComponentProps<"input">, "id" | "className"> {
  id: string;
  label: string;
  /** Help shown under the input. */
  hint?: string;
  /** Problem with the current value. Replaces nothing: it is shown above the hint. */
  error?: string;
  /** Marks the field as not required. */
  optional?: boolean;
  /** Content placed at the right edge inside the input, such as a show/hide button. */
  trailing?: ReactNode;
}

export function FormField({
  id,
  label,
  hint,
  error,
  optional,
  trailing,
  ...inputProps
}: FormFieldProps) {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ");

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between gap-4">
        <Label htmlFor={id} className="text-sm font-medium text-ink">
          {label}
        </Label>
        {optional ? <span className="text-xs text-ink-muted">Optional</span> : null}
      </div>

      <div className="relative">
        <Input
          id={id}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy || undefined}
          className={trailing ? "pr-12" : undefined}
          {...inputProps}
        />
        {trailing ? (
          <div className="absolute inset-y-0 right-1 flex items-center">{trailing}</div>
        ) : null}
      </div>

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
