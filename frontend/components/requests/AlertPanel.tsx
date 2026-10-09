/**
 * How many donors have been texted about a request, and a button to text more.
 *
 * Donors are alerted automatically when the request is raised. Staff can alert again at
 * the radius chosen in the match list, which texts only the donors not alerted before: the
 * server guarantees no donor is messaged twice about the same request, so the button is
 * safe to press more than once.
 *
 * When SMS is not configured (the server reports the "console" sender), the panel says
 * plainly that messages are recorded but not delivered, so nobody mistakes a demonstration
 * for real alerts.
 */

import { CircleAlert, MessageSquareText } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { AlertRun, AlertSummary } from "@/types/api";

interface AlertPanelProps {
  requestId: string;
  /** The radius currently chosen in the match list, in kilometres. */
  radiusKm: number;
}

function describeRun(run: AlertRun): string {
  if (run.newly_alerted === 0) {
    if (run.matched === 0) return "No matching donors to text at this radius.";
    if (run.without_phone === run.matched) return "None of these donors has given a phone number.";
    return "Every matching donor with a phone number has already been texted.";
  }
  const people = run.newly_alerted === 1 ? "donor" : "donors";
  const failed = run.failed > 0 ? ` ${run.failed} could not be delivered.` : "";
  return `Texted ${run.newly_alerted} more ${people}.${failed}`;
}

export function AlertPanel({ requestId, radiusKm }: AlertPanelProps) {
  const summary = useResource<AlertSummary>(`/requests/${requestId}/alerts`);
  const [working, setWorking] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function alertDonors() {
    setWorking(true);
    setMessage(null);
    setError(null);
    try {
      const run = await api.post<AlertRun>(`/requests/${requestId}/alerts`, undefined, {
        query: { radius_km: radiusKm },
      });
      setMessage(describeRun(run));
      summary.reload();
    } catch (failure) {
      setError(
        failure instanceof ApiError ? failure.message : "Something went wrong. Please try again.",
      );
    } finally {
      setWorking(false);
    }
  }

  const totals = summary.data;

  return (
    <div className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="flex items-center gap-2 text-sm text-ink" aria-live="polite">
          <MessageSquareText className="size-4 text-ink-muted" aria-hidden="true" />
          {!totals ? (
            "Checking alerts..."
          ) : totals.total === 0 ? (
            "No donor has been texted yet."
          ) : (
            <span>
              <span className="font-medium">{totals.sent}</span>{" "}
              {totals.sent === 1 ? "donor" : "donors"} texted
              {totals.failed > 0 ? `, ${totals.failed} not delivered` : ""}
            </span>
          )}
        </p>
        <Button variant="outline" size="sm" disabled={working} onClick={() => void alertDonors()}>
          {working ? "Texting..." : `Text donors within ${radiusKm} km`}
        </Button>
      </div>

      {totals?.provider === "console" ? (
        <p className="text-sm text-ink-muted">
          Text messages are switched off on this server, so alerts are recorded but not
          delivered.
        </p>
      ) : null}
      {message ? <p className="text-sm text-ink">{message}</p> : null}
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-sm text-danger">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
    </div>
  );
}
