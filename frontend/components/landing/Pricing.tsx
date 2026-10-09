/**
 * Who pays, and for what: the pricing story for hospitals and blood banks.
 *
 * Hospitals and blood banks are the customers; donors never pay. The tiers describe what
 * each kind of customer gets. Amounts are deliberately not shown: they are being set with
 * the first pilot hospitals from what they spend today on finding blood, and published
 * figures must come from those conversations, not from a guess. Once agreed, put them in
 * the `price` field of each tier.
 */

import { Check } from "lucide-react";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Tier {
  name: string;
  audience: string;
  /** Shown in place of an amount until prices are agreed with pilot partners. */
  price: string;
  priceNote: string;
  features: string[];
  cta: { label: string; href: string };
  highlighted?: boolean;
}

const TIERS: Tier[] = [
  {
    name: "Pilot",
    audience: "For the first private hospitals in Lagos and Abuja",
    price: "Free",
    priceNote: "For three months, in exchange for anonymised fulfilment data.",
    features: [
      "Verified hospital account",
      "Unlimited urgent requests",
      "Matching and SMS alerts to eligible donors",
      "Pledge tracking and donation records",
    ],
    cta: { label: "Apply for the pilot", href: "/register?as=hospital" },
    highlighted: true,
  },
  {
    name: "Hospital",
    audience: "For a single hospital after the pilot",
    price: "Monthly subscription",
    priceNote: "Priced by request volume, set with our pilot partners.",
    features: [
      "Everything in the pilot",
      "Performance figures: time to fulfil, no-show rate",
      "Several staff accounts",
      "Priority support",
    ],
    cta: { label: "Register your hospital", href: "/register?as=hospital" },
  },
  {
    name: "Blood bank and network",
    audience: "For blood banks and hospital groups",
    price: "Annual agreement",
    priceNote: "For several sites, donor drives and reporting.",
    features: [
      "Everything in Hospital, for every site",
      "Donor drives with employers and universities",
      "Reports for management and regulators",
      "Integration with existing systems",
    ],
    cta: { label: "Register your organisation", href: "/register?as=hospital" },
  },
];

export function Pricing() {
  return (
    <div className="grid gap-6 lg:grid-cols-3">
      {TIERS.map((tier) => (
        <article
          key={tier.name}
          className={cn(
            "flex flex-col rounded-3xl border bg-surface p-7",
            tier.highlighted ? "border-primary-600 shadow-lift" : "border-border",
          )}
          aria-labelledby={`tier-${tier.name}`}
        >
          {tier.highlighted ? (
            <p className="mb-3 self-start rounded-full bg-primary-50 px-3 py-1 text-xs font-semibold text-primary-700">
              Open now
            </p>
          ) : null}
          <h3 id={`tier-${tier.name}`} className="font-heading text-xl font-semibold text-ink">
            {tier.name}
          </h3>
          <p className="mt-1 text-sm text-ink-muted">{tier.audience}</p>

          <p className="mt-6 font-heading text-3xl font-semibold text-ink">{tier.price}</p>
          <p className="mt-1 text-sm text-ink-muted">{tier.priceNote}</p>

          <ul className="mt-6 flex-1 space-y-3">
            {tier.features.map((feature) => (
              <li key={feature} className="flex items-start gap-2.5 text-sm text-ink">
                <Check className="mt-0.5 size-4 shrink-0 text-trust-600" aria-hidden="true" />
                {feature}
              </li>
            ))}
          </ul>

          <Link
            href={tier.cta.href}
            className={cn(
              "mt-8",
              buttonVariants({ variant: tier.highlighted ? "default" : "outline", size: "lg" }),
            )}
          >
            {tier.cta.label}
          </Link>
        </article>
      ))}
    </div>
  );
}
