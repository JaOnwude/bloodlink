/**
 * One open request a donor can answer, with the button to pledge or to cancel.
 *
 * Pledging is a commitment to travel to the hospital before the deadline, so it takes a
 * confirmation that says so, and reminds the donor that clinical staff make the final
 * decision on the day. Once pledged, the card shows where to go and whom to call.
 *
 * Once every unit is pledged, a request with standby places offers "Join the standby list"
 * instead: the donor waits in reserve and is texted if a pledged donor cannot give.
 *
 * When the server refuses (for example someone else took the last unit a moment earlier),
 * its message is shown in the confirmation panel and the list is refreshed.
 */

import { HeartHandshake, Hourglass, MapPin } from "lucide-react";

import { HospitalContact } from "@/components/donor/HospitalContact";
import { ConfirmAction } from "@/components/form/ConfirmAction";
import { UrgencyBadge } from "@/components/requests/RequestBadges";
import { ApiError, api } from "@/lib/api";
import { formatDateTime, formatRelative, withArticle } from "@/lib/format";
import type { OpenRequestForDonor } from "@/types/api";

interface OpenRequestCardProps {
  request: OpenRequestForDonor;
  /** True when the donor holds a pledge for another request, which blocks a new one. */
  pledgedElsewhere: boolean;
  /** Called after a pledge or cancellation, so the lists can reload. */
  onChanged: () => void;
}

export function OpenRequestCard({ request, pledgedElsewhere, onChanged }: OpenRequestCardProps) {
  const pledged = request.my_pledge_id !== null;
  const onStandby = request.my_pledge_status === "standby";
  const units = request.units_remaining;
  // Every unit is pledged, but the hospital still wants donors in reserve.
  const standbyOnly = !pledged && units === 0 && request.standby_places_left > 0;
  const places = request.standby_places_left;

  async function pledge() {
    try {
      await api.post(`/requests/${request.id}/pledges`);
    } catch (error) {
      // A conflict means the request changed under us (filled, closed); refresh the list.
      if (error instanceof ApiError && error.status === 409) onChanged();
      throw error;
    }
    onChanged();
  }

  async function cancel() {
    await api.delete(`/pledges/${request.my_pledge_id}`);
    onChanged();
  }

  return (
    <article
      className={`space-y-4 rounded-2xl border bg-card p-5 shadow-soft ${
        pledged ? "border-primary-600" : "border-border"
      }`}
      aria-labelledby={`request-${request.id}`}
    >
      <div className="flex items-start gap-4">
        <span
          className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary-50 font-heading text-xl font-semibold text-primary-700"
          aria-hidden="true"
        >
          {request.recipient_group}
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 id={`request-${request.id}`} className="font-heading text-lg font-semibold text-ink">
              {request.hospital.name}
            </h3>
            <UrgencyBadge urgency={request.urgency} />
          </div>
          <p className="text-sm text-ink-muted">
            {request.component_name} for {withArticle(request.recipient_group)} patient &middot;{" "}
            {units > 0
              ? `${units} ${units === 1 ? "unit" : "units"} still needed`
              : `All units pledged · ${places} standby ${places === 1 ? "place" : "places"} left`}
          </p>
          <p className="flex items-center gap-1 text-sm text-ink-muted">
            <MapPin className="size-3.5" aria-hidden="true" />
            {request.distance_km < 1 ? "Under 1 km" : `${request.distance_km.toFixed(1)} km`} away
            in {request.hospital.city}
          </p>
          <p className="text-sm text-ink-muted">
            Needed by {formatDateTime(request.deadline)} ({formatRelative(request.deadline)})
          </p>
        </div>
      </div>

      {request.notes ? (
        <p className="rounded-xl bg-secondary px-4 py-3 text-sm whitespace-pre-line text-ink">
          {request.notes}
        </p>
      ) : null}

      {pledged && onStandby ? (
        <div className="space-y-4">
          <p className="flex items-center gap-2 text-sm font-medium text-ink">
            <Hourglass className="size-4" aria-hidden="true" />
            You are on standby. If a pledged donor cannot give, you will be texted and asked to
            come.
          </p>
          <HospitalContact hospital={request.hospital} />
          <ConfirmAction
            label="Step down from standby"
            variant="ghost"
            title="Step down from standby?"
            description="Your standby place goes back to other donors. You can pledge to other requests straight away."
            confirmLabel="Yes, step down"
            workingLabel="Stepping down..."
            confirmVariant="destructive"
            cancelLabel="Stay on standby"
            onConfirm={cancel}
          />
        </div>
      ) : pledged ? (
        <div className="space-y-4">
          <p className="flex items-center gap-2 text-sm font-medium text-primary-700">
            <HeartHandshake className="size-4" aria-hidden="true" />
            You pledged to this request. Thank you.
          </p>
          <HospitalContact hospital={request.hospital} />
          <ConfirmAction
            label="Cancel my pledge"
            variant="ghost"
            title="Cancel your pledge?"
            description="The hospital will be told you are no longer coming, and your unit goes to a standby donor or back to other donors."
            confirmLabel="Yes, cancel it"
            workingLabel="Cancelling..."
            confirmVariant="destructive"
            cancelLabel="Keep my pledge"
            onConfirm={cancel}
          />
        </div>
      ) : pledgedElsewhere ? (
        <p className="text-sm text-ink-muted">
          You already have a pledge waiting for another request. You can pledge again once it is
          resolved or cancelled.
        </p>
      ) : standbyOnly ? (
        <ConfirmAction
          label="Join the standby list"
          variant="outline"
          size="default"
          title={`Join the standby list at ${request.hospital.name}?`}
          description={
            <div className="space-y-2">
              <p>
                Every unit is pledged, but some donors are turned away at screening or cannot
                come. If that happens before {formatDateTime(request.deadline)}, you will be
                texted and asked to come in their place.
              </p>
              <p>
                Your name and phone number will be shared with the hospital. While you are on
                standby you cannot pledge to another request; you can step down at any time.
              </p>
            </div>
          }
          confirmLabel="Join the standby list"
          workingLabel="Joining..."
          onConfirm={pledge}
        />
      ) : (
        <ConfirmAction
          label="I can donate"
          variant="default"
          size="default"
          title={`Pledge to ${request.hospital.name}?`}
          description={
            <div className="space-y-2">
              <p>
                You are committing to go to the hospital before{" "}
                {formatDateTime(request.deadline)}. Your name and phone number will be shared
                with the hospital so they can reach you.
              </p>
              <p>Clinical staff at the hospital make the final decision on whether you can give.</p>
            </div>
          }
          confirmLabel="Confirm my pledge"
          workingLabel="Pledging..."
          onConfirm={pledge}
        />
      )}
    </article>
  );
}
