/**
 * Safe handling of the "where to go after signing in" address.
 *
 * The address arrives in the URL (`/login?next=/donor`), so it is untrusted: someone could
 * craft a link that sends a freshly signed-in user to a malicious site. Only paths on this
 * site are accepted.
 */

/**
 * Returns `next` when it is a path within this site, otherwise `fallback`.
 *
 * Accepted: a single string starting with one `/`. Rejected: addresses with a scheme or
 * host (`https://...`), protocol-relative addresses (`//host`), backslash tricks, and
 * anything that is not a string.
 */
export function safeRedirectPath(next: string | string[] | undefined, fallback = "/"): string {
  if (typeof next !== "string") return fallback;
  if (!next.startsWith("/") || next.startsWith("//")) return fallback;
  if (next.includes("\\")) return fallback;
  return next;
}
