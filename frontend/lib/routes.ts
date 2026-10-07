/**
 * Where each kind of account lands after signing in.
 *
 * An entry points at the home page until that role's dashboard exists.
 */

import type { UserRole } from "@/types/api";

const landingPaths: Record<UserRole, string> = {
  donor: "/donor",
  hospital_staff: "/hospital",
  admin: "/admin",
};

/** The page a signed-in user of this role starts from. */
export function homePathFor(role: UserRole): string {
  return landingPaths[role];
}

/** Page areas that only one kind of account may open, and which kind. */
const restrictedAreas: { prefix: string; role: UserRole }[] = [
  { prefix: "/admin", role: "admin" },
  { prefix: "/hospital", role: "hospital_staff" },
  { prefix: "/donor", role: "donor" },
];

/**
 * Whether an account with this role may open the given path.
 *
 * Used before sending someone to a remembered page, so a return address left over from a
 * different account (for example after signing out of an administrator account and into a
 * donor one) is never followed. Paths outside the restricted areas are open to everyone.
 * This is a convenience for navigation; the API enforces the real access rules.
 */
export function pathAllowedFor(role: UserRole, path: string): boolean {
  const pathname = path.split(/[?#]/)[0];
  for (const area of restrictedAreas) {
    if (pathname === area.prefix || pathname.startsWith(`${area.prefix}/`)) {
      return area.role === role;
    }
  }
  return true;
}
