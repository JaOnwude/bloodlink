/**
 * A checkbox with a label and an explanation, for yes/no choices such as consent.
 *
 * The whole block is one label, so the text is part of the click target and a screen reader
 * announces it as the checkbox's name. The description is linked with `aria-describedby`.
 */

import type { ComponentProps, ReactNode } from "react";

interface CheckboxFieldProps extends Omit<ComponentProps<"input">, "id" | "type" | "className"> {
  id: string;
  label: string;
  description?: ReactNode;
}

export function CheckboxField({ id, label, description, ...inputProps }: CheckboxFieldProps) {
  const descriptionId = `${id}-description`;

  return (
    <label
      htmlFor={id}
      className="flex cursor-pointer items-start gap-3 rounded-2xl border border-border bg-surface p-4 transition-colors duration-150 hover:border-input"
    >
      <input
        id={id}
        type="checkbox"
        aria-describedby={description ? descriptionId : undefined}
        className="mt-0.5 size-5 shrink-0 cursor-pointer accent-primary-600"
        {...inputProps}
      />
      <span className="space-y-1">
        <span className="block text-sm font-medium text-ink">{label}</span>
        {description ? (
          <span id={descriptionId} className="block text-sm text-ink-muted">
            {description}
          </span>
        ) : null}
      </span>
    </label>
  );
}
