/**
 * A switch that turns alerts on or off.
 *
 * Built as a real button with `role="switch"`, so it works with the keyboard (Space and
 * Enter) and screen readers announce "on" or "off". It is disabled while saving, and a
 * failure is reported next to it instead of being swallowed.
 */

import { useState } from "react";

import { ApiError } from "@/lib/api";

interface AvailabilityToggleProps {
  available: boolean;
  /** Saves the new value. Should throw if saving fails. */
  onChange: (next: boolean) => Promise<void>;
}

export function AvailabilityToggle({ available, onChange }: AvailabilityToggleProps) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setSaving(true);
    setError(null);
    try {
      await onChange(!available);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Could not save. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p id="availability-label" className="text-sm font-medium text-ink">
            Receive alerts
          </p>
          <p className="text-sm text-ink-muted">
            {available ? "You are available. Matching requests will reach you." : "Alerts are paused."}
          </p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={available}
          aria-labelledby="availability-label"
          disabled={saving}
          onClick={() => void toggle()}
          className={`relative h-7 w-12 shrink-0 rounded-full transition-colors duration-250 ease-brand outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:opacity-60 ${
            available ? "bg-trust-600" : "bg-input"
          }`}
        >
          <span
            className={`absolute top-0.5 left-0.5 size-6 rounded-full bg-white shadow-soft transition-transform duration-250 ease-brand ${
              available ? "translate-x-5" : "translate-x-0"
            }`}
          />
        </button>
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}
