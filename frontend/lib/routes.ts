/**
 * Where each kind of account lands after signing in.
 *
 * An entry points at the home page until that role's dashboard exists.
 */

import type { UserRole } from "@/types/api";

const landingPaths: Record<UserRole, string> = {
  donor: "/donor",
  hospital_staff: "/hospital",
  admin: "/",
};

/** The page a signed-in user of this role starts from. */
export function homePathFor(role: UserRole): string {
  return landingPaths[role];
}
