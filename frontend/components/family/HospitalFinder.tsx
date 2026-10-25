/**
 * Helps a family find the verified hospital their patient is in.
 *
 * Two ways to search, usable together: the hospital's NIPOST postcode (often on its sign or
 * letterhead, or the family's own postcode to find hospitals close to home), or the
 * device's location. With a postcode, the hospital with exactly that code comes first,
 * then hospitals in the same postcode area, district, LGA and state. Only hospitals an
 * administrator has verified are listed.
 *
 * The device position is sent once, for the search, and is not stored.
 */

import { LocateFixed, MapPin, Phone, Search } from "lucide-react";
import { useState } from "react";
import type { FormEvent } from "react";

import { FormField } from "@/components/auth/FormField";
import { Button } from "@/components/ui/button";
import { ApiError, api } from "@/lib/api";
import type { PostcodeRing, PublicHospital } from "@/types/api";

const RING_LABELS: Record<PostcodeRing, string> = {
  area: "Same postcode area",
  district: "Same district",
  lga: "Same LGA",
  state: "Same state",
};

interface Position {
  latitude: number;
  longitude: number;
}

export function HospitalFinder({ onChoose }: { onChoose: (hospital: PublicHospital) => void }) {
  const [postcode, setPostcode] = useState("");
  const [position, setPosition] = useState<Position | null>(null);
  const [results, setResults] = useState<PublicHospital[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function search(at: Position | null) {
    setSearching(true);
    setError(null);
    try {
      const found = await api.get<PublicHospital[]>("/public/hospitals", {
        query: {
          postcode: postcode.trim() || null,
          latitude: at?.latitude,
          longitude: at?.longitude,
        },
      });
      setResults(found);
    } catch (failure) {
      setResults(null);
      setError(
        failure instanceof ApiError && failure.status === 422
          ? "Enter a full postcode of 11 letters and digits, like FC-01-A01-KP-27."
          : "We could not search right now. Check your connection and try again.",
      );
    } finally {
      setSearching(false);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void search(position);
  }

  function handleUseLocation() {
    if (!("geolocation" in navigator)) {
      setError("Your browser cannot share its location. Enter a postcode instead.");
      return;
    }
    setSearching(true);
    navigator.geolocation.getCurrentPosition(
      (found) => {
        const here = { latitude: found.coords.latitude, longitude: found.coords.longitude };
        setPosition(here);
        void search(here);
      },
      () => {
        setSearching(false);
        setError("We could not get your location. Allow location access, or enter a postcode.");
      },
      { timeout: 10000, maximumAge: 600000 },
    );
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} noValidate className="space-y-3">
        <FormField
          id="search_postcode"
          name="postcode"
          label="Hospital's NIPOST postcode"
          optional
          autoComplete="off"
          spellCheck={false}
          placeholder="FC-01-A01-KP-27"
          hint="Or your own postcode, to see hospitals near you first."
          value={postcode}
          onChange={(event) => setPostcode(event.target.value.toUpperCase())}
        />
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={searching}>
            <Search />
            {searching ? "Searching..." : "Find hospitals"}
          </Button>
          <Button type="button" variant="outline" onClick={handleUseLocation} disabled={searching}>
            <LocateFixed />
            Use my location
          </Button>
        </div>
        {error ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
      </form>

      {results === null ? null : results.length === 0 ? (
        <p className="text-ink-muted">No verified hospital matched. Try another postcode.</p>
      ) : (
        <ol className="space-y-3" aria-label="Verified hospitals">
          {results.map((hospital) => (
            <li
              key={hospital.id}
              className="space-y-3 rounded-2xl border border-border bg-surface p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <p className="font-heading text-lg font-semibold text-ink">{hospital.name}</p>
                  <p className="flex items-start gap-1.5 text-sm text-ink-muted">
                    <MapPin className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
                    <span>
                      {hospital.address}, {hospital.city}
                      {hospital.postcode ? (
                        <span className="font-medium text-ink"> · {hospital.postcode}</span>
                      ) : null}
                    </span>
                  </p>
                  <p className="flex items-center gap-1.5 text-sm text-ink-muted">
                    <Phone className="size-4 shrink-0" aria-hidden="true" />
                    <a href={`tel:${hospital.contact_phone}`} className="hover:underline">
                      {hospital.contact_phone}
                    </a>
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {hospital.postcode_ring ? (
                    <span className="rounded-full bg-trust-50 px-2 py-0.5 font-medium text-trust-700">
                      {RING_LABELS[hospital.postcode_ring]}
                    </span>
                  ) : null}
                  {hospital.distance_km !== null ? (
                    <span className="text-ink-muted tabular-nums">
                      {hospital.distance_km < 1
                        ? "Under 1 km"
                        : `${hospital.distance_km.toFixed(1)} km`}
                    </span>
                  ) : null}
                </div>
              </div>
              <Button type="button" size="sm" onClick={() => onChoose(hospital)}>
                Ask this hospital for blood
              </Button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
