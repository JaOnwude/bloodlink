/**
 * Types that mirror the shapes exchanged with the BloodLink API.
 *
 * Keeping them in one module gives every page and component a single, searchable source
 * of truth. String unions are used instead of TypeScript enums so values serialise to and
 * from JSON without any conversion step.
 */

/** Authorisation role attached to an account. */
export type UserRole = "donor" | "hospital_staff" | "admin";

/** ABO and Rh blood group, in the conventional written form. */
export type BloodGroup = "A+" | "A-" | "B+" | "B-" | "AB+" | "AB-" | "O+" | "O-";

/** Every blood group, in a stable display order suitable for select inputs. */
export const BLOOD_GROUPS: readonly BloodGroup[] = [
  "O-",
  "O+",
  "A-",
  "A+",
  "B-",
  "B+",
  "AB-",
  "AB+",
] as const;

/** The signed-in account as returned by the session endpoint. */
export interface SessionUser {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  /** Set for hospital staff; null for donors and administrators. */
  hospital_id: string | null;
}

/** Response of the API liveness probe. */
export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

/** Response of the API readiness probe. */
export interface ReadinessResponse {
  status: "ready";
  database: "up";
}
