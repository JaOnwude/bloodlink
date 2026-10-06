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
