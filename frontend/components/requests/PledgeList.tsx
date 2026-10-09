/**
 * The donors who pledged to a request, with their contact details and the outcome controls.
 *
 * Staff see each pledged donor's name, phone number and email, because the donor chose to
 * share them by pledging. Contact details disappear when a donor cancels.
 *
 * For a pledge that is still waiting, staff record what happened:
 *
 * - "Donated" confirms the donation. It is recorded at once, because it is the common case
 *   and is what staff do with the donor standing in front of them.
 * - "Did not attend" asks for confirmation first, because it frees the unit for another
 *   donor and cannot be undone.
 *
 * After either, the parent reloads the request so its progress and state stay current.
 */

import { Mail, Phone, UserRound, Users } from "lucide-react";
import { useState } from "react";

import { ConfirmAction } from "@/components/form/ConfirmAction";
import { LoadError } from "@/components/layout/LoadError";
import { PledgeStatusBadge } from "@/components/requests/RequestBadges";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { HospitalPledge } from "@/types/api";

interface PledgeListProps {
  requestId: string;
  /** Called after an outcome is recorded, so the request can reload. */
  onChanged: () => void;
}

function DonatedButton({ pledgeId, onDone }: { pledgeId: string; onDone: () => void }) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setWorking(true);
    setError(null);
    try {
      await api.post(`/pledges/${pledgeId}/donated`);
      onDone();
    } catch (failure) {
      setError(
        failure instanceof ApiError ? failure.message : "Something went wrong. Please try again.",
      );
      setWorking(false);
    }
  }

  return (
    <div className="space-y-2">
      <Button size="sm" disabled={working} onClick={() => void confirm()}>
        {working ? "Recording..." : "Donated"}
      </Button>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function PledgeRow({ pledge, onChanged }: { pledge: HospitalPledge; onChanged: () => void }) {
  const { donor } = pledge;

  return (
    <li className="space-y-3 px-4 py-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-50 font-heading font-semibold text-primary-700">
          {donor.blood_group}
        </span>
        <div className="min-w-0 flex-1">
          <p className="flex items-center gap-1.5 font-medium text-ink">
            <UserRound className="size-4 text-ink-muted" aria-hidden="true" />
            {donor.full_name ?? "Donor withdrew"}
          </p>
          <p className="text-sm text-ink-muted">
            {donor.city} &middot; pledged {formatDateTime(pledge.pledged_at)}
          </p>
        </div>
        <PledgeStatusBadge status={pledge.status} />
      </div>

      {donor.phone || donor.email ? (
        <p className="flex flex-wrap gap-x-5 gap-y-1 pl-14 text-sm">
          {donor.phone ? (
            <a
              href={`tel:${donor.phone}`}
              className="inline-flex items-center gap-1.5 font-medium text-primary underline-offset-4 hover:underline"
            >
              <Phone className="size-4" aria-hidden="true" />
              {donor.phone}
            </a>
          ) : (
            <span className="text-ink-muted">No phone number given</span>
          )}
          {donor.email ? (
            <a
              href={`mailto:${donor.email}`}
              className="inline-flex items-center gap-1.5 font-medium text-primary underline-offset-4 hover:underline"
            >
              <Mail className="size-4" aria-hidden="true" />
              {donor.email}
            </a>
          ) : null}
        </p>
      ) : null}

      {pledge.status === "pledged" ? (
        <div className="flex flex-wrap items-start gap-2 pl-14">
          <DonatedButton pledgeId={pledge.id} onDone={onChanged} />
          <ConfirmAction
            label="Did not attend"
            title="Record that this donor did not attend?"
            description="The unit is released so another donor can pledge. This cannot be undone."
            confirmLabel="Yes, record it"
            workingLabel="Recording..."
            confirmVariant="destructive"
            cancelLabel="Not yet"
            onConfirm={async () => {
              await api.post(`/pledges/${pledge.id}/no-show`);
              onChanged();
            }}
          />
        </div>
      ) : pledge.resolved_at ? (
        <p className="pl-14 text-sm text-ink-muted">
          Recorded on {formatDateTime(pledge.resolved_at)}.
        </p>
      ) : null}
    </li>
  );
}

export function PledgeList({ requestId, onChanged }: PledgeListProps) {
  const pledges = useResource<HospitalPledge[]>(`/requests/${requestId}/pledges`);

  function handleChanged() {
    pledges.reload();
    onChanged();
  }

  if (!pledges.loaded) {
    return (
      <div className="space-y-3" role="status" aria-label="Loading pledges">
        <Skeleton className="h-20" />
        <Skeleton className="h-20" />
      </div>
    );
  }

  if (pledges.error || !pledges.data) {
    return (
      <LoadError
        message="We could not load the pledges. Check your connection and try again."
        onRetry={pledges.reload}
      />
    );
  }

  if (pledges.data.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-10 text-center">
        <Users className="size-8 text-ink-muted" aria-hidden="true" />
        <p className="text-ink">No donor has pledged yet.</p>
        <p className="max-w-md text-sm text-ink-muted">
          Pledged donors appear here with their phone number, so you can confirm they are on
          their way.
        </p>
      </div>
    );
  }

  return (
    <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">
      {pledges.data.map((pledge) => (
        <PledgeRow key={pledge.id} pledge={pledge} onChanged={handleChanged} />
      ))}
    </ul>
  );
}
