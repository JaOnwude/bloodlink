/**
 * Donor dashboard: eligibility today, the profile and alerts switch, the open requests the
 * donor can answer, and their pledges.
 *
 * A donor who has not created a profile yet is invited to do so. Data loads only after the
 * route guard has confirmed the visitor is a signed-in donor, so no request is made for
 * anyone else.
 */

import { BellOff, HeartPulse } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { AvailabilityToggle } from "@/components/donor/AvailabilityToggle";
import { EligibilityCard } from "@/components/donor/EligibilityCard";
import { OpenRequestCard } from "@/components/donor/OpenRequestCard";
import { PledgeHistory } from "@/components/donor/PledgeHistory";
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
import type {
  DonorPledgePage,
  DonorProfile,
  Eligibility,
  OpenRequestsForDonor,
} from "@/types/api";

// The radius the server searches when none is given; shown until the answer arrives.
const DEFAULT_RADIUS_KM = 25;
// How many pledges the dashboard lists.
const HISTORY_SHOWN = 10;

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

function SectionSkeleton({ label }: { label: string }) {
  return (
    <div className="space-y-4" role="status" aria-label={label}>
      <Skeleton className="h-40" />
      <Skeleton className="h-40" />
    </div>
  );
}

/**
 * The open requests the donor can answer, and their own pledges.
 *
 * Both lists are reloaded together after any pledge or cancellation, because one change
 * affects both: a new pledge marks the request card and adds a history entry.
 */
function Activity() {
  const requests = useResource<OpenRequestsForDonor>("/donors/me/requests");
  const pledges = useResource<DonorPledgePage>(`/donors/me/pledges?limit=${HISTORY_SHOWN}`);

  function reloadBoth() {
    requests.reload();
    pledges.reload();
  }

  const activePledge = pledges.data?.items.find((item) => item.status === "pledged") ?? null;

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[3fr_2fr]">
      <Reveal className="space-y-4">
        <div>
          <h2 className="text-heading font-semibold text-ink">Requests near you</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Verified hospitals within {requests.data?.radius_km ?? DEFAULT_RADIUS_KM} km that
            need your blood group, and that you can give to today. Most urgent first.
          </p>
        </div>
        {!requests.loaded ? (
          <SectionSkeleton label="Loading requests near you" />
        ) : requests.error || !requests.data ? (
          <LoadError
            message="We could not load requests near you. Check your connection and try again."
            onRetry={requests.reload}
          />
        ) : requests.data.items.length === 0 ? (
          <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-10 text-center">
            <HeartPulse className="size-8 text-ink-muted" aria-hidden="true" />
            <p className="text-ink">No hospital near you needs your blood group right now.</p>
            <p className="max-w-md text-sm text-ink-muted">
              Keep your alerts on and we will let you know when one does.
            </p>
          </div>
        ) : (
          <ul className="space-y-4">
            {requests.data.items.map((item) => (
              <li key={item.id}>
                <OpenRequestCard
                  request={item}
                  pledgedElsewhere={activePledge !== null && activePledge.request.id !== item.id}
                  onChanged={reloadBoth}
                />
              </li>
            ))}
          </ul>
        )}
      </Reveal>

      <Reveal delay={80} className="space-y-4">
        <h2 className="text-heading font-semibold text-ink">Your pledges</h2>
        {!pledges.loaded ? (
          <SectionSkeleton label="Loading your pledges" />
        ) : pledges.error || !pledges.data ? (
          <LoadError
            message="We could not load your pledges. Check your connection and try again."
            onRetry={pledges.reload}
          />
        ) : (
          <PledgeHistory
            pledges={pledges.data.items}
            total={pledges.data.total}
            onChanged={reloadBoth}
          />
        )}
      </Reveal>
    </div>
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

      <Activity />
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
