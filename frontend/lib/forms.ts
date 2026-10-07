/**
 * Helpers for forms that talk to the API.
 */

import { ApiError } from "@/lib/api";

/**
 * Shortest password the form accepts before contacting the server. It mirrors the server's
 * rule (15 characters, following NIST SP 800-63B-4) only to give instant feedback; the
 * server remains the authority and may reject a password for other reasons.
 */
export const PASSWORD_MIN_LENGTH = 15;

/** Messages keyed by form field name. */
export type FieldErrors = Record<string, string>;

export interface FormFailure {
  /** Problems that belong to a specific field. */
  fields: FieldErrors;
  /** A problem with the form as a whole, or null when every problem has a field. */
  general: string | null;
}

/**
 * Turns an API error into messages the form can place next to the right inputs.
 *
 * Validation errors (422) carry a location such as `["body", "password"]`; the last part is
 * the field. A conflict (409) is attached to the email field, because a duplicate email is
 * the only conflict the sign-up form can cause. Everything else becomes a general message.
 */
export function failureFromError(error: unknown): FormFailure {
  if (!(error instanceof ApiError)) {
    return { fields: {}, general: "Something went wrong. Please try again." };
  }

  if (error.status === 409) {
    return { fields: { email: error.message }, general: null };
  }

  if (error.status === 422) {
    const detail = (error.detail as { detail?: unknown } | undefined)?.detail;
    if (Array.isArray(detail)) {
      const fields: FieldErrors = {};
      let general: string | null = null;
      for (const item of detail) {
        const loc = Array.isArray(item?.loc) ? (item.loc as unknown[]) : [];
        const message = typeof item?.msg === "string" ? item.msg : "This value is not valid.";
        const field = loc.length > 1 ? String(loc[loc.length - 1]) : null;
        if (field) {
          fields[field] ??= message;
        } else {
          general ??= message;
        }
      }
      return { fields, general };
    }
  }

  return { fields: {}, general: error.message };
}

/**
 * Moves keyboard focus to the first input that has an error.
 *
 * After a failed submit, this puts the cursor where the person needs to act and, for screen
 * reader users, announces the field together with its error message.
 *
 * @param errors Messages keyed by field name.
 * @param order Field names in the order they appear on the page.
 */
export function focusFirstInvalid(errors: FieldErrors, order: string[]): void {
  const first = order.find((name) => errors[name]);
  if (first) document.getElementById(first)?.focus();
}
