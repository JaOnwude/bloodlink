/**
 * Sends a signed-in visitor away from the sign-in and register pages.
 *
 * The destination is the page they were trying to reach (the safe `next` address in the URL),
 * provided the account that signed in may open it, or otherwise the landing page for their role. The hook waits until the query string is
 * available, so the requested destination is never lost.
 *
 * @returns The requested destination, or an empty string when there is none. Pages use it to
 *   carry the destination across to the other form (sign in to register and back).
 */

import { useRouter } from "next/router";
import { useEffect } from "react";

import { useAuth } from "@/context/AuthContext";
import { homePathFor, pathAllowedFor } from "@/lib/routes";
import { safeRedirectPath } from "@/lib/redirect";

export function useRedirectIfSignedIn(): string {
  const router = useRouter();
  const { user, status } = useAuth();
  const requested = safeRedirectPath(router.query.next, "");

  useEffect(() => {
    if (router.isReady && status === "authenticated" && user) {
      // Follow the remembered page only if this account may open it.
      const target =
        requested && pathAllowedFor(user.role, requested) ? requested : homePathFor(user.role);
      void router.replace(target);
    }
  }, [router, status, user, requested]);

  return requested;
}
