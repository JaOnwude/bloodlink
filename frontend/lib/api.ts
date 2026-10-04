/**
 * Typed HTTP client for the BloodLink API.
 *
 * Every network call in the application goes through this module so that cross-cutting
 * behaviour lives in exactly one place:
 *
 *  - credentials are always included, because the session is carried by an httpOnly cookie
 *    that scripts cannot read;
 *  - JSON is serialised and parsed consistently;
 *  - failures of every kind (network down, validation error, expired session) surface as a
 *    single `ApiError` type with a human-readable message that can be shown directly.
 */

import { API_BASE_URL } from "@/lib/config";

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
type QueryValue = string | number | boolean | null | undefined;

/** Optional per-call settings. */
export interface RequestOptions {
  /** Query-string parameters. Null and undefined values are omitted. */
  query?: Record<string, QueryValue>;
  /** Allows the caller to cancel the request, for example when a component unmounts. */
  signal?: AbortSignal;
  /** Additional request headers. */
  headers?: Record<string, string>;
}

/**
 * Error raised for any failed API call.
 *
 * `status` is the HTTP status code, or 0 when the server could not be reached at all.
 * `detail` carries the raw error payload for callers that need field-level information.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** Returns true when an error was produced by cancelling a request on purpose. */
export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = `${API_BASE_URL}${path}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null) params.append(key, String(value));
  }
  const queryString = params.toString();
  return queryString ? `${url}?${queryString}` : url;
}

/**
 * Extracts a readable message from an error payload.
 *
 * FastAPI reports business errors as `{ "detail": "text" }` and validation errors as
 * `{ "detail": [{ "msg": "text", ... }] }`; both are handled.
 */
function messageFromPayload(payload: unknown, fallback: string): string {
  if (payload && typeof payload === "object" && "detail" in payload) {
    const detail = (payload as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) =>
          item && typeof item === "object" && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : null,
        )
        .filter((message): message is string => message !== null);
      if (messages.length > 0) return messages.join("; ");
    }
  }
  return fallback;
}

async function request<T>(
  method: HttpMethod,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), {
      method,
      // Required so the browser sends and accepts the session cookie across origins.
      credentials: "include",
      headers: {
        Accept: "application/json",
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options.signal,
    });
  } catch (error) {
    // A deliberate cancellation is not a failure and must reach the caller unchanged.
    if (isAbortError(error)) throw error;
    throw new ApiError(0, "Unable to reach the server. Check your connection and try again.", error);
  }

  // "No Content" responses carry no body to parse.
  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(
      response.status,
      messageFromPayload(payload, response.statusText || "Request failed"),
      payload,
    );
  }
  return payload as T;
}

/** Convenience methods for each HTTP verb the API uses. */
export const api = {
  get: <T>(path: string, options?: RequestOptions) => request<T>("GET", path, undefined, options),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("POST", path, body ?? {}, options),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PUT", path, body ?? {}, options),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) =>
    request<T>("PATCH", path, body ?? {}, options),
  delete: <T>(path: string, options?: RequestOptions) =>
    request<T>("DELETE", path, undefined, options),
};
