/**
 * Design system reference page.
 *
 * Shows every colour, type size, button, form control and motion pattern in one place, so
 * the visual language can be reviewed before screens are built with it. It is excluded from
 * search engines. Remove it, or restrict it to development, before a public launch.
 */

import { ArrowRight, ShieldCheck, TriangleAlert } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import type { ReactNode } from "react";

import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { SectionHeading } from "@/components/layout/SectionHeading";
import { Reveal } from "@/components/motion/Reveal";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface SwatchProps {
  name: string;
  className: string;
  note?: string;
}

function Swatch({ name, className, note }: SwatchProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface">
      <div className={`h-20 border-b border-border ${className}`} />
      <div className="p-3">
        <p className="text-sm font-medium text-ink">{name}</p>
        {note ? <p className="text-xs text-ink-muted">{note}</p> : null}
      </div>
    </div>
  );
}

function SwatchGrid({ children }: { children: ReactNode }) {
  return <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">{children}</div>;
}

const buttonVariantNames = ["default", "outline", "secondary", "ghost", "destructive"] as const;
const buttonSizeNames = ["xs", "sm", "default", "lg", "xl"] as const;

export default function DesignSystemPage() {
  return (
    <>
      <Head>
        <title>Design system | BloodLink</title>
        <meta name="robots" content="noindex, nofollow" />
      </Head>

      <Section tone="canvas">
        <Container>
          <SectionHeading
            eyebrow="Design system"
            title="One visual language for every screen"
            lead="Colours, type, buttons, forms and motion, all driven by the tokens in styles/globals.css."
          />
        </Container>
      </Section>

      <Section tone="surface" className="py-16!">
        <Container className="space-y-10">
          <h2 className="font-heading text-heading font-semibold text-ink">Colour</h2>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Neutrals</p>
            <SwatchGrid>
              <Swatch name="canvas" className="bg-canvas" note="Page background" />
              <Swatch name="surface" className="bg-surface" note="Cards, inputs" />
              <Swatch name="ink" className="bg-ink" note="Primary text" />
              <Swatch name="ink-muted" className="bg-ink-muted" note="Secondary text" />
              <Swatch name="ivory" className="bg-ivory" note="Text on dark" />
              <Swatch name="night" className="bg-night" note="Dark sections" />
            </SwatchGrid>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Crimson (brand)</p>
            <SwatchGrid>
              <Swatch name="primary-50" className="bg-primary-50" note="Tints" />
              <Swatch name="primary-100" className="bg-primary-100" />
              <Swatch name="primary-500" className="bg-primary-500" note="Highlights" />
              <Swatch name="primary-600" className="bg-primary-600" note="Buttons, links" />
              <Swatch name="primary-700" className="bg-primary-700" note="Hover" />
              <Swatch name="primary-900" className="bg-primary-900" note="Deep accents" />
            </SwatchGrid>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Trust and status</p>
            <SwatchGrid>
              <Swatch name="trust-50" className="bg-trust-50" />
              <Swatch name="trust-600" className="bg-trust-600" note="Verified" />
              <Swatch name="trust-700" className="bg-trust-700" />
              <Swatch name="success" className="bg-success" />
              <Swatch name="warning" className="bg-warning" />
              <Swatch name="danger" className="bg-danger" />
            </SwatchGrid>
          </div>
        </Container>
      </Section>

      <Section tone="canvas" className="py-16!">
        <Container className="space-y-8">
          <h2 className="font-heading text-heading font-semibold text-ink">Typography</h2>
          <div className="space-y-6">
            <div>
              <p className="mb-1 text-xs text-ink-muted">text-display (Fraunces)</p>
              <p className="font-heading text-display font-semibold text-ink">Find donors who can give</p>
            </div>
            <div>
              <p className="mb-1 text-xs text-ink-muted">text-title</p>
              <p className="font-heading text-title font-semibold text-ink">Verified hospitals only</p>
            </div>
            <div>
              <p className="mb-1 text-xs text-ink-muted">text-heading</p>
              <p className="font-heading text-heading font-semibold text-ink">How a request becomes a donation</p>
            </div>
            <div>
              <p className="mb-1 text-xs text-ink-muted">text-lead (Inter)</p>
              <p className="max-w-reading text-lead text-ink-muted">
                Every alert comes from a hospital an administrator has verified, and every
                pledge is tracked through to a confirmed donation.
              </p>
            </div>
            <div>
              <p className="mb-1 text-xs text-ink-muted">Body</p>
              <p className="max-w-reading text-base text-ink">
                Body text is set at a comfortable size and line height, with a measure short
                enough to read without effort on any screen.
              </p>
            </div>
          </div>
        </Container>
      </Section>

      <Section tone="surface" className="py-16!">
        <Container className="space-y-10">
          <h2 className="font-heading text-heading font-semibold text-ink">Buttons</h2>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Variants</p>
            <div className="flex flex-wrap items-center gap-3">
              {buttonVariantNames.map((variant) => (
                <Button key={variant} variant={variant}>
                  {variant}
                </Button>
              ))}
              <Button disabled>disabled</Button>
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Sizes</p>
            <div className="flex flex-wrap items-center gap-3">
              {buttonSizeNames.map((size) => (
                <Button key={size} size={size}>
                  {size}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <p className="text-sm font-medium text-ink-muted">Links styled as buttons, and text actions</p>
            <div className="flex flex-wrap items-center gap-6">
              <Link href="/" className={buttonVariants({ size: "lg" })}>
                Primary link
              </Link>
              <Link href="/" className={buttonVariants({ variant: "outline", size: "lg" })}>
                Outline link
              </Link>
              <Link href="/" className={buttonVariants({ variant: "arrow" })}>
                See how it works <ArrowRight />
              </Link>
              <Link href="/" className={buttonVariants({ variant: "link" })}>
                Plain text link
              </Link>
            </div>
          </div>
        </Container>
      </Section>

      <Section tone="canvas" className="py-16!">
        <Container className="space-y-10">
          <h2 className="font-heading text-heading font-semibold text-ink">Forms, cards and status</h2>

          <div className="grid gap-8 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Form controls</CardTitle>
                <CardDescription>Labels are always visible and linked to their fields.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-2">
                  <Label htmlFor="ds-email">Email address</Label>
                  <Input id="ds-email" type="email" placeholder="you@example.com" />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ds-invalid">Password</Label>
                  <Input
                    id="ds-invalid"
                    type="password"
                    aria-invalid="true"
                    aria-describedby="ds-invalid-help"
                    defaultValue="short"
                  />
                  <p id="ds-invalid-help" className="flex items-center gap-1.5 text-sm text-danger">
                    <TriangleAlert className="size-4" aria-hidden="true" />
                    Password must be at least 15 characters long.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Status badges</CardTitle>
                <CardDescription>Colour is always paired with an icon and words.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-3">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-trust-50 px-3 py-1 text-sm font-medium text-trust-700">
                  <ShieldCheck className="size-4" aria-hidden="true" />
                  Verified hospital
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-50 px-3 py-1 text-sm font-medium text-primary-700">
                  Pending review
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-sm font-medium text-ink-muted">
                  Rejected
                </span>
              </CardContent>
            </Card>
          </div>
        </Container>
      </Section>

      <Section tone="night">
        <Container className="space-y-10">
          <SectionHeading
            eyebrow="Motion"
            title="Content eases into place as you scroll"
            lead="Each card below fades and rises once, staggered by 80 milliseconds. With reduced motion switched on in your system settings, they simply appear."
          />
          <div className="grid gap-6 md:grid-cols-3">
            {["Hospital posts a request", "Eligible donors are alerted", "Donation is confirmed"].map(
              (label, index) => (
                <Reveal key={label} delay={index * 80}>
                  <div className="h-full rounded-3xl border border-ivory/15 bg-ivory/5 p-6">
                    <p className="font-heading text-heading font-semibold text-ivory">{index + 1}</p>
                    <p className="mt-3 text-ivory/80">{label}</p>
                  </div>
                </Reveal>
              ),
            )}
          </div>
        </Container>
      </Section>
    </>
  );
}
