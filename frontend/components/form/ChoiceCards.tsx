/**
 * A small set of large selectable cards, built on native radio buttons.
 *
 * Keyboard use, arrow-key movement and screen reader announcements come from the radios
 * themselves. The first radio carries the group's `name` as its id, so an error can move
 * focus there.
 */

import { TriangleAlert } from "lucide-react";

export interface ChoiceOption<T extends string> {
  value: T;
  title: string;
  description?: string;
}

interface ChoiceCardsProps<T extends string> {
  name: string;
  legend: string;
  options: ChoiceOption<T>[];
  value: T | "";
  onChange: (value: T) => void;
  hint?: string;
  error?: string;
}

export function ChoiceCards<T extends string>({
  name,
  legend,
  options,
  value,
  onChange,
  hint,
  error,
}: ChoiceCardsProps<T>) {
  const errorId = `${name}-error`;
  const hintId = `${name}-hint`;
  const describedBy = [error ? errorId : null, hint ? hintId : null].filter(Boolean).join(" ");

  return (
    <fieldset aria-describedby={describedBy || undefined}>
      <legend className="mb-2 text-sm font-medium text-ink">{legend}</legend>
      <div className="grid gap-3 sm:grid-cols-2">
        {options.map((option, index) => (
          <label key={option.value} className="relative block cursor-pointer">
            <input
              id={index === 0 ? name : undefined}
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="peer sr-only"
            />
            <span className="flex h-full flex-col gap-1 rounded-2xl border border-input bg-surface p-4 transition-colors duration-150 peer-checked:border-primary-600 peer-checked:bg-primary-50 peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-background">
              <span className="text-sm font-semibold text-ink">{option.title}</span>
              {option.description ? (
                <span className="text-sm text-ink-muted">{option.description}</span>
              ) : null}
            </span>
          </label>
        ))}
      </div>
      {error ? (
        <p id={errorId} className="mt-2 flex items-start gap-1.5 text-sm text-danger">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      {hint ? (
        <p id={hintId} className="mt-2 text-sm text-ink-muted">
          {hint}
        </p>
      ) : null}
    </fieldset>
  );
}
