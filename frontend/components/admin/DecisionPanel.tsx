/**
 * The administrator's decision controls for one hospital.
 *
 * Verifying asks for a confirmation, because a verified hospital's requests reach donors.
 * Rejecting (or revoking an earlier verification) requires a written reason, which is shown
 * to the hospital's staff so they can correct and resubmit. The server records every
 * decision in the audit log with who made it.
 *
 * After any attempt, including a failed one, the parent is told to reload, so the screen
 * always reflects the current state (for example if another administrator acted first).
 */

import { CircleAlert } from "lucide-react";
import { useState } from "react";

import { TextareaField } from "@/components/form/TextareaField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { failureFromError } from "@/lib/forms";
import type { AdminHospital } from "@/types/api";

type Mode = "idle" | "confirm-verify" | "reject";

const MIN_REASON_LENGTH = 5;

interface DecisionPanelProps {
  hospital: AdminHospital;
  /** Called after an attempt so the parent can reload. Receives a message on success. */
  onChanged: (successMessage?: string) => void;
}

export function DecisionPanel({ hospital, onChanged }: DecisionPanelProps) {
  const [mode, setMode] = useState<Mode>("idle");
  const [reason, setReason] = useState("");
  const [reasonError, setReasonError] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = hospital.verification_status;
  const rejectLabel = status === "verified" ? "Revoke verification" : "Reject hospital";

  function cancel() {
    setMode("idle");
    setReason("");
    setReasonError(undefined);
    setError(null);
  }

  async function verify() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/admin/hospitals/${hospital.id}/verify`);
      setMode("idle");
      onChanged(`${hospital.name} is now verified.`);
    } catch (failure) {
      setError(failure instanceof ApiError ? failure.message : "Could not verify. Try again.");
      setMode("idle");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setReasonError(`Write a reason of at least ${MIN_REASON_LENGTH} characters.`);
      return;
    }
    setBusy(true);
    setError(null);
    setReasonError(undefined);
    try {
      await api.post(`/admin/hospitals/${hospital.id}/reject`, { reason: reason.trim() });
      const message =
        status === "verified"
          ? `Verification of ${hospital.name} has been revoked.`
          : `${hospital.name} has been rejected. Its staff can see your reason.`;
      cancel();
      onChanged(message);
    } catch (failure) {
      const problem = failureFromError(failure);
      if (problem.fields.reason) setReasonError(problem.fields.reason);
      else setError(problem.general ?? "Could not save the decision. Try again.");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-primary-50 p-4 text-sm text-primary-900"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      ) : null}

      {mode === "idle" ? (
        <div className="flex flex-wrap gap-3">
          {status !== "verified" ? (
            <Button onClick={() => setMode("confirm-verify")}>
              {status === "rejected" ? "Verify instead" : "Verify hospital"}
            </Button>
          ) : null}
          {status !== "rejected" ? (
            <Button variant="outline" onClick={() => setMode("reject")}>
              {rejectLabel}
            </Button>
          ) : null}
        </div>
      ) : null}

      {status === "rejected" && mode === "idle" ? (
        <p className="text-sm text-ink-muted">
          The hospital has been asked to correct its details. It returns to the queue when its
          staff resubmit.
        </p>
      ) : null}

      {mode === "confirm-verify" ? (
        <div className="space-y-4 rounded-2xl border border-border bg-surface p-4">
          <p className="text-sm text-ink">
            Verify <strong>{hospital.name}</strong>? Donors will receive its blood requests as
            coming from a verified hospital. Check its registration number and location first.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button onClick={() => void verify()} disabled={busy}>
              {busy ? "Verifying..." : "Yes, verify"}
            </Button>
            <Button variant="ghost" onClick={cancel} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      {mode === "reject" ? (
        <div className="space-y-4 rounded-2xl border border-border bg-surface p-4">
          <TextareaField
            id="reason"
            name="reason"
            label="Reason"
            hint="The hospital's staff will see this. Be specific, so they know what to correct."
            autoFocus
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            error={reasonError}
          />
          <div className="flex flex-wrap gap-3">
            <Button variant="destructive" onClick={() => void reject()} disabled={busy}>
              {busy ? "Saving..." : rejectLabel}
            </Button>
            <Button variant="ghost" onClick={cancel} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
