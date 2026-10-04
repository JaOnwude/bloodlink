/**
 * Page chrome shared by every route: a header with the brand and account controls, a
 * centred content column, and a footer.
 */

import Link from "next/link";
import type { ReactNode } from "react";

import { useAuth } from "@/context/AuthContext";

export function Layout({ children }: { children: ReactNode }) {
  const { user, status, signOut } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <Link href="/" className="flex items-center gap-2 text-lg font-bold text-primary">
            <span aria-hidden="true">●</span>
            BloodLink
          </Link>

          {/* Account controls appear only once a session has been confirmed. */}
          {status === "authenticated" && user ? (
            <div className="flex items-center gap-4 text-sm">
              <span className="text-muted-foreground">{user.full_name}</span>
              <button
                type="button"
                onClick={() => void signOut()}
                className="rounded-md border border-border px-3 py-1.5 font-medium hover:bg-muted"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">{children}</main>

      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        BloodLink connects verified hospitals with eligible donors. Final eligibility to donate
        is always decided by clinical staff at the donation site.
      </footer>
    </div>
  );
}
