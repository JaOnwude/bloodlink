/**
 * Example cards floating beside the landing page headline, showing BloodLink at work.
 *
 * Three small cards tell the story at a glance: a verified hospital with its NIPOST
 * postcode, a request filling up as donors in its own postcode area answer, and a donor
 * pledging. They are an illustration, labelled "Example", not live figures. They drift
 * gently for visitors who have not asked for reduced motion.
 */

import { BadgeCheck, BellRing, MapPin } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

function Card({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  return (
    <div
      className={cn(
        "hero-float rounded-2xl bg-white/95 p-4 text-ink shadow-pop ring-1 ring-black/5 backdrop-blur",
        className,
      )}
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}

function Ring({ label, donors, width }: { label: string; donors: number; width: string }) {
  return (
    <li className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-ink-muted">{label}</span>
        <span className="font-medium text-ink tabular-nums">{donors} donors texted</span>
      </div>
      <div className="h-1.5 rounded-full bg-primary-50">
        <div className="h-1.5 rounded-full bg-primary-600" style={{ width }} />
      </div>
    </li>
  );
}

export function HeroCards() {
  return (
    <figure className="relative mx-auto w-full max-w-sm" aria-label="Example of BloodLink at work">
      <Card className="relative z-10 ml-auto w-fit max-w-full" delay={0}>
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          <BadgeCheck className="size-4 text-trust-600" aria-hidden="true" />
          Unity Teaching Hospital
        </p>
        <p className="mt-1 flex items-center gap-1.5 text-xs text-ink-muted">
          <MapPin className="size-3.5" aria-hidden="true" />
          NIPOST postcode{" "}
          <span className="font-mono whitespace-nowrap text-ink">FC-01-A01-KP-27</span>
        </p>
      </Card>

      <Card className="relative -mt-3 space-y-4 p-5" delay={1200}>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold tracking-wider text-primary-600 uppercase">
              Urgent request
            </p>
            <p className="font-heading text-xl font-semibold">O− whole blood</p>
          </div>
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary-50 font-heading font-semibold text-primary-700">
            O−
          </span>
        </div>
        <div>
          <div className="flex justify-between text-sm">
            <span className="text-ink-muted">Units pledged</span>
            <span className="font-semibold tabular-nums">2 of 2</span>
          </div>
          <div className="mt-1.5 h-2 rounded-full bg-trust-50">
            <div className="h-2 w-full rounded-full bg-trust-600" />
          </div>
        </div>
        <ul className="space-y-2.5">
          <Ring label="Same postcode area" donors={3} width="45%" />
          <Ring label="Same district" donors={5} width="75%" />
        </ul>
      </Card>

      <Card className="relative z-10 -mt-4 mr-auto w-60" delay={2400}>
        <p className="flex items-center gap-2 text-sm font-medium">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-success opacity-60 motion-reduce:hidden" />
            <span className="relative inline-flex size-2.5 rounded-full bg-success" />
          </span>
          Donor pledged
        </p>
        <p className="mt-1 flex items-center gap-1.5 text-xs text-ink-muted">
          <BellRing className="size-3.5" aria-hidden="true" />
          Texted with the hospital&apos;s postcode
        </p>
      </Card>

      <figcaption className="mt-3 text-center text-xs text-white/60">Example request</figcaption>
    </figure>
  );
}
