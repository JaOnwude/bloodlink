/**
 * Landing page: the pitch to hospitals first, and the invitation to donors second.
 *
 * Hospitals and blood banks are the paying customers, so the page opens with their problem
 * and what BloodLink does about it, then why they can trust it and what it costs. Donors,
 * who always use BloodLink free, are recruited in their own section further down.
 *
 * Claims about the scale of the problem are written without figures on purpose. Numbers go
 * here only once they have been checked and cited in the project research notes.
 *
 * The page is written for newcomers. Signed-in visitors can still read it, and reach their
 * own dashboard from the link in the site header.
 */

import {
  BellRing,
  ClipboardCheck,
  HandHeart,
  HeartHandshake,
  MapPinned,
  MessageCircleWarning,
  PhoneOff,
  ShieldCheck,
  Timer,
  UserCheck,
  UsersRound,
} from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import type { ReactNode } from "react";

import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { HeroBackdrop } from "@/components/landing/HeroBackdrop";
import { HeroCards } from "@/components/landing/HeroCards";
import { PhotoCarousel } from "@/components/landing/PhotoCarousel";
import { Pricing } from "@/components/landing/Pricing";
import { Reveal } from "@/components/motion/Reveal";
import { buttonVariants } from "@/components/ui/button";
import { carouselSlides, heroPhotos } from "@/lib/images";
import { siteConfig } from "@/lib/site";
import { cn } from "@/lib/utils";

const REGISTER_HOSPITAL = "/register?as=hospital";
const REGISTER_DONOR = "/register?as=donor";

/** Short trust signals above the headline. */
const HERO_BADGES = [
  { icon: <ShieldCheck className="size-3.5" aria-hidden="true" />, label: "Verified hospitals only" },
  { icon: <MapPinned className="size-3.5" aria-hidden="true" />, label: "Built on Nigeria's postcode" },
  { icon: <HandHeart className="size-3.5" aria-hidden="true" />, label: "Always free for donors" },
];

interface Point {
  icon: ReactNode;
  title: string;
  body: string;
}

const PROBLEMS: Point[] = [
  {
    icon: <PhoneOff className="size-6" aria-hidden="true" />,
    title: "The search starts on the phone",
    body: "When a patient needs blood now, staff call blood banks, relatives and WhatsApp groups one by one, while the clock runs.",
  },
  {
    icon: <MessageCircleWarning className="size-6" aria-hidden="true" />,
    title: "Willing is not the same as able",
    body: "Appeals reach people with the wrong blood group, people who gave last month, and people across the city.",
  },
  {
    icon: <UsersRound className="size-6" aria-hidden="true" />,
    title: "Nobody knows who is coming",
    body: "Promises made in a chat are not tracked. Too many donors turn up, or none, and nobody can tell which until it is too late.",
  },
];

const STEPS: Point[] = [
  {
    icon: <ClipboardCheck className="size-6" aria-hidden="true" />,
    title: "A verified hospital raises a request",
    body: "Blood group, component, units and deadline. Only hospitals checked by our team can send one.",
  },
  {
    icon: <BellRing className="size-6" aria-hidden="true" />,
    title: "The right donors are texted",
    body: "Compatible, eligible today, available and nearby, nearest first. Nobody is texted twice about the same request.",
  },
  {
    icon: <HeartHandshake className="size-6" aria-hidden="true" />,
    title: "Donors pledge, and it never overbooks",
    body: "Each pledge takes one unit. When the last unit is taken the request closes itself, even if two donors answer at once.",
  },
  {
    icon: <UserCheck className="size-6" aria-hidden="true" />,
    title: "You confirm who gave",
    body: "Mark each donor as donated or did not attend. Their waiting period starts, and your figures stay honest.",
  },
];

const TRUST: Point[] = [
  {
    icon: <ShieldCheck className="size-6" aria-hidden="true" />,
    title: "Verified hospitals only",
    body: "Every hospital is reviewed before it can contact a donor, so every alert is real.",
  },
  {
    icon: <Timer className="size-6" aria-hidden="true" />,
    title: "Eligibility enforced",
    body: "Waiting periods, age, weight and deferrals are checked before a donor is offered. Clinical staff still decide on the day.",
  },
  {
    icon: <MapPinned className="size-6" aria-hidden="true" />,
    title: "Donor privacy by default",
    body: "Hospitals see a donor's name and number only after that donor pledges. On the map, donors are shown to the nearest kilometre.",
  },
  {
    icon: <HandHeart className="size-6" aria-hidden="true" />,
    title: "No payment for blood",
    body: "Donation stays voluntary and unpaid, as WHO recommends. Hospitals pay for the service, never for the blood.",
  },
];

function PointGrid({ points, columns }: { points: Point[]; columns: 3 | 4 }) {
  return (
    <ul className={`grid gap-6 sm:grid-cols-2 ${columns === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
      {points.map((point, index) => (
        <Reveal as="li" key={point.title} delay={index * 60} className="space-y-3">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
            {point.icon}
          </span>
          <h3 className="font-heading text-lg font-semibold text-ink">{point.title}</h3>
          <p className="text-ink-muted">{point.body}</p>
        </Reveal>
      ))}
    </ul>
  );
}

export default function HomePage() {
  return (
    <>
      <Head>
        <title>BloodLink: urgent blood, matched to donors who can give</title>
        <meta name="description" content={siteConfig.description} />
      </Head>

      {/* Hero: the hospital's problem in one line, over photos of blood being given. */}
      <section className="relative isolate overflow-hidden">
        <HeroBackdrop photos={heroPhotos} />
        <Container className="grid min-h-[calc(100svh-4.5rem)] items-center gap-12 py-20 lg:grid-cols-[1.25fr_1fr] lg:py-24">
          <Reveal>
            <ul className="mb-7 flex flex-wrap gap-2" aria-label="Why hospitals trust BloodLink">
              {HERO_BADGES.map((badge) => (
                <li
                  key={badge.label}
                  className="flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5 text-xs font-medium text-white ring-1 ring-white/20 backdrop-blur"
                >
                  {badge.icon}
                  {badge.label}
                </li>
              ))}
            </ul>
            <p className="mb-4 text-sm font-semibold tracking-wider text-primary-100 uppercase">
              For hospitals and blood banks
            </p>
            <h1 className="max-w-3xl text-display font-semibold text-white lg:text-[3.25rem] lg:leading-[1.08] xl:text-[3.75rem]">
              When a hospital needs O-negative tonight,{" "}
              <span className="text-primary-500">find donors who can actually give.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lead text-white/80">
              BloodLink texts compatible, eligible donors near your hospital, starting in your
              own postcode area, tracks every pledge, and closes the request the moment you
              have enough.
            </p>
            <div className="mt-9 flex flex-wrap items-center gap-3">
              <Link href={REGISTER_HOSPITAL} className={buttonVariants({ size: "xl" })}>
                Register your hospital
              </Link>
              <Link
                href="/find-blood"
                className={cn(
                  buttonVariants({ variant: "outline", size: "xl" }),
                  "border-white/70 text-white hover:bg-white hover:text-ink",
                )}
              >
                Need blood for a patient?
              </Link>
            </div>
            <p className="mt-6 text-sm text-white/70">
              Free for pilot hospitals. Always free for donors.{" "}
              <Link
                href={REGISTER_DONOR}
                className="font-medium text-white underline-offset-4 hover:underline"
              >
                Become a donor
              </Link>
            </p>
          </Reveal>
          <Reveal delay={160} className="hidden lg:block">
            <HeroCards />
          </Reveal>
        </Container>
        <p className="absolute right-5 bottom-5 hidden text-[11px] text-white/50 sm:block">
          Photos: Pexels. The people shown are models, not BloodLink users.
        </p>
      </section>

      {/* The problem today. */}
      <Section tone="night">
        <Container className="space-y-12">
          <Reveal className="max-w-2xl">
            <p className="mb-3 text-sm font-semibold tracking-wider text-primary-100 uppercase">
              The problem
            </p>
            <h2 className="text-title font-semibold text-ivory">
              Finding blood in an emergency still depends on who you can reach.
            </h2>
          </Reveal>
          <ul className="grid gap-8 md:grid-cols-3">
            {PROBLEMS.map((point, index) => (
              <Reveal as="li" key={point.title} delay={index * 60} className="space-y-3">
                <span className="flex size-12 items-center justify-center rounded-2xl bg-ivory/10 text-primary-100">
                  {point.icon}
                </span>
                <h3 className="font-heading text-lg font-semibold text-ivory">{point.title}</h3>
                <p className="text-ivory/75">{point.body}</p>
              </Reveal>
            ))}
          </ul>
        </Container>
      </Section>

      {/* How it works. */}
      <Section id="how-it-works">
        <Container className="space-y-12">
          <Reveal>
            <SectionHeading
              eyebrow="How it works"
              title="From request to confirmed donation, in one place."
              lead="Every step a hospital takes today by phone, BloodLink does in a few clicks, and keeps a record of."
            />
          </Reveal>
          <PointGrid points={STEPS} columns={4} />
          <Reveal className="pt-4">
            <PhotoCarousel slides={carouselSlides} label="BloodLink at work" />
            <p className="mt-3 text-xs text-ink-muted">
              Photographs from Pexels by{" "}
              {carouselSlides.map((slide) => slide.image.credit?.author).join(", ")}. The people shown
              are not BloodLink donors, patients or staff.
            </p>
          </Reveal>
        </Container>
      </Section>

      {/* Why it can be trusted. */}
      <Section tone="surface">
        <Container className="space-y-12">
          <Reveal>
            <SectionHeading
              eyebrow="Built for trust"
              title="Safe for patients, fair to donors."
              lead="Existing tools either move stock between blood banks or match people in a chat and stop there. BloodLink is the closed loop in between: verified requests, enforced eligibility, tracked donations."
            />
          </Reveal>
          <PointGrid points={TRUST} columns={4} />
        </Container>
      </Section>

      {/* Who pays. */}
      <Section id="pricing">
        <Container className="space-y-12">
          <Reveal>
            <SectionHeading
              eyebrow="Pricing"
              title="Hospitals pay for faster blood. Donors never pay."
              lead="We are starting with private hospitals and blood banks in Lagos and Abuja. Pilot hospitals use BloodLink free while we set prices together, based on what finding blood costs you today."
            />
          </Reveal>
          <Reveal delay={80}>
            <Pricing />
          </Reveal>
        </Container>
      </Section>

      {/* Donors. */}
      <Section tone="tint" id="donors">
        <Container className="grid items-center gap-10 lg:grid-cols-[1.2fr_1fr]">
          <Reveal>
            <SectionHeading
              eyebrow="For donors"
              title="Give blood when it counts, close to home."
              lead="We only contact you when a verified hospital near you needs your blood group and you are able to give. You choose when you are available, and you can pause alerts at any time. It is always free."
            />
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href={REGISTER_DONOR} className={buttonVariants({ size: "lg" })}>
                Become a donor
              </Link>
              <Link href="/login" className={buttonVariants({ variant: "ghost", size: "lg" })}>
                I already have an account
              </Link>
            </div>
          </Reveal>
          <Reveal delay={100}>
            <ul className="space-y-4 rounded-3xl bg-surface p-7 shadow-soft">
              {[
                "See when you can donate next, for each kind of donation",
                "Get a text only for requests you can actually answer",
                "Your number is shared only with a hospital you pledge to",
                "A record of every donation you have given",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3 text-ink">
                  <HeartHandshake className="mt-0.5 size-5 shrink-0 text-primary-600" aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </Container>
      </Section>

      {/* Closing call to action. */}
      <Section>
        <Container size="reading" className="text-center">
          <Reveal>
            <h2 className="text-title font-semibold text-ink">
              The next emergency is already on its way.
            </h2>
            <p className="mt-4 text-lead text-ink-muted">
              Register your hospital now. An administrator verifies it, and you can send your
              first request the same day.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link href={REGISTER_HOSPITAL} className={buttonVariants({ size: "xl" })}>
                Register your hospital
              </Link>
              <Link href={REGISTER_DONOR} className={buttonVariants({ variant: "outline", size: "xl" })}>
                Become a donor
              </Link>
            </div>
            <p className="mt-6 text-sm text-ink-muted">
              BloodLink matches and coordinates. It does not perform medical screening: final
              eligibility is always decided by clinical staff at the donation site.
            </p>
          </Reveal>
        </Container>
      </Section>
    </>
  );
}
