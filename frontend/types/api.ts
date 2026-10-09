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

/** A staff member linked to a hospital, shown to administrators reviewing it. */
export interface StaffSummary {
  id: string;
  full_name: string;
  email: string;
  phone: string | null;
}

/** A hospital as shown to administrators: its details plus the people who registered it. */
export interface AdminHospital extends Hospital {
  staff: StaffSummary[];
}

/** One page of the administrator's review queue. */
export interface HospitalPage {
  items: AdminHospital[];
  total: number;
  limit: number;
  offset: number;
}

/** A blood component that a request can ask for, such as whole blood or platelets. */
export interface BloodComponent {
  code: string;
  name: string;
}

/** How quickly a hospital needs the blood. */
export type RequestUrgency = "critical" | "urgent" | "routine";

/** Where a blood request is in its life. */
export type RequestStatus = "open" | "fulfilled" | "closed" | "expired";

/**
 * A blood request as shown to the staff of the hospital that raised it.
 *
 * `units_pledged` counts donors who have committed or already given; `units_remaining` is
 * what is still needed. Timestamps are ISO date-times in UTC.
 */
export interface BloodRequest {
  id: string;
  hospital_id: string;
  recipient_group: BloodGroup;
  component_code: string;
  component_name: string;
  units_needed: number;
  units_pledged: number;
  units_remaining: number;
  urgency: RequestUrgency;
  deadline: string;
  notes: string | null;
  status: RequestStatus;
  fulfilled_at: string | null;
  created_at: string;
}

/** One page of a hospital's requests. */
export interface RequestPage {
  items: BloodRequest[];
  total: number;
  limit: number;
  offset: number;
}

/**
 * A donor who can answer a request. Deliberately anonymous: the hospital sees contact
 * details only after the donor pledges.
 */
export interface DonorMatch {
  donor_id: string;
  blood_group: BloodGroup;
  city: string;
  distance_km: number;
  /** Position rounded to about a kilometre, for the map. Never the exact location. */
  approx_latitude: number;
  approx_longitude: number;
}

/** The donors matching a request, nearest first, and the radius that was searched. */
export interface MatchesResponse {
  items: DonorMatch[];
  total: number;
  radius_km: number;
}

/** Where a donor's commitment to a request stands. */
export type PledgeStatus = "pledged" | "donated" | "no_show" | "cancelled";

/** A pledge after a change, with the effect on its request. */
export interface PledgeResult {
  id: string;
  request_id: string;
  status: PledgeStatus;
  pledged_at: string;
  resolved_at: string | null;
  request_status: RequestStatus;
  units_remaining: number;
}

/**
 * The donor behind a pledge, as the hospital sees them. The contact fields are null for a
 * cancelled pledge.
 */
export interface PledgedDonor {
  donor_id: string;
  blood_group: BloodGroup;
  city: string;
  full_name: string | null;
  phone: string | null;
  email: string | null;
}

/** A pledge to one of the hospital's requests. */
export interface HospitalPledge {
  id: string;
  status: PledgeStatus;
  pledged_at: string;
  resolved_at: string | null;
  donor: PledgedDonor;
}

/** Where to go and whom to call, as shown to a donor. */
export interface HospitalSummary {
  id: string;
  name: string;
  address: string;
  city: string;
  state: string;
  contact_phone: string;
  latitude: number;
  longitude: number;
}

/** The request a donor's pledge is for. */
export interface DonorRequestSummary {
  id: string;
  recipient_group: BloodGroup;
  component_name: string;
  urgency: RequestUrgency;
  deadline: string;
  notes: string | null;
  status: RequestStatus;
}

/** One of the donor's own pledges. */
export interface DonorPledge {
  id: string;
  status: PledgeStatus;
  pledged_at: string;
  resolved_at: string | null;
  request: DonorRequestSummary;
  hospital: HospitalSummary;
}

/** One page of the donor's pledges, most recent first. */
export interface DonorPledgePage {
  items: DonorPledge[];
  total: number;
  limit: number;
  offset: number;
}

/** An open request the donor can answer, with the donor's own pledge if they made one. */
export interface OpenRequestForDonor {
  id: string;
  recipient_group: BloodGroup;
  component_code: string;
  component_name: string;
  urgency: RequestUrgency;
  deadline: string;
  notes: string | null;
  units_remaining: number;
  distance_km: number;
  hospital: HospitalSummary;
  my_pledge_id: string | null;
}

/** The open requests a donor can answer, and the radius searched. */
export interface OpenRequestsForDonor {
  items: OpenRequestForDonor[];
  radius_km: number;
}

/** How many donors have been texted about a request, and through which sender. */
export interface AlertSummary {
  sent: number;
  failed: number;
  queued: number;
  total: number;
  /** "termii" for real messages; "console" when messages are only recorded. */
  provider: "termii" | "console";
}

/** What one request to alert donors did, followed by the request's totals. */
export interface AlertRun {
  matched: number;
  newly_alerted: number;
  sent: number;
  failed: number;
  already_alerted: number;
  without_phone: number;
  totals: AlertSummary;
}

/**
 * A hospital's figures for requests raised in a period. Rates are fractions from 0 to 1,
 * and null when there is nothing to measure yet.
 */
export interface HospitalStats {
  period_days: number;
  since: string;
  requests_raised: number;
  requests_open: number;
  requests_finished: number;
  requests_fulfilled: number;
  fulfilment_rate: number | null;
  median_minutes_to_fulfil: number | null;
  pledges_resolved: number;
  no_shows: number;
  no_show_rate: number | null;
  units_donated: number;
  donors_alerted: number;
}
