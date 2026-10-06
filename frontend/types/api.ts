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

/** Biological sex, used to choose the waiting period between donations. */
export type Sex = "male" | "female";

/** The donor's own profile as returned by the API. Dates are ISO strings (YYYY-MM-DD). */
export interface DonorProfile {
  id: string;
  blood_group: BloodGroup;
  date_of_birth: string;
  weight_kg: number;
  sex: Sex;
  latitude: number;
  longitude: number;
  city: string;
  last_donation_date: string | null;
  is_available: boolean;
  consent_to_contact: boolean;
}

/** Whether the donor can give one kind of donation, and from when if not. */
export interface ComponentEligibility {
  component_code: string;
  component_name: string;
  eligible: boolean;
  next_eligible_date: string | null;
}

/** The donor's eligibility today, as returned by the API. */
export interface Eligibility {
  eligible_for_any: boolean;
  blockers: string[];
  components: ComponentEligibility[];
}

/** Where a hospital is in the administrator's review. */
export type VerificationStatus = "pending" | "verified" | "rejected";

/** A hospital as shown to its own staff. Timestamps are ISO date-times. */
export interface Hospital {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  latitude: number;
  longitude: number;
  registration_number: string | null;
  contact_phone: string;
  verification_status: VerificationStatus;
  verified_at: string | null;
  rejection_reason: string | null;
  created_at: string;
}
