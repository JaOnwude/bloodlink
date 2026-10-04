/**
 * Runtime configuration for the web client.
 *
 * Next.js inlines variables prefixed with NEXT_PUBLIC_ into the browser bundle at build
 * time, so nothing placed here may be secret. The API location is the only value needed.
 */

/** Base URL of the BloodLink API, including its version prefix and without a trailing slash. */
export const API_BASE_URL: string = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/+$/, "");
