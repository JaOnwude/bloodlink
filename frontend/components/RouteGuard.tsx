/**
 * Restricts a page to signed-in users holding one of the permitted roles.
 *
 * This improves the experience (people are redirected instead of seeing an error) but is
 * NOT a security boundary: the API independently enforces role and ownership checks on
 * every protected endpoint, and that is what actually protects the data.
 */

import { useRouter } from "next/router";
import { useEffect } from "react";
import type { ReactNode } from "react";

import { useAuth } from "@/context/AuthContext";
import type { UserRole } from "@/types/api";

interface RouteGuardProps {
  /** Roles allowed to view the wrapped content. */
  allow: UserRole[];
  children: ReactNode;
}

export function RouteGuard({ allow, children }: RouteGuardProps) {
  const { user, status } = useAuth();
  const router = useRouter();

  // Visitors who are not signed in are sent to the sign-in page, which receives the
  // address they were trying to reach so it can return them there afterwards.
  useEffect(() => {
    if (status === "unauthenticated") {
      void router.replace(`/login?next=${encodeURIComponent(router.asPath)}`);
    }
  }, [status, router]);

  if (status === "loading" || status === "unauthenticated") {
    return (
      <p role="status" className="py-16 text-center text-sm text-muted-foreground">
        Checking your session…
      </p>
    );
  }

  if (!user || !allow.includes(user.role)) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <h1 className="text-xl font-semibold text-foreground">Access not permitted</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your account does not have permission to view this page.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}
