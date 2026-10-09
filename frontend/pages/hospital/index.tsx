/**
 * Hospital dashboard: open blood requests, performance figures, the facility's details and
 * its review status.
 *
 * Staff who have not registered a hospital yet are invited to. The page explains what each
 * verification state means and what to do next, including how to correct and resubmit after
 * a rejection. Once the hospital is verified, its open requests are listed at the top with a
 * shortcut to raise a new one. Data loads only after the route guard has confirmed the
 * visitor is signed-in hospital staff.
 */

import { Inbox, Plus } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { HospitalStats } from "@/components/hospital/HospitalStats";
import { VerificationBadge } from "@/components/hospital/VerificationBadge";
import { VerificationSteps } from "@/components/hospital/VerificationSteps";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { RequestSummaryCard } from "@/components/requests/RequestSummaryCard";
import { RouteGuard } from "@/components/RouteGuard";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTimestamp, placeName } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { Hospital, RequestPage } from "@/types/api";

/** How many open requests the dashboard shows before linking to the full list. */
const OPEN_REQUESTS_SHOWN = 3;

function DashboardSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading your hospital">
      <Skeleton className="h-10 w-80" />
      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-80" />
        <Skeleton className="h-80" />
      </div>
    </div>
  );
}

function Onboarding() {
  return (
    <Reveal>
      <Card className="mx-auto max-w-xl">
        <CardHeader>
          <CardTitle>Register your hospital</CardTitle>
          <CardDescription>An administrator reviews every hospital before it can send a request.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <p className="text-ink-muted">
            Tell us the name, address and contact number of your hospital or blood bank. Once an
            administrator has verified it, you can request blood from donors nearby. Verification
            keeps every alert trustworthy for the people who receive it.
          </p>
          <Link href="/hospital/register" className={buttonVariants({ size: "lg" })}>
            Register your hospital
          </Link>
        </CardContent>
      </Card>
    </Reveal>
  );
}

function StatusMessage({ hospital }: { hospital: Hospital }) {
  if (hospital.verification_status === "verified") {
    return (
      <div className="space-y-2 rounded-2xl bg-trust-50 p-4 text-sm text-trust-700">
        <p className="font-medium">Your hospital is verified</p>
        <p>
          {hospital.verified_at ? `Verified on ${formatTimestamp(hospital.verified_at)}. ` : ""}
          Donors will see requests from {hospital.name} as coming from a verified hospital.
        </p>
      </div>
    );
  }

  if (hospital.verification_status === "rejected") {
    return (
      <div className="space-y-3 rounded-2xl bg-secondary p-4 text-sm text-ink">
        <p className="font-medium">An administrator asked for changes</p>
        {hospital.rejection_reason ? (
          <blockquote className="border-l-2 border-primary-600 pl-3 text-ink-muted">
            {hospital.rejection_reason}
          </blockquote>
        ) : null}
        <Link
          href="/hospital/register"
          className={buttonVariants({ variant: "default", size: "sm" })}
        >
          Correct and resubmit
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-2 rounded-2xl bg-primary-50 p-4 text-sm text-primary-900">
      <p className="font-medium">Waiting for review</p>
      <p>
        An administrator checks every hospital before it can send a request. This keeps donors
        safe. You will be able to raise requests as soon as yours is verified.
      </p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-ink-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

function OpenRequests() {
  const page = useResource<RequestPage>(`/requests?status=open&limit=${OPEN_REQUESTS_SHOWN}`);
  const more = page.data ? page.data.total - page.data.items.length : 0;

  return (
    <Reveal className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-heading font-semibold text-ink">Open requests</h2>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/hospital/requests"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            All requests
          </Link>
          <Link href="/hospital/requests/new" className={buttonVariants({ size: "sm" })}>
            <Plus /> New request
          </Link>
        </div>
      </div>

      {!page.loaded ? (
        <Skeleton className="h-32" role="status" aria-label="Loading open requests" />
      ) : page.error || !page.data ? (
        <LoadError
          message="We could not load your open requests. Check your connection and try again."
          onRetry={page.reload}
        />
      ) : page.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-10 text-center">
          <Inbox className="size-8 text-ink-muted" aria-hidden="true" />
          <p className="text-ink">No open requests. Raise one when a patient needs blood.</p>
        </div>
      ) : (
        <>
          <ul className="space-y-4">
            {page.data.items.map((request) => (
              <li key={request.id}>
                <RequestSummaryCard request={request} />
              </li>
            ))}
          </ul>
          {more > 0 ? (
            <p className="text-sm text-ink-muted">
              {more} more open {more === 1 ? "request" : "requests"}.{" "}
              <Link
                href="/hospital/requests"
                className="font-medium text-primary underline-offset-4 hover:underline"
              >
                See them all
              </Link>
            </p>
          ) : null}
        </>
      )}
    </Reveal>
  );
}

function DashboardContent() {
  const hospital = useResource<Hospital>("/hospitals/me");

  if (!hospital.loaded) return <DashboardSkeleton />;

  if (hospital.error?.status === 404) return <Onboarding />;

  if (hospital.error || !hospital.data) {
    return (
      <LoadError
        message="We could not load your hospital. Check your connection and try again."
        onRetry={hospital.reload}
      />
    );
  }

  const record = hospital.data;

  return (
    <div className="space-y-8">
      <Reveal className="flex flex-wrap items-center gap-4">
        <h1 className="text-title font-semibold text-ink">{record.name}</h1>
        <VerificationBadge status={record.verification_status} />
      </Reveal>

      {record.verification_status === "verified" ? (
        <>
          <OpenRequests />
          <Reveal>
            <HospitalStats />
          </Reveal>
        </>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Reveal>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Verification</CardTitle>
              <CardDescription>Where your hospital is in the review.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <VerificationSteps status={record.verification_status} />
              <StatusMessage hospital={record} />
            </CardContent>
          </Card>
        </Reveal>

        <Reveal delay={80}>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Hospital details</CardTitle>
              <CardDescription>
                Registered on {formatTimestamp(record.created_at)}.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Detail label="Address" value={record.address} />
                <Detail label="City" value={placeName(record.city, record.state)} />
                <Detail label="Contact phone" value={record.contact_phone} />
                <Detail
                  label="Registration number"
                  value={record.registration_number ?? "Not provided"}
                />
              </dl>
              {record.verification_status !== "verified" ? (
                <Link
                  href="/hospital/register"
                  className={buttonVariants({ variant: "outline", size: "sm" })}
                >
                  Edit details
                </Link>
              ) : (
                <p className="text-sm text-ink-muted">
                  Details of a verified hospital can only be changed by an administrator.
                </p>
              )}
            </CardContent>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}

export default function HospitalDashboardPage() {
  return (
    <>
      <Head>
        <title>Hospital dashboard | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["hospital_staff"]}>
            <DashboardContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
