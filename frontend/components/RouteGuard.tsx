/**
 * Restricts a page to signed-in users holding one of the permitted roles.
 *
 * This improves the experience (people are redirected instead of seeing an error) but is
 * NOT a security boundary: the API independently enforces role and ownership checks on
 * every protected endpoint, and that is what actually protects the data.
 *
 * A visitor who was never signed in is sent to the sign-in page together with the address
 * they wanted, so they can be returned there. Someone who WAS signed in and then signed out
 * is sent to the sign-in page without it: they chose to leave, and the next person to sign
 * in may be a different kind of user.
 */

import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

import { buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { homePathFor } from "@/lib/routes";
import type { UserRole } from "@/types/api";

interface RouteGuardProps {
  /** Roles allowed to view the wrapped content. */
  allow: UserRole[];
  children: ReactNode;
}

export function RouteGuard({ allow, children }: RouteGuardProps) {
  const { user, status } = useAuth();
  const router = useRouter();
  const wasSignedIn = useRef(false);

  useEffect(() => {
    if (status === "authenticated") {
      wasSignedIn.current = true;
      return;
    }
    if (status === "unauthenticated") {
      const target = wasSignedIn.current
        ? "/login"
        : `/login?next=${encodeURIComponent(router.asPath)}`;
      void router.replace(target);
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
    const home = user ? homePathFor(user.role) : "/";
    return (
      <div className="mx-auto max-w-md space-y-4 py-16 text-center">
        <h1 className="text-xl font-semibold text-foreground">Access not permitted</h1>
        <p className="text-sm text-muted-foreground">
          Your account does not have permission to view this page.
        </p>
        <Link href={home} className={buttonVariants({ variant: "outline" })}>
          {home === "/" ? "Go to the home page" : "Go to your dashboard"}
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
