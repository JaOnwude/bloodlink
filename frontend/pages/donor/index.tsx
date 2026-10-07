/**
 * Donor dashboard: eligibility today, the donor's profile and the alerts switch.
 *
 * A donor who has not created a profile yet is invited to do so. Data loads only after the
 * route guard has confirmed the visitor is a signed-in donor, so no request is made for
 * anyone else.
 */

import { BellOff } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { AvailabilityToggle } from "@/components/donor/AvailabilityToggle";
import { EligibilityCard } from "@/components/donor/EligibilityCard";
import { ProfileSummary } from "@/components/donor/ProfileSummary";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { RouteGuard } from "@/components/RouteGuard";
import { Reveal } from "@/components/motion/Reveal";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { useResource } from "@/lib/use-resource";
import type { DonorProfile, Eligibility } from "@/types/api";

function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading your dashboard">
      <Skeleton className="h-10 w-72" />
      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <Skeleton className="h-96" />
        <Skeleton className="h-96" />
      </div>
    </div>
  );
}

function Onboarding() {
  return (
    <Reveal>
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Create your donor profile</CardTitle>
          <CardDescription>It takes about two minutes.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="text-ink-muted">
            Tell us your blood group, where you are and when you last donated. We use it to show
            you when you can donate and to match you with requests nearby. You choose whether to
            be contacted.
          </p>
          <Link href="/donor/profile" className={buttonVariants({ size: "lg" })}>
            Get started
          </Link>
        </CardContent>
      </Card>
    </Reveal>
  );
}

function DashboardContent() {
  const { user } = useAuth();
  const profile = useResource<DonorProfile>("/donors/me");
  const eligibility = useResource<Eligibility>(profile.data ? "/donors/me/eligibility" : null);

  async function saveAvailability(next: boolean) {
    await api.patch("/donors/me/availability", { is_available: next });
    profile.reload();
  }

  if (!profile.loaded) return <DashboardSkeleton />;

  if (profile.error?.status === 404) return <Onboarding />;

  if (profile.error || !profile.data) {
    return (
      <LoadError
        message="We could not load your dashboard. Check your connection and try again."
        onRetry={profile.reload}
      />
    );
  }

  const donor = profile.data;
  const firstName = user?.full_name.split(" ")[0] ?? "";

  return (
    <div className="space-y-8">
      <Reveal>
        <h1 className="text-title font-semibold text-ink">Welcome, {firstName}</h1>
        <p className="mt-2 text-ink-muted">Here is where you stand today.</p>
      </Reveal>

      {!donor.consent_to_contact ? (
        <Reveal>
          <div
            role="status"
            className="flex flex-wrap items-center gap-4 rounded-2xl border border-primary-100 bg-primary-50 p-4 text-sm text-primary-900"
          >
            <BellOff className="size-5 shrink-0" aria-hidden="true" />
            <p className="flex-1">
              You have not agreed to be contacted, so you will not receive any requests.
            </p>
            <Link href="/donor/profile" className={buttonVariants({ variant: "outline", size: "sm" })}>
              Update profile
            </Link>
          </div>
        </Reveal>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <Reveal>
          {eligibility.data ? (
            <EligibilityCard eligibility={eligibility.data} />
          ) : eligibility.error ? (
            <LoadError
              message="We could not check your eligibility just now."
              onRetry={eligibility.reload}
            />
          ) : (
            <Skeleton className="h-96" />
          )}
        </Reveal>

        <Reveal delay={80} className="space-y-6">
          <ProfileSummary profile={donor} />
          <AvailabilityToggle available={donor.is_available} onChange={saveAvailability} />
        </Reveal>
      </div>
    </div>
  );
}

export default function DonorDashboardPage() {
  return (
    <>
      <Head>
        <title>Donor dashboard | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["donor"]}>
            <DashboardContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
