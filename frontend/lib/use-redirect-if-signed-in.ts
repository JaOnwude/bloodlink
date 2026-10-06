/**
 * Sends a signed-in visitor away from the sign-in and register pages.
 *
 * The destination is the page they were trying to reach (the safe `next` address in the URL)
 * or, failing that, the landing page for their role. The hook waits until the query string is
 * available, so the requested destination is never lost.
 *
 * @returns The requested destination, or an empty string when there is none. Pages use it to
 *   carry the destination across to the other form (sign in to register and back).
 */

import { useRouter } from "next/router";
import { useEffect } from "react";

import { useAuth } from "@/context/AuthContext";
import { homePathFor } from "@/lib/routes";
import { safeRedirectPath } from "@/lib/redirect";

export function useRedirectIfSignedIn(): string {
  const router = useRouter();
  const { user, status } = useAuth();
  const requested = safeRedirectPath(router.query.next, "");

  useEffect(() => {
    if (router.isReady && status === "authenticated" && user) {
      void router.replace(requested || homePathFor(user.role));
    }
  }, [router, status, user, requested]);

  return requested;
}
