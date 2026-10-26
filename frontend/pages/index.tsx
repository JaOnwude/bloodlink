/**
 * Landing page: the pitch to hospitals first, then families and donors.
 *
 * Hospitals and blood banks are the paying customers, so the page opens with their problem
 * and what BloodLink does about it. It then shows what sets BloodLink apart (Nigeria's
 * digital postcode), how a family can ask for blood, why it can be trusted, what it costs,
 * the invitation to donors, and common questions.
 *
 * Sections alternate in tone (light, white, dark, tinted) so the page has a rhythm, and
 * every section uses the same heading component so the hierarchy stays consistent.
 *
 * Claims about the scale of the problem are written without figures on purpose. Numbers go
 * here only once they have been checked and cited in the project research notes; the facts
 * strip states properties of the product, not usage.
 *
 * The page is written for newcomers. Signed-in visitors can still read it, and reach their
 * own dashboard from the link in the site header.
 */

import {
  BadgeCheck,
  BellRing,
  Building2,
  ClipboardCheck,
  ClipboardList,
  HandHeart,
  HeartHandshake,
  MapPinned,
  MessageCircleWarning,
  MessageSquareText,
  PhoneOff,
  Radar,
  Search,
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
import { FactStrip } from "@/components/landing/FactStrip";
import { Faq } from "@/components/landing/Faq";
import type { FaqItem } from "@/components/landing/Faq";
import { HeroBackdrop } from "@/components/landing/HeroBackdrop";
import { HeroCards } from "@/components/landing/HeroCards";
import { PhotoCarousel } from "@/components/landing/PhotoCarousel";
import { PostcodeAnatomy } from "@/components/landing/PostcodeAnatomy";
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
    icon: <ClipboardCheck className="size-5" aria-hidden="true" />,
    title: "A verified hospital raises a request",
    body: "Blood group, component, units and deadline. Only hospitals checked by our team can send one.",
  },
  {
    icon: <BellRing className="size-5" aria-hidden="true" />,
    title: "The right donors are texted",
    body: "Compatible, eligible today and available, starting in the hospital's own postcode area. Nobody is texted twice about the same request.",
  },
  {
    icon: <HeartHandshake className="size-5" aria-hidden="true" />,
    title: "Donors pledge, and it never overbooks",
    body: "Each pledge takes one unit. When the last unit is taken the request closes itself, even if two donors answer at once.",
  },
  {
    icon: <UserCheck className="size-5" aria-hidden="true" />,
    title: "You confirm who gave",
    body: "Mark each donor as donated, did not attend or deferred at screening. Their waiting period starts, and your figures stay honest.",
  },
];

const POSTCODE_FEATURES: Point[] = [
  {
    icon: <BadgeCheck className="size-5" aria-hidden="true" />,
    title: "Checked with NIPOST at sign-up",
    body: "Hospitals and donors add their postcode by typing it or from their location, and NIPOST confirms it is a real, assigned building.",
  },
  {
    icon: <Radar className="size-5" aria-hidden="true" />,
    title: "Alerts in postcode rings",
    body: "Donors in the hospital's own postcode area hear first, then its district, LGA and state.",
  },
  {
    icon: <MessageSquareText className="size-5" aria-hidden="true" />,
    title: "The postcode in every text",
    body: "Each alert carries the hospital's postcode, so a donor on a basic phone can find the building.",
  },
  {
    icon: <Building2 className="size-5" aria-hidden="true" />,
    title: "Hospitals verified against NIPOST",
    body: "Before a hospital can alert anyone, an administrator compares it with NIPOST's record of the building.",
  },
];

const FAMILY_STEPS: Point[] = [
  {
    icon: <Search className="size-5" aria-hidden="true" />,
    title: "Find the hospital",
    body: "Search by the hospital's postcode or your location. Only hospitals we have verified are listed.",
  },
  {
    icon: <ClipboardList className="size-5" aria-hidden="true" />,
    title: "Tell it what is needed",
    body: "The blood group, the units and the ward or lab slip number from the doctor.",
  },
  {
    icon: <BellRing className="size-5" aria-hidden="true" />,
    title: "The hospital confirms, donors are alerted",
    body: "Once staff confirm your patient, nearby donors are texted. You follow it on your own page and get a text.",
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
    body: "Hospitals see a donor's name and number only after that donor pledges. A donor's postcode is kept to the area, never the building.",
  },
  {
    icon: <HandHeart className="size-6" aria-hidden="true" />,
    title: "No payment for blood",
    body: "Donation stays voluntary and unpaid, as WHO recommends. Hospitals pay for the service, never for the blood.",
  },
];

const FAQS: FaqItem[] = [
  {
    question: "Is BloodLink free?",
    answer:
      "Always free for donors and for families. Pilot hospitals use it free while we agree prices together. Hospitals will pay for the service, never for blood: donation stays voluntary and unpaid.",
  },
  {
    question: "Who can ask for blood?",
    answer:
      "Verified hospitals and blood banks raise requests directly. A patient's family can ask a verified hospital from the Need blood page; the hospital confirms the patient before any donor is alerted.",
  },
  {
    question: "How does BloodLink use Nigeria's digital postcode?",
    answer:
      "Postcodes are checked with NIPOST when hospitals and donors add them. Donors are alerted ring by ring from the hospital's own postcode area, alerts carry the hospital's postcode, and administrators compare each hospital with NIPOST's record of its building.",
  },
  {
    question: "What happens to my personal data?",
    answer:
      "You choose whether to be contacted. Hospitals see a donor's name and number only after that donor pledges. A donor's postcode is cut back to the area before it is stored. We handle data under the Nigeria Data Protection Act.",
  },
  {
    question: "Does BloodLink decide if I can donate?",
    answer:
      "No. It checks waiting periods, age, weight and deferrals so you are only asked when you are likely able to give, but clinical staff at the donation site always make the final decision.",
  },
  {
    question: "What if a donor does not turn up?",
    answer:
      "Hospitals can ask for standby donors. If a pledged donor cancels, does not come or is turned away at screening, the longest-waiting standby donor is called in and texted automatically.",
  },
];

/** Cards with an icon, for lists of reasons (the problem, why it can be trusted). */
function CardGrid({ points, columns }: { points: Point[]; columns: 3 | 4 }) {
  return (
    <ul
      className={cn(
        "grid gap-5 sm:grid-cols-2",
        columns === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3",
      )}
    >
      {points.map((point, index) => (
        <Reveal
          as="li"
          key={point.title}
          delay={index * 60}
          className="group space-y-3 rounded-3xl border border-border bg-surface p-6 shadow-soft transition-[box-shadow,transform] duration-250 ease-brand hover:-translate-y-1 hover:shadow-lift"
        >
          <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-700 transition-colors group-hover:bg-primary-600 group-hover:text-white">
            {point.icon}
          </span>
          <h3 className="font-heading text-lg font-semibold text-ink">{point.title}</h3>
          <p className="text-ink-muted">{point.body}</p>
        </Reveal>
      ))}
    </ul>
  );
}

/**
 * Numbered steps joined by a line, for anything that happens in order.
 *
 * `ring` is the colour of the gap drawn around each number so the line appears to pass
 * behind it; it must match the section's background.
 */
function StepList({ points, ring }: { points: Point[]; ring: string }) {
  return (
    <ol
      className={cn(
        "relative grid gap-8 sm:grid-cols-2",
        points.length === 4 ? "lg:grid-cols-4" : "lg:grid-cols-3",
      )}
    >
      {/* The line behind the numbers, on wide screens where the steps share one row. */}
      <span
        className="absolute top-6 right-[10%] left-6 hidden h-px bg-primary-100 lg:block"
        aria-hidden="true"
      />
      {points.map((point, index) => (
        <Reveal as="li" key={point.title} delay={index * 80} className="relative space-y-3">
          <span
            className={cn(
              "relative flex size-12 items-center justify-center rounded-full bg-primary-600 font-heading text-lg font-semibold text-white shadow-lift ring-8",
              ring,
            )}
          >
            {index + 1}
          </span>
          <h3 className="flex items-start gap-2 font-heading text-lg font-semibold text-ink">
            <span className="mt-1 text-primary-600">{point.icon}</span>
            {point.title}
          </h3>
          <p className="text-ink-muted">{point.body}</p>
        </Reveal>
      ))}
    </ol>
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

      <FactStrip />

      {/* The problem today. */}
      <Section>
        <Container className="space-y-12">
          <Reveal>
            <SectionHeading
              eyebrow="The problem"
              title="Finding blood in an emergency still depends on who you can reach."
            />
          </Reveal>
          <CardGrid points={PROBLEMS} columns={3} />
        </Container>
      </Section>

      {/* How it works. */}
      <Section tone="surface" id="how-it-works">
        <Container className="space-y-14">
          <Reveal>
            <SectionHeading
              eyebrow="How it works"
              title="From request to confirmed donation, in one place."
              lead="Every step a hospital takes today by phone, BloodLink does in a few clicks, and keeps a record of."
            />
          </Reveal>
          <StepList points={STEPS} ring="ring-surface" />
          <Reveal className="pt-2">
            <PhotoCarousel slides={carouselSlides} label="BloodLink at work" />
            <p className="mt-3 text-xs text-ink-muted">
              Photographs from Pexels by{" "}
              {carouselSlides.map((slide) => slide.image.credit?.author).join(", ")}. The people
              shown are not BloodLink donors, patients or staff.
            </p>
          </Reveal>
        </Container>
      </Section>

      {/* Nigeria's digital postcode. */}
      <Section tone="night" id="postcode">
        <Container className="grid items-center gap-12 lg:grid-cols-[1fr_1.1fr]">
          <Reveal>
            <p className="mb-3 text-sm font-semibold tracking-wider text-primary-100 uppercase">
              Built on Nigeria&apos;s postcode
            </p>
            <h2 className="text-title font-semibold text-ivory">
              Every hospital and donor, placed to the building.
            </h2>
            <p className="mt-4 text-lead text-ivory/75">
              BloodLink uses NIPOST&apos;s digital postcode wherever location matters, so
              &ldquo;nearby&rdquo; means a real place, not a guess.
            </p>
            <ul className="mt-8 space-y-5">
              {POSTCODE_FEATURES.map((feature) => (
                <li key={feature.title} className="flex gap-3">
                  <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-white/10 text-primary-100">
                    {feature.icon}
                  </span>
                  <span>
                    <span className="block font-semibold text-ivory">{feature.title}</span>
                    <span className="block text-sm text-ivory/70">{feature.body}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Reveal>
          <Reveal delay={120}>
            <PostcodeAnatomy />
          </Reveal>
        </Container>
      </Section>

      {/* Families. */}
      <Section tone="tint" id="families">
        <Container className="space-y-12">
          <Reveal className="flex flex-wrap items-end justify-between gap-6">
            <SectionHeading
              eyebrow="For families"
              title="Searching for blood for someone you love?"
              lead="Ask the hospital through BloodLink instead of searching alone. No account needed, and nothing to pay."
            />
            <Link href="/find-blood" className={buttonVariants({ size: "lg" })}>
              Find a hospital
            </Link>
          </Reveal>
          <StepList points={FAMILY_STEPS} ring="ring-primary-50" />
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
          <CardGrid points={TRUST} columns={4} />
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
                  <HeartHandshake
                    className="mt-0.5 size-5 shrink-0 text-primary-600"
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>
        </Container>
      </Section>

      {/* Questions. */}
      <Section tone="surface" id="faq">
        <Container className="grid gap-12 lg:grid-cols-[1fr_1.6fr]">
          <Reveal>
            <SectionHeading
              eyebrow="Questions"
              title="What people ask us."
              lead="Something not answered here? Register your hospital and talk to us during the pilot."
            />
          </Reveal>
          <Reveal delay={80}>
            <Faq items={FAQS} />
          </Reveal>
        </Container>
      </Section>

      {/* Closing call to action. */}
      <section className="bg-[linear-gradient(120deg,var(--color-primary-700),var(--color-night)_70%)] py-section text-white">
        <Container size="reading" className="text-center">
          <Reveal>
            <h2 className="text-title font-semibold text-white">
              The next emergency is already on its way.
            </h2>
            <p className="mt-4 text-lead text-white/80">
              Register your hospital now. An administrator verifies it, and you can send your
              first request the same day.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link
                href={REGISTER_HOSPITAL}
                className={cn(
                  buttonVariants({ size: "xl" }),
                  "bg-white text-primary-700 hover:bg-primary-50",
                )}
              >
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
              BloodLink matches and coordinates. It does not perform medical screening: final
              eligibility is always decided by clinical staff at the donation site.
            </p>
          </Reveal>
        </Container>
      </section>
    </>
  );
}
