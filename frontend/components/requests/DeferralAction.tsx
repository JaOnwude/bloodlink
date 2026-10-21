/**
 * Records that a donor came but was turned away at screening.
 *
 * Staff choose a reason category; the panel says how long that reason defers the donor, as
 * set in the server's deferral rules, so the consequence is clear before confirming. Only
 * the category is ever stored, never a result. For a positive infection screen the panel
 * reminds staff that BloodLink only asks the donor to contact the hospital: the donor must
 * be told in person, in confidence.
 *
 * The reasons are loaded once by the parent list and passed in, rather than once per donor.
 */

import { CircleAlert } from "lucide-react";
import { useState } from "react";

import { SelectField } from "@/components/form/SelectField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { DeferralReason, DeferralReasonOption } from "@/types/api";

interface DeferralActionProps {
  pledgeId: string;
  reasons: DeferralReasonOption[];
  onDone: () => void;
}

function describePeriod(option: DeferralReasonOption): string {
  if (option.deferral_days === null) return "The donor is deferred permanently.";
  if (option.deferral_days === 1) return "The donor is deferred for 1 day.";
  return `The donor is deferred for ${option.deferral_days} days.`;
}

export function DeferralAction({ pledgeId, reasons, onDone }: DeferralActionProps) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState<DeferralReason | "">("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chosen = reasons.find((option) => option.code === reason) ?? null;
  const fieldId = `deferral-${pledgeId}`;

  async function confirm() {
    if (!reason) {
      setError("Choose the reason.");
      return;
    }
    setWorking(true);
    setError(null);
    try {
      await api.post(`/pledges/${pledgeId}/deferred`, { reason });
      onDone();
    } catch (failure) {
      setError(
        failure instanceof ApiError ? failure.message : "Something went wrong. Please try again.",
      );
      setWorking(false);
    }
  }

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)} disabled={reasons.length === 0}>
        Deferred at screening
      </Button>
    );
  }

  return (
    <div className="w-full space-y-3 rounded-2xl bg-secondary p-4 text-sm text-ink" role="group" aria-label="Record a deferral">
      <p className="font-medium">Record that this donor could not give?</p>
      <div className="max-w-sm">
        <SelectField
          id={fieldId}
          label="Reason"
          value={reason}
          onChange={(event) => setReason(event.target.value as DeferralReason)}
        >
          <option value="" disabled>
            Choose a reason
          </option>
          {reasons.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </SelectField>
      </div>
      {chosen ? (
        <div className="space-y-1 text-ink-muted">
          <p>{describePeriod(chosen)} The unit goes to the next standby donor, who is texted.</p>
          {chosen.code === "positive_screen" ? (
            <p className="font-medium text-ink">
              BloodLink only asks the donor to contact you. Tell them the result in person, in
              confidence, and refer them for care.
            </p>
          ) : null}
        </div>
      ) : (
        <p className="text-ink-muted">Only the reason category is recorded, never a result.</p>
      )}
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-danger">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={working} onClick={() => void confirm()}>
          {working ? "Recording..." : "Record deferral"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={working}
          onClick={() => {
            setOpen(false);
            setError(null);
            setReason("");
          }}
        >
          Not now
        </Button>
      </div>
    </div>
  );
}
