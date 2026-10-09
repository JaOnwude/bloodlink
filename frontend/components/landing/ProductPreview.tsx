/**
 * A drawing of BloodLink's request screen, for the landing page.
 *
 * It shows what a hospital actually gets (a request, its progress, the donors who pledged
 * and the ones matched nearby) instead of a stock photograph. It is built from the same
 * badges and progress bar as the real screen, so it stays in step with the product, and it
 * is marked as an example so nobody mistakes it for live data. The names are invented.
 *
 * Screen readers get one sentence describing the picture rather than every detail in it.
 */

import { MapPin, MessageSquareText, UserRound } from "lucide-react";

import { PledgeStatusBadge, RequestStatusBadge, UrgencyBadge } from "@/components/requests/RequestBadges";
import { UnitsProgress } from "@/components/requests/UnitsProgress";

const PLEDGED = [
  { name: "Adaeze N.", group: "O-", km: "3.1" },
  { name: "Musa B.", group: "O-", km: "6.4" },
];

const MATCHED = [
  { group: "O-", area: "Yaba", km: "4.8" },
  { group: "O-", area: "Surulere", km: "7.2" },
];

export function ProductPreview() {
  return (
    <div
      role="img"
      aria-label="Example of a BloodLink request: an O-negative whole blood request marked critical, with two donors pledged and more matched nearby."
      className="relative mx-auto w-full max-w-md"
    >
      <div className="absolute -inset-4 -z-10 rounded-[2rem] bg-linear-to-br from-primary-100 via-primary-50 to-transparent blur-2xl" />

      <div aria-hidden="true" className="space-y-5 rounded-3xl border border-border bg-surface p-6 shadow-pop">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold tracking-wider text-ink-muted uppercase">Example</span>
          <span className="text-xs text-ink-muted">Lagoon Specialist Hospital</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="font-heading text-2xl font-semibold text-ink">O- whole blood</span>
          <RequestStatusBadge status="fulfilled" />
          <UrgencyBadge urgency="critical" />
        </div>

        <UnitsProgress needed={2} pledged={2} />

        <div className="space-y-2">
          <p className="text-xs font-semibold tracking-wider text-ink-muted uppercase">Pledged</p>
          <ul className="divide-y divide-border rounded-2xl border border-border">
            {PLEDGED.map((donor) => (
              <li key={donor.name} className="flex items-center gap-3 px-3 py-2.5 text-sm">
                <UserRound className="size-4 text-ink-muted" />
                <span className="flex-1 font-medium text-ink">{donor.name}</span>
                <span className="text-ink-muted tabular-nums">{donor.km} km</span>
                <PledgeStatusBadge status={donor.name.startsWith("A") ? "donated" : "pledged"} />
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-semibold tracking-wider text-ink-muted uppercase">Also matched nearby</p>
          <ul className="space-y-1.5">
            {MATCHED.map((donor) => (
              <li key={donor.area} className="flex items-center gap-3 text-sm text-ink-muted">
                <span className="flex size-7 items-center justify-center rounded-lg bg-primary-50 text-xs font-semibold text-primary-700">
                  {donor.group}
                </span>
                <MapPin className="size-3.5" />
                <span className="flex-1">{donor.area}</span>
                <span className="tabular-nums">{donor.km} km</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="flex items-center gap-2 border-t border-border pt-4 text-sm text-ink-muted">
          <MessageSquareText className="size-4" />
          14 matched donors texted
        </p>
      </div>
    </div>
  );
}
