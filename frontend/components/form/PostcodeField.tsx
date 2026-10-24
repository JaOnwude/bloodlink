/**
 * Lets someone give their NIPOST postcode, and checks it with NIPOST as they go.
 *
 * Nobody knows an 11-character code by heart, so there are two ways in: type it, or press
 * "Find from my location" and NIPOST reverse search returns the postcode of the building
 * the device is in. Either way the code is checked with NIPOST, and the result (the LGA and
 * state it belongs to, or "not found") is shown under the field before the form is sent.
 *
 * The device position is sent once, for that search, and is not stored.
 *
 * The parent owns the typed value. The server checks the postcode again when the form is
 * saved, so this check is a convenience, not the gate.
 */

import { CircleCheck, CircleX, LocateFixed } from "lucide-react";
import { useEffect, useState } from "react";

import { FormField } from "@/components/auth/FormField";
import { Button } from "@/components/ui/button";
import { ApiError, api, isAbortError } from "@/lib/api";
import type { PostcodeAt, PostcodeCheck, PostcodeSource } from "@/types/api";

/** How far from the device NIPOST may look for a building, in metres (its limit is 250). */
const SEARCH_DISTANCE_M = 100;

/** Shape of a full postcode once spaces and dashes are removed. */
const COMPACT_POSTCODE = /^[A-Z]{2}\d{2}[A-Z0-9]{3}[A-Z]{2}\d{2}$/;

function isPostcodeShaped(value: string): boolean {
  return COMPACT_POSTCODE.test(value.replace(/[\s\-./]/g, "").toUpperCase());
}

type Status =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "valid"; check: PostcodeCheck }
  | { kind: "invalid"; postcode: string; source: PostcodeSource }
  | { kind: "error"; message: string };

interface PostcodeFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** Problem reported by the server when the form was saved. */
  error?: string;
  /** Help shown under the field. */
  hint?: string;
  label?: string;
}

export function PostcodeField({
  value,
  onChange,
  error,
  hint,
  label = "NIPOST postcode",
}: PostcodeFieldProps) {
  // The answer for the last postcode checked. Kept with the postcode it belongs to, so an
  // answer for an earlier value is never shown against the current one.
  const [answer, setAnswer] = useState<{
    postcode: string;
    status: Status;
  } | null>(null);
  const [locating, setLocating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const shaped = isPostcodeShaped(value);
  const status: Status = !shaped
    ? { kind: "idle" }
    : answer?.postcode === value
      ? answer.status
      : { kind: "checking" };

  // Check the code with NIPOST once it has the full shape, and again whenever it changes.
  useEffect(() => {
    if (!shaped) return;
    const controller = new AbortController();
    api
      .get<PostcodeCheck>("/postcodes/check", {
        query: { code: value },
        signal: controller.signal,
      })
      .then((check) =>
        setAnswer({
          postcode: value,
          status: check.valid
            ? { kind: "valid", check }
            : {
                kind: "invalid",
                postcode: check.postcode,
                source: check.source,
              },
        }),
      )
      .catch((failure: unknown) => {
        if (isAbortError(failure)) return;
        setAnswer({
          postcode: value,
          status: {
            kind: "error",
            message:
              failure instanceof ApiError ? failure.message : "The postcode could not be checked.",
          },
        });
      });
    return () => controller.abort();
  }, [shaped, value]);

  function handleFindFromLocation() {
    if (!("geolocation" in navigator)) {
      setMessage("Your browser cannot share its location. Type the postcode instead.");
      return;
    }
    setLocating(true);
    setMessage(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        api
          .get<PostcodeAt>("/postcodes/at", {
            query: {
              latitude: position.coords.latitude,
              longitude: position.coords.longitude,
              max_distance_m: SEARCH_DISTANCE_M,
            },
          })
          .then((found) => {
            if (found.found && found.postcode) {
              onChange(found.postcode);
            } else {
              setMessage(
                `NIPOST has no building within ${SEARCH_DISTANCE_M} m of this location. ` +
                  "Type the postcode instead.",
              );
            }
          })
          .catch((failure: unknown) => {
            setMessage(
              failure instanceof ApiError ? failure.message : "The postcode could not be found.",
            );
          })
          .finally(() => setLocating(false));
      },
      () => {
        setMessage("We could not get the location. Allow location access, or type the postcode.");
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    );
  }

  return (
    <div className="space-y-3">
      <FormField
        id="postcode"
        name="postcode"
        label={label}
        optional
        autoComplete="off"
        spellCheck={false}
        placeholder="FC-01-A01-KP-27"
        hint={hint}
        value={value}
        onChange={(event) => onChange(event.target.value.toUpperCase())}
        error={error}
      />

      <PostcodeStatus status={status} />

      <div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleFindFromLocation}
          disabled={locating}
        >
          <LocateFixed />
          {locating ? "Asking NIPOST..." : "Find from my location"}
        </Button>
      </div>

      {message ? (
        <p role="alert" className="text-sm text-danger">
          {message}
        </p>
      ) : null}
    </div>
  );
}

function PostcodeStatus({ status }: { status: Status }) {
  if (status.kind === "idle") return null;
  if (status.kind === "checking") {
    return (
      <p className="text-sm text-ink-muted" aria-live="polite">
        Checking with NIPOST...
      </p>
    );
  }
  if (status.kind === "error") {
    return (
      <p className="text-sm text-danger" aria-live="polite">
        {status.message}
      </p>
    );
  }
  if (status.kind === "invalid") {
    return (
      <p
        className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-danger"
        aria-live="polite"
      >
        <CircleX className="size-4 shrink-0" aria-hidden="true" />
        <span>NIPOST has no building with the postcode {status.postcode}.</span>
        <SourceBadge source={status.source} />
      </p>
    );
  }

  const { check } = status;
  const place = [
    check.lga_name ? `${check.lga_name} LGA` : null,
    check.state_name ?? check.state_code,
  ]
    .filter(Boolean)
    .join(", ");
  return (
    <p
      className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-success"
      aria-live="polite"
    >
      <CircleCheck className="size-4 shrink-0" aria-hidden="true" />
      <span>Assigned by NIPOST{place ? ` · ${place}` : ""}</span>
      <SourceBadge source={check.source} />
    </p>
  );
}

/** Says plainly when an answer came from sample data rather than NIPOST's live dataset. */
function SourceBadge({ source }: { source: PostcodeSource }) {
  if (source === "live") return null;
  return (
    <span className="rounded-full bg-surface px-2 py-0.5 text-xs text-ink-muted ring-1 ring-border">
      {source === "mock" ? "Sample data" : "NIPOST sandbox"}
    </span>
  );
}
