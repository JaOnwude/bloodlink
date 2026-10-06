/**
 * The site header: logo, main navigation and account actions, with a mobile menu.
 *
 * The header stays at the top while scrolling and blurs what passes beneath it. On small
 * screens the navigation collapses into a menu button that is keyboard-operable, announces
 * its state to assistive technology, closes with Escape, and closes when a page loads.
 */

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useEffect, useState } from "react";

import { Logo } from "@/components/brand/Logo";
import { Container } from "@/components/layout/Container";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { siteConfig } from "@/lib/site";

export function SiteHeader() {
  const { user, status, signOut } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close the mobile menu as soon as navigation begins.
  useEffect(() => {
    const close = () => setMenuOpen(false);
    router.events.on("routeChangeStart", close);
    return () => router.events.off("routeChangeStart", close);
  }, [router.events]);

  // Close the mobile menu with the Escape key.
  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  const accountActions = status === "authenticated" && user ? (
    <>
      <span className="text-sm text-ink-muted">{user.full_name}</span>
      <Button variant="outline" size="sm" onClick={() => void signOut()}>
        Sign out
      </Button>
    </>
  ) : status === "loading" ? null : (
    <>
      <Link href={siteConfig.accountLinks.signIn} className={buttonVariants({ variant: "ghost" })}>
        Sign in
      </Link>
      <Link href={siteConfig.accountLinks.register} className={buttonVariants({})}>
        Get started
      </Link>
    </>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <Container className="flex h-16 items-center justify-between gap-6">
        <Link href="/" aria-label="BloodLink home" className="rounded-md">
          <Logo />
        </Link>

        {siteConfig.nav.length > 0 ? (
          <nav aria-label="Main" className="hidden items-center gap-8 md:flex">
            {siteConfig.nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm font-medium text-ink-muted transition-colors duration-150 hover:text-ink"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        ) : null}

        <div className="hidden items-center gap-3 md:flex">{accountActions}</div>

        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label={menuOpen ? "Close menu" : "Open menu"}
          aria-expanded={menuOpen}
          aria-controls="mobile-menu"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X /> : <Menu />}
        </Button>
      </Container>

      <div id="mobile-menu" hidden={!menuOpen} className="border-t border-border bg-background md:hidden">
        <Container className="flex flex-col gap-4 py-6">
          {siteConfig.nav.length > 0 ? (
            <nav aria-label="Mobile" className="flex flex-col gap-1">
              {siteConfig.nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-md px-2 py-3 text-base font-medium text-ink hover:bg-muted"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          ) : null}
          <div className="flex flex-wrap items-center gap-3">{accountActions}</div>
        </Container>
      </div>
    </header>
  );
}
