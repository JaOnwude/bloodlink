/**
 * Lets someone say where they (or their hospital) are.
 *
 * The main choice is a city from a list: easy, and private. For a closer match there is an
 * optional button that uses the device's location. That position is rounded to about one
 * kilometre before it leaves the browser, so an exact address is never stored.
 *
 * The parent owns the values. When the city changes, any device location is cleared so the
 * two cannot disagree.
 */

import { MapPin } from "lucide-react";
import { useState } from "react";

import { SelectField } from "@/components/form/SelectField";
import { Button } from "@/components/ui/button";
import { NIGERIAN_CITIES, findCity, roundCoordinate } from "@/lib/locations";
import type { Coordinates } from "@/lib/locations";

interface LocationPickerProps {
  /** The chosen city name, or an empty string for none. */
  city: string;
  /** A city saved earlier that is not in the list, kept as an extra choice. */
  unlistedCity?: string | null;
  /** Device location, when it is being used instead of the city centre. */
  precise: Coordinates | null;
  onCityChange: (city: string) => void;
  onPreciseChange: (coordinates: Coordinates | null) => void;
  error?: string;
  /** Wording for the device-location button. */
  deviceButtonLabel?: string;
}

export function LocationPicker({
  city,
  unlistedCity,
  precise,
  onCityChange,
  onPreciseChange,
  error,
  deviceButtonLabel = "Use my current location",
}: LocationPickerProps) {
  const [locating, setLocating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const selected = findCity(city);

  function handleUseDeviceLocation() {
    if (!("geolocation" in navigator)) {
      setMessage("Your browser cannot share its location. Pick a city instead.");
      return;
    }
    setLocating(true);
    setMessage(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onPreciseChange({
          latitude: roundCoordinate(position.coords.latitude),
          longitude: roundCoordinate(position.coords.longitude),
        });
        setLocating(false);
      },
      () => {
        setMessage("We could not get the location. Allow location access, or pick a city instead.");
        setLocating(false);
      },
      { timeout: 10000, maximumAge: 600000 },
    );
  }

  const summary = precise
    ? "Using the device location, rounded to about 1 km."
    : selected
      ? `Using the centre of ${selected.city}.`
      : "Choose a city above.";

  return (
    <div className="space-y-4">
      <SelectField
        id="city"
        name="city"
        label="City"
        hint="If the town is not listed, choose the nearest city."
        value={city}
        onChange={(event) => {
          onCityChange(event.target.value);
          onPreciseChange(null);
        }}
        error={error}
      >
        <option value="">Select a city</option>
        {unlistedCity ? <option value={unlistedCity}>{unlistedCity}</option> : null}
        {NIGERIAN_CITIES.map((entry) => (
          <option key={entry.city} value={entry.city}>
            {entry.city}, {entry.state}
          </option>
        ))}
      </SelectField>

      <div className="space-y-3 rounded-2xl border border-border bg-surface p-4">
        <p className="text-sm text-ink-muted" aria-live="polite">
          {summary}
        </p>
        <div className="flex flex-wrap items-center gap-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleUseDeviceLocation}
            disabled={locating}
          >
            <MapPin />
            {locating ? "Finding the location..." : deviceButtonLabel}
          </Button>
          {precise ? (
            <Button type="button" variant="ghost" size="sm" onClick={() => onPreciseChange(null)}>
              Use city centre instead
            </Button>
          ) : null}
        </div>
        {message ? (
          <p role="alert" className="text-sm text-danger">
            {message}
          </p>
        ) : null}
      </div>
    </div>
  );
}
