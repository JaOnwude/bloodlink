/**
 * The site footer: brand statement, optional link columns and the safety notice.
 *
 * Link columns come from `siteConfig.footerGroups`; empty groups are not rendered.
 */

import Link from "next/link";

import { Logo } from "@/components/brand/Logo";
import { Container } from "@/components/layout/Container";
import { siteConfig } from "@/lib/site";

export function SiteFooter() {
  const groups = siteConfig.footerGroups.filter((group) => group.links.length > 0);

  return (
    <footer className="bg-night text-ivory">
      <Container className="py-14">
        <div className="grid gap-10 md:grid-cols-[1.4fr_2fr]">
          <div className="max-w-sm">
            <Logo tone="light" />
            <p className="mt-4 text-sm leading-relaxed text-ivory/70">{siteConfig.description}</p>
          </div>

          {groups.length > 0 ? (
            <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
              {groups.map((group) => (
                <nav key={group.title} aria-label={group.title}>
                  <h2 className="font-sans text-sm font-semibold tracking-wide text-ivory">
                    {group.title}
                  </h2>
                  <ul className="mt-4 space-y-3">
                    {group.links.map((link) => (
                      <li key={link.href}>
                        <Link
                          href={link.href}
                          className="text-sm text-ivory/70 transition-colors duration-150 hover:text-ivory"
                        >
                          {link.label}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </nav>
              ))}
            </div>
          ) : null}
        </div>

        <div className="mt-12 flex flex-col gap-3 border-t border-ivory/15 pt-6 text-xs text-ivory/60 sm:flex-row sm:justify-between">
          <p>BloodLink coordinates requests and donors. Final eligibility to donate is always decided by clinical staff at the donation site.</p>
          <p className="shrink-0">&copy; {new Date().getFullYear()} {siteConfig.name}</p>
        </div>
      </Container>
    </footer>
  );
}
