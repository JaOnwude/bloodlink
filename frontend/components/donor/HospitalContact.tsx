/**
 * Where a hospital is and how to reach it, for a donor on their way to give blood.
 *
 * The phone number is a `tel:` link, so one tap calls it on a phone, and the map link opens
 * OpenStreetMap at the hospital for directions.
 */

import { ExternalLink, MapPin, Phone } from "lucide-react";

import { mapLinkFor } from "@/lib/format";
import type { HospitalSummary } from "@/types/api";

export function HospitalContact({ hospital }: { hospital: HospitalSummary }) {
  return (
    <div className="space-y-2 text-sm">
      <p className="flex items-start gap-2 text-ink">
        <MapPin className="mt-0.5 size-4 shrink-0 text-ink-muted" aria-hidden="true" />
        <span>
          {hospital.address}, {hospital.city}, {hospital.state}
        </span>
      </p>
      <p className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <a
          href={`tel:${hospital.contact_phone}`}
          className="inline-flex items-center gap-1.5 font-medium text-primary underline-offset-4 hover:underline"
        >
          <Phone className="size-4" aria-hidden="true" />
          {hospital.contact_phone}
        </a>
        <a
          href={mapLinkFor(hospital.latitude, hospital.longitude)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 font-medium text-primary underline-offset-4 hover:underline"
        >
          Directions <ExternalLink className="size-4" aria-hidden="true" />
          <span className="sr-only">(opens in a new tab)</span>
        </a>
      </p>
    </div>
  );
}
