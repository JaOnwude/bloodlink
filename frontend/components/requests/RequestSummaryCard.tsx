/**
 * One blood request in a list: what is needed, by when, and how far it has got.
 *
 * The whole card is a single link to the request's page, so it is one tab stop and one
 * large touch target. The deadline is shown relative to now ("in 3 hours") for open
 * requests, where that is what matters, and as a date otherwise.
 */

import { ChevronRight } from "lucide-react";
import Link from "next/link";

import { RequestStatusBadge, UrgencyBadge } from "@/components/requests/RequestBadges";
import { UnitsProgress } from "@/components/requests/UnitsProgress";
import { formatDateTime, formatRelative } from "@/lib/format";
import type { BloodRequest } from "@/types/api";

export function RequestSummaryCard({ request }: { request: BloodRequest }) {
  const isOpen = request.status === "open";

  return (
    <Link
      href={`/hospital/requests/${request.id}`}
      className="group block rounded-2xl border border-border bg-card p-5 shadow-soft transition-[box-shadow,border-color] duration-250 ease-brand outline-none hover:border-input hover:shadow-lift focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <div className="flex items-start gap-4">
        <span
          className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary-50 font-heading text-xl font-semibold text-primary-700"
          aria-hidden="true"
        >
          {request.recipient_group}
        </span>

        <div className="min-w-0 flex-1 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-heading text-lg font-semibold text-ink">
              <span className="sr-only">{request.recipient_group} </span>
              {request.component_name}
            </p>
            <RequestStatusBadge status={request.status} />
            {isOpen ? <UrgencyBadge urgency={request.urgency} /> : null}
          </div>

          <p className="text-sm text-ink-muted">
            {isOpen ? (
              <>
                Needed by {formatDateTime(request.deadline)} ({formatRelative(request.deadline)})
              </>
            ) : (
              <>Deadline was {formatDateTime(request.deadline)}</>
            )}
          </p>

          <div className="max-w-sm">
            <UnitsProgress needed={request.units_needed} pledged={request.units_pledged} compact />
          </div>
        </div>

        <ChevronRight
          className="mt-4 size-5 shrink-0 text-ink-muted transition-transform duration-250 group-hover:translate-x-1"
          aria-hidden="true"
        />
      </div>
    </Link>
  );
}
