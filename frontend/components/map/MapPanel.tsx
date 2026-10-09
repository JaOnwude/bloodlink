/**
 * Loads the request map in the browser only, with a placeholder while it arrives.
 *
 * Leaflet reads `window` as soon as it is imported, which fails during server rendering.
 * Loading the map with `ssr: false` keeps it out of the server bundle and also keeps the
 * map library off pages that do not show a map. Below the map, a key explains the markers
 * without relying on colour alone.
 */

import dynamic from "next/dynamic";

import type { RequestMapProps } from "@/components/map/RequestMap";
import { Skeleton } from "@/components/ui/skeleton";

const RequestMap = dynamic(() => import("@/components/map/RequestMap"), {
  ssr: false,
  loading: () => (
    <Skeleton className="h-72 w-full rounded-2xl sm:h-80" role="status" aria-label="Loading map" />
  ),
});

export function MapPanel(props: RequestMapProps) {
  return (
    <figure className="space-y-2">
      {/* Leaflet's panes use high z-indexes; isolating them keeps the site header on top. */}
      <div className="isolate overflow-hidden rounded-2xl border border-border">
        <RequestMap {...props} />
      </div>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-ink-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="size-3 rounded-full border-2 border-white bg-primary-600 shadow-soft" aria-hidden="true" />
          Your hospital
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-3 rounded-full border-2 border-white bg-trust-600 shadow-soft" aria-hidden="true" />
          Matching donors, shown to the nearest kilometre (larger marks are several donors)
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="size-3 rounded-full border border-dashed border-primary-700" aria-hidden="true" />
          Search radius
        </span>
      </figcaption>
    </figure>
  );
}
