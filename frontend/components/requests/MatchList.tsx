/**
 * The donors who can answer an open request, nearest first.
 *
 * Staff can widen or narrow the search radius. The list is anonymous on purpose: it shows
 * each donor's blood group, city and distance only. A hospital sees a donor's name and phone
 * number only after that donor pledges, so donors stay in control of who can contact them.
 *
 * Every donor shown is compatible with the patient, available, has agreed to be contacted
 * and is eligible to give the requested component today; the server applies those rules.
 *
 * Below the list, the alert panel shows how many donors have been texted and can text the
 * donors at the chosen radius who have not been alerted yet.
 */

import { MapPin, ShieldCheck, Users } from "lucide-react";
import { useState } from "react";

import { SelectField } from "@/components/form/SelectField";
import { AlertPanel } from "@/components/requests/AlertPanel";
import { LoadError } from "@/components/layout/LoadError";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { MatchesResponse } from "@/types/api";

/** Search radii offered, in kilometres. The server accepts up to 200. */
const RADIUS_CHOICES = [10, 25, 50, 100, 200];
const DEFAULT_RADIUS = 25;

function formatDistance(km: number): string {
  return km < 1 ? "under 1 km" : `${km.toFixed(1)} km`;
}

export function MatchList({ requestId }: { requestId: string }) {
  const [radius, setRadius] = useState(DEFAULT_RADIUS);
  const matches = useResource<MatchesResponse>(
    `/requests/${requestId}/matches?radius_km=${radius}`,
  );

  return (
    <div className="space-y-5">
      <div className="max-w-xs">
        <SelectField
          id="radius"
          label="Search within"
          value={String(radius)}
          onChange={(event) => setRadius(Number(event.target.value))}
        >
          {RADIUS_CHOICES.map((choice) => (
            <option key={choice} value={choice}>
              {choice} km of your hospital
            </option>
          ))}
        </SelectField>
      </div>

      {!matches.loaded ? (
        <div className="space-y-3" role="status" aria-label="Finding donors">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : matches.error || !matches.data ? (
        <LoadError
          message="We could not find donors just now. Check your connection and try again."
          onRetry={matches.reload}
        />
      ) : matches.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-10 text-center">
          <Users className="size-8 text-ink-muted" aria-hidden="true" />
          <p className="text-ink">No eligible donors within {matches.data.radius_km} km yet.</p>
          <p className="max-w-md text-sm text-ink-muted">
            Try a wider radius. Donors who become eligible or turn their alerts on later will
            appear here.
          </p>
        </div>
      ) : (
        <>
          <p className="text-sm text-ink-muted" aria-live="polite">
            <span className="font-medium text-ink">{matches.data.total}</span>{" "}
            {matches.data.total === 1 ? "donor" : "donors"} within {matches.data.radius_km} km
            {matches.data.total > matches.data.items.length
              ? `, nearest ${matches.data.items.length} shown`
              : ""}
            .
          </p>
          <ol className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">
            {matches.data.items.map((match, index) => (
              <li key={match.donor_id} className="flex items-center gap-4 px-4 py-3">
                <span className="w-6 text-right text-sm text-ink-muted tabular-nums">
                  {index + 1}
                </span>
                <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-primary-50 font-heading font-semibold text-primary-700">
                  {match.blood_group}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-ink">
                    Donor, {match.blood_group}
                  </span>
                  <span className="flex items-center gap-1 text-sm text-ink-muted">
                    <MapPin className="size-3.5" aria-hidden="true" />
                    {match.city}
                  </span>
                </span>
                <span className="text-sm font-medium text-ink tabular-nums">
                  {formatDistance(match.distance_km)}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}

      <AlertPanel requestId={requestId} radiusKm={radius} />

      <p className="flex items-start gap-2 text-sm text-ink-muted">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-trust-600" aria-hidden="true" />
        <span>
          Donors stay anonymous until they pledge. You will see a donor&apos;s name and phone
          number once they commit to this request.
        </span>
      </p>
    </div>
  );
}
