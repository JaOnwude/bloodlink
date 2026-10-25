/**
 * Families' appeals waiting at this hospital, for staff to confirm or decline.
 *
 * An appeal comes from the public page, so it alerts nobody until a member of staff checks
 * the patient on the ward (the family gives the ward, bed or lab slip number) and approves
 * it. Approving raises an ordinary blood request, so the usual limits, audit trail and
 * donor alerts apply; staff choose the urgency and deadline, and may correct the units.
 * Declining needs a reason, which the family is shown and texted.
 *
 * The family's name and phone number are shown here so staff can call back.
 */

import { Phone } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { FormField } from "@/components/auth/FormField";
import { SelectField } from "@/components/form/SelectField";
import { TextareaField } from "@/components/form/TextareaField";
import { LoadError } from "@/components/layout/LoadError";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { formatRelative, toLocalInputValue } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { FamilyRequest, RequestUrgency } from "@/types/api";

/** The deadline offered by default when approving: twelve hours from now. */
const DEFAULT_DEADLINE_HOURS = 12;

function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

function Decision({ appeal, onDone }: { appeal: FamilyRequest; onDone: () => void }) {
  const [mode, setMode] = useState<"idle" | "approve" | "decline">("idle");
  const [urgency, setUrgency] = useState<RequestUrgency>("urgent");
  const [deadline, setDeadline] = useState(() =>
    toLocalInputValue(new Date(Date.now() + DEFAULT_DEADLINE_HOURS * 60 * 60 * 1000)),
  );
  const [units, setUnits] = useState(String(appeal.units_needed));
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function approve() {
    setBusy(true);
    setError(null);
    try {
      await api.post(`/family-requests/${appeal.id}/approve`, {
        urgency,
        deadline: new Date(deadline).toISOString(),
        units_needed: Number(units),
      });
      onDone();
    } catch (failure) {
      setError(errorMessage(failure));
      setBusy(false);
    }
  }

  async function decline() {
    if (reason.trim().length < 5) {
      setError("Give the family a reason of at least a few words.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.post(`/family-requests/${appeal.id}/decline`, { reason: reason.trim() });
      onDone();
    } catch (failure) {
      setError(errorMessage(failure));
      setBusy(false);
    }
  }

  if (mode === "idle") {
    return (
      <div className="flex flex-wrap gap-3">
        <Button type="button" size="sm" onClick={() => setMode("approve")}>
          Patient confirmed: alert donors
        </Button>
        <Button type="button" size="sm" variant="outline" onClick={() => setMode("decline")}>
          Decline
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl bg-background p-4 ring-1 ring-border">
      {mode === "approve" ? (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <SelectField
              id={`urgency-${appeal.id}`}
              label="Urgency"
              value={urgency}
              onChange={(event) => setUrgency(event.target.value as RequestUrgency)}
            >
              <option value="critical">Critical</option>
              <option value="urgent">Urgent</option>
              <option value="routine">Routine</option>
            </SelectField>
            <FormField
              id={`deadline-${appeal.id}`}
              label="Needed by"
              type="datetime-local"
              value={deadline}
              onChange={(event) => setDeadline(event.target.value)}
            />
            <FormField
              id={`units-${appeal.id}`}
              label="Units"
              type="number"
              min={1}
              max={20}
              value={units}
              onChange={(event) => setUnits(event.target.value)}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button type="button" size="sm" disabled={busy} onClick={() => void approve()}>
              {busy ? "Raising the request..." : "Raise request and alert donors"}
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setMode("idle")}>
              Back
            </Button>
          </div>
        </>
      ) : (
        <>
          <TextareaField
            id={`reason-${appeal.id}`}
            label="Reason, shown to the family"
            rows={2}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="button" size="sm" disabled={busy} onClick={() => void decline()}>
              {busy ? "Declining..." : "Decline request"}
            </Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setMode("idle")}>
              Back
            </Button>
          </div>
        </>
      )}
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function AppealCard({ appeal, onDone }: { appeal: FamilyRequest; onDone: () => void }) {
  return (
    <li className="space-y-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <p className="font-heading text-lg font-semibold text-ink">
            {appeal.units_needed} × {appeal.recipient_group} {appeal.component_name.toLowerCase()}
          </p>
          <p className="text-sm text-ink">Ward or reference: {appeal.ward_reference}</p>
          {appeal.notes ? <p className="text-sm text-ink-muted">“{appeal.notes}”</p> : null}
        </div>
        <span className="text-xs text-ink-muted">{formatRelative(appeal.created_at)}</span>
      </div>
      <p className="flex flex-wrap items-center gap-2 text-sm text-ink-muted">
        From {appeal.requester_name}
        <a
          href={`tel:${appeal.requester_phone}`}
          className="inline-flex items-center gap-1 font-medium text-primary hover:underline"
        >
          <Phone className="size-3.5" aria-hidden="true" />
          {appeal.requester_phone}
        </a>
      </p>
      {appeal.status === "pending" ? (
        <Decision appeal={appeal} onDone={onDone} />
      ) : appeal.status === "approved" && appeal.blood_request_id ? (
        <Link
          href={`/hospital/requests/${appeal.blood_request_id}`}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          Approved: open the request
        </Link>
      ) : (
        <p className="text-sm text-ink-muted">Declined: {appeal.decline_reason}</p>
      )}
    </li>
  );
}

export function FamilyRequestsPanel() {
  const appeals = useResource<FamilyRequest[]>("/family-requests");

  if (!appeals.loaded) return <Skeleton className="h-40 rounded-2xl" />;
  if (appeals.error || !appeals.data) {
    return (
      <LoadError
        message="We could not load requests from families. Check your connection and try again."
        onRetry={appeals.reload}
      />
    );
  }

  const waiting = appeals.data.filter((appeal) => appeal.status === "pending");
  const recent = appeals.data.filter((appeal) => appeal.status !== "pending").slice(0, 3);

  return (
    <section className="space-y-4" aria-labelledby="family-heading">
      <div className="space-y-1">
        <h2 id="family-heading" className="text-heading font-semibold text-ink">
          Requests from families
          {waiting.length > 0 ? (
            <span className="ml-2 rounded-full bg-primary px-2 py-0.5 align-middle text-sm text-white">
              {waiting.length}
            </span>
          ) : null}
        </h2>
        <p className="text-sm text-ink-muted">
          Families ask from BloodLink&apos;s public page. Nobody is alerted until you confirm the
          patient is on your ward.
        </p>
      </div>
      {waiting.length === 0 && recent.length === 0 ? (
        <p className="text-sm text-ink-muted">No requests from families yet.</p>
      ) : (
        <ul className="space-y-3">
          {[...waiting, ...recent].map((appeal) => (
            <AppealCard key={appeal.id} appeal={appeal} onDone={appeals.reload} />
          ))}
        </ul>
      )}
    </section>
  );
}
