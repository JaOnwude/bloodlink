/**
 * Shows whether the donor can give blood today and, if not, from when and why.
 *
 * The headline answers the question in one line. Below it, each kind of donation is listed
 * with its own status, because waiting periods differ (for example platelets can be given
 * more often than whole blood). The note at the end is deliberate: this is guidance based on
 * what the donor entered, and clinical staff decide on the day.
 */

import { CircleAlert, CircleCheck, Clock } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate } from "@/lib/format";
import type { Eligibility } from "@/types/api";

export function EligibilityCard({ eligibility }: { eligibility: Eligibility }) {
  // ISO dates sort correctly as plain text, so the earliest is simply the smallest.
  const upcomingDates = eligibility.components
    .map((item) => item.next_eligible_date)
    .filter((date): date is string => date !== null)
    .sort();
  const earliest = upcomingDates[0] ?? null;

  const state = eligibility.eligible_for_any
    ? {
        icon: <CircleCheck className="size-6" aria-hidden="true" />,
        tone: "bg-trust-50 text-trust-700",
        headline: "You can donate now",
      }
    : earliest
      ? {
          icon: <Clock className="size-6" aria-hidden="true" />,
          tone: "bg-primary-50 text-primary-700",
          headline: `You can donate again from ${formatDate(earliest)}`,
        }
      : {
          icon: <CircleAlert className="size-6" aria-hidden="true" />,
          tone: "bg-secondary text-ink",
          headline: "You are not eligible to donate at the moment",
        };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Your eligibility</CardTitle>
        <CardDescription>Based on the details in your profile.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className={`flex items-center gap-3 rounded-2xl p-4 ${state.tone}`}>
          {state.icon}
          <p className="font-heading text-lg font-semibold">{state.headline}</p>
        </div>

        {eligibility.blockers.length > 0 ? (
          <ul className="space-y-2 text-sm text-ink">
            {eligibility.blockers.map((reason) => (
              <li key={reason} className="flex gap-2">
                <span
                  className="mt-2 size-1.5 shrink-0 rounded-full bg-primary-600"
                  aria-hidden="true"
                />
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        ) : null}

        <ul className="divide-y divide-border rounded-2xl border border-border">
          {eligibility.components.map((item) => (
            <li
              key={item.component_code}
              className="flex items-center justify-between gap-4 px-4 py-3 text-sm"
            >
              <span className="font-medium text-ink">{item.component_name}</span>
              {item.eligible ? (
                <span className="rounded-full bg-trust-50 px-3 py-1 font-medium text-trust-700">
                  Eligible now
                </span>
              ) : item.next_eligible_date ? (
                <span className="text-ink-muted">From {formatDate(item.next_eligible_date)}</span>
              ) : (
                <span className="text-ink-muted">Not eligible</span>
              )}
            </li>
          ))}
        </ul>

        <p className="text-xs text-ink-muted">
          This is guidance only. Clinical staff make the final decision at the donation site.
        </p>
      </CardContent>
    </Card>
  );
}
