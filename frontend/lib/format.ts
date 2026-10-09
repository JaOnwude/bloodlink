/**
 * Formatting helpers for dates shown to people.
 */

/**
 * Formats an ISO date (YYYY-MM-DD) as, for example, "12 January 2027".
 *
 * The date is read as a calendar date in the local time zone. Parsing "2027-01-12" directly
 * would treat it as midnight UTC, which can display as the previous day west of Greenwich.
 */
export function formatDate(iso: string): string {
  const date = new Date(`${iso}T00:00:00`);
  return new Intl.DateTimeFormat("en-NG", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

/** Today's date in the local time zone as YYYY-MM-DD, for the `max` of date inputs. */
export function todayIso(): string {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

/** Formats an ISO date-time (for example from the API) as a local date, such as "12 January 2027". */
export function formatTimestamp(iso: string): string {
  return new Intl.DateTimeFormat("en-NG", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(new Date(iso));
}

/** Formats an ISO date-time as a local date and time, such as "12 January 2027, 18:00". */
export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat("en-NG", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/**
 * Describes how far a moment is from now in words, such as "in 3 hours" or "2 days ago".
 *
 * The largest whole unit is used, which is precise enough for deadlines measured in hours
 * and days. `now` can be passed in so a list of times is judged against the same instant.
 */
export function formatRelative(iso: string, now: Date = new Date()): string {
  const seconds = Math.round((new Date(iso).getTime() - now.getTime()) / 1000);
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ["day", 86_400],
    ["hour", 3_600],
    ["minute", 60],
  ];
  const formatter = new Intl.RelativeTimeFormat("en-NG", { numeric: "auto" });
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return formatter.format(Math.trunc(seconds / size), unit);
  }
  return formatter.format(0, "minute");
}

/**
 * Turns a moment into the "YYYY-MM-DDTHH:mm" form a `datetime-local` input expects, in the
 * local time zone. `toISOString` cannot be used: it gives UTC, which the input would then
 * show as if it were local time.
 */
export function toLocalInputValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** A link that opens OpenStreetMap at a point, for directions to a hospital. */
export function mapLinkFor(latitude: number, longitude: number): string {
  return `https://www.openstreetmap.org/?mlat=${latitude}&mlon=${longitude}#map=16/${latitude}/${longitude}`;
}
