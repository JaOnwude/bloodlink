/**
 * Application-wide authentication state.
 *
 * The session itself lives in an httpOnly cookie managed by the API, which scripts cannot
 * read. The browser therefore never "knows" it is signed in; it asks the API who the
 * current user is. This provider performs that check once on load, shares the answer with
 * every component through React context, and exposes helpers to refresh or end the session.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { api, isAbortError } from "@/lib/api";
import type { SessionUser } from "@/types/api";

/** Where the session check currently stands. */
export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  /** The signed-in user, or null when nobody is signed in or the check is still running. */
  user: SessionUser | null;
  /** Lets components distinguish "still checking" from "definitely signed out". */
  status: AuthStatus;
  /** Re-queries the API for the current user, for example right after signing in. */
  refresh: () => Promise<void>;
  /** Ends the session on the server and clears local state. */
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Asks the API who is signed in.
 *
 * Returns the user, or null when there is no usable session. Any failure (no session,
 * expired session, API unreachable) means the visitor cannot be treated as signed in, so
 * protected pages will send them to sign in. A deliberate cancellation is the one
 * exception: it is re-thrown so the caller can ignore the result of an abandoned request.
 */
async function fetchSession(signal?: AbortSignal): Promise<SessionUser | null> {
  try {
    return await api.get<SessionUser>("/auth/me", { signal });
  } catch (error) {
    if (isAbortError(error)) throw error;
    return null;
  }
}

/** Provides authentication state to the component tree. Mount once, near the root. */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  // Single place where the outcome of a session check is turned into component state.
  const applySession = useCallback((current: SessionUser | null) => {
    setUser(current);
    setStatus(current ? "authenticated" : "unauthenticated");
  }, []);

  const refresh = useCallback(async () => {
    applySession(await fetchSession());
  }, [applySession]);

  const signOut = useCallback(async () => {
    try {
      await api.post("/auth/logout");
    } catch {
      // The request can fail because the session already expired or the API is briefly
      // unreachable. Either way the user asked to leave, so local state is cleared below.
    }
    // Always clear local state, so the interface never shows a signed-in view that the
    // user has asked to leave.
    applySession(null);
  }, [applySession]);

  // Initial session check. State is updated from the promise callback rather than directly
  // in the effect body, and the request is cancelled if the provider unmounts first (which
  // also happens once in development because React mounts components twice on purpose).
  useEffect(() => {
    const controller = new AbortController();

    fetchSession(controller.signal)
      .then(applySession)
      .catch(() => {
        // Aborted on unmount: nothing to update.
      });

    return () => controller.abort();
  }, [applySession]);

  const value = useMemo(
    () => ({ user, status, refresh, signOut }),
    [user, status, refresh, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Access the authentication state.
 *
 * @throws If called outside an `AuthProvider`, which indicates a wiring mistake.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside an <AuthProvider>.");
  }
  return context;
}
