/**
 * How many donors the hospital can reach, ring by postcode ring.
 *
 * Each row is one ring of the hospital's NIPOST postcode: its own area, its district, its
 * LGA and its state, each counting the narrower rings inside it. Alerts go out in the same
 * order, so the rows read as "who hears first". Blood groups are listed per ring, so a gap
 * (no O-negative donors in the LGA, say) shows where a blood drive would help most.
 *
 * Counts only: no donor is named or located. Donors who paused alerts or did not agree to
 * be contacted are not counted, because they could not be reached.
 */

import { LoadError } from "@/components/layout/LoadError";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import { BLOOD_GROUPS } from "@/types/api";
import type { Coverage, PostcodeRing, RingCoverage } from "@/types/api";

const RING_TITLES: Record<PostcodeRing, string> = {
  area: "Your postcode area",
  district: "Your district",
  lga: "Your LGA",
  state: "Your state",
};

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function RingRow({ ring }: { ring: RingCoverage }) {
  const groups = BLOOD_GROUPS.filter((group) => (ring.by_group[group] ?? 0) > 0);
  return (
    <li className="flex flex-wrap items-start justify-between gap-x-6 gap-y-2 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink">
          {RING_TITLES[ring.ring]}
          {ring.name ? <span className="font-normal text-ink-muted"> · {ring.name}</span> : null}
        </p>
        <p className="font-mono text-xs text-ink-muted">{ring.prefix}</p>
      </div>
      <div className="text-right">
        <p className="font-heading text-lg font-semibold text-ink tabular-nums">
          {plural(ring.total, "donor")}
        </p>
        <p className="text-xs text-ink-muted">
          {groups.length > 0
            ? groups.map((group) => `${group} ${ring.by_group[group]}`).join(" · ")
            : "None yet"}
        </p>
      </div>
    </li>
  );
}

export function DonorCoverage() {
  const coverage = useResource<Coverage>("/stats/coverage");

  if (!coverage.loaded) return <Skeleton className="h-64 rounded-2xl" />;
  if (coverage.error || !coverage.data) {
    return (
      <LoadError
        message="We could not load your donor coverage. Check your connection and try again."
        onRetry={coverage.reload}
      />
    );
  }

  const data = coverage.data;
  return (
    <section className="space-y-4" aria-labelledby="coverage-heading">
      <div className="space-y-1">
        <h2 id="coverage-heading" className="text-heading font-semibold text-ink">
          Donors you can reach, by postcode
        </h2>
        <p className="text-sm text-ink-muted">
          {data.postcode
            ? `Counted from NIPOST postcode ${data.postcode}. Alerts reach your own area first, then widen ring by ring.`
            : "Add your NIPOST postcode to see donors ring by ring around your building."}
        </p>
      </div>

      {data.rings.length > 0 ? (
        <ol className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">
          {data.rings.map((ring) => (
            <RingRow key={ring.ring} ring={ring} />
          ))}
        </ol>
      ) : null}

      <p className="text-sm text-ink-muted">
        {data.without_postcode_nearby > 0
          ? `${plural(data.without_postcode_nearby, "more donor")} within ${data.radius_km} km ${
              data.without_postcode_nearby === 1 ? "has" : "have"
            } not added a postcode yet. They are still matched by distance.`
          : `Every reachable donor within ${data.radius_km} km has added a postcode.`}
      </p>
    </section>
  );
}
