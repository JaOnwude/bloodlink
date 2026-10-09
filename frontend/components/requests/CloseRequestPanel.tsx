/**
 * Lets staff withdraw a request that is no longer needed.
 *
 * Closing stops the request reaching donors and cannot be undone, so it takes two steps:
 * the first button reveals a confirmation with the consequences spelled out. A failure is
 * shown in place and the request is left as it was.
 */

import { CircleAlert } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { BloodRequest } from "@/types/api";

interface CloseRequestPanelProps {
  request: BloodRequest;
  /** Called after the request has been closed, so the page can reload it. */
  onClosed: () => void;
}

export function CloseRequestPanel({ request, onClosed }: CloseRequestPanelProps) {
  const [confirming, setConfirming] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function close() {
    setWorking(true);
    setError(null);
    try {
      await api.post<BloodRequest>(`/requests/${request.id}/close`);
      onClosed();
    } catch (failure) {
      setError(
        failure instanceof ApiError ? failure.message : "Something went wrong. Please try again.",
      );
      setWorking(false);
    }
  }

  if (!confirming) {
    return (
      <Button variant="outline" size="sm" onClick={() => setConfirming(true)}>
        Close request
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-2xl bg-secondary p-4 text-sm text-ink" role="group">
      <p className="font-medium">Close this request?</p>
      <p className="text-ink-muted">
        {request.status === "open"
          ? "Donors will no longer be able to pledge to it. This cannot be undone."
          : "It is already fulfilled. Closing it marks the need as finished. This cannot be undone."}
      </p>
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-danger">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button variant="destructive" size="sm" disabled={working} onClick={() => void close()}>
          {working ? "Closing..." : "Yes, close it"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={working}
          onClick={() => {
            setConfirming(false);
            setError(null);
          }}
        >
          Keep it open
        </Button>
      </div>
    </div>
  );
}
