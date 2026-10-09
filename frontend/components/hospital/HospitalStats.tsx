/**
 * A hospital's performance at a glance: how often requests are met, how fast, and how
 * reliable pledged donors are.
 *
 * Each figure is a headline number with a one-line explanation of what it counts, so it can
 * be read without a chart. Numbers wear the text colours; nothing here relies on colour.
 * When a rate cannot be measured yet (for example no request has finished), it says so in
 * words instead of showing a misleading 0%.
 *
 * The period buttons choose how far back to look: 30, 90 or 365 days.
 */

import { useState } from "react";

import { LoadError } from "@/components/layout/LoadError";
import { Skeleton } from "@/components/ui/skeleton";
import { formatMinutes, formatPercent } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { HospitalStats as Stats } from "@/types/api";

const PERIODS = [
  { days: 30, label: "30 days" },
  { days: 90, label: "90 days" },
  { days: 365, label: "12 months" },
];

interface TileProps {
  label: string;
  value: string;
  detail: string;
}

function Tile({ label, value, detail }: TileProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="mt-2 font-heading text-3xl font-semibold text-ink tabular-nums">{value}</dd>
      <dd className="mt-1 text-sm text-ink-muted">{detail}</dd>
    </div>
  );
}

function tiles(stats: Stats): TileProps[] {
  const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? "" : "s"}`;
  return [
    {
      label: "Requests met",
      value: stats.fulfilment_rate === null ? "–" : formatPercent(stats.fulfilment_rate),
      detail:
        stats.fulfilment_rate === null
          ? "Shown once a request has finished."
          : `${stats.requests_fulfilled} of ${plural(stats.requests_finished, "finished request")} got every unit.`,
    },
    {
      label: "Median time to fulfil",
      value:
        stats.median_minutes_to_fulfil === null ? "–" : formatMinutes(stats.median_minutes_to_fulfil),
      detail:
        stats.median_minutes_to_fulfil === null
          ? "Shown once a request has been fulfilled."
          : "From raising a request to the last unit pledged.",
    },
    {
      label: "Did not attend",
      value: stats.no_show_rate === null ? "–" : formatPercent(stats.no_show_rate),
      detail:
        stats.no_show_rate === null
          ? "Shown once a pledge has an outcome."
          : `${stats.no_shows} of ${plural(stats.pledges_resolved, "recorded pledge")}.`,
    },
    {
      label: "Units donated",
      value: String(stats.units_donated),
      detail: `Confirmed donations from ${plural(stats.requests_raised, "request")} raised.`,
    },
    {
      label: "Open now",
      value: String(stats.requests_open),
      detail: "Requests still waiting for donors.",
    },
    {
      label: "Donors texted",
      value: String(stats.donors_alerted),
      detail: "Different donors who received an alert.",
    },
  ];
}

export function HospitalStats() {
  const [days, setDays] = useState(30);
  const stats = useResource<Stats>(`/stats/hospital?days=${days}`);

  return (
    <section aria-labelledby="stats-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 id="stats-heading" className="text-heading font-semibold text-ink">
          How your requests are doing
        </h2>
        <div role="group" aria-label="Period" className="flex flex-wrap gap-2">
          {PERIODS.map((period) => (
            <button
              key={period.days}
              type="button"
              aria-pressed={days === period.days}
              onClick={() => setDays(period.days)}
              className={`rounded-full border px-4 py-1.5 text-sm font-medium transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
                days === period.days
                  ? "border-ink bg-ink text-background"
                  : "border-input bg-surface text-ink hover:bg-muted"
              }`}
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>

      {!stats.loaded ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" role="status" aria-label="Loading figures">
          {PERIODS.concat(PERIODS).map((_, index) => (
            <Skeleton key={index} className="h-36" />
          ))}
        </div>
      ) : stats.error || !stats.data ? (
        <LoadError
          message="We could not load your figures. Check your connection and try again."
          onRetry={stats.reload}
        />
      ) : (
        <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {tiles(stats.data).map((tile) => (
            <Tile key={tile.label} {...tile} />
          ))}
        </dl>
      )}
      <p className="text-sm text-ink-muted">
        Figures cover requests raised in the period. Open requests are left out of the rates
        until they finish.
      </p>
    </section>
  );
}
