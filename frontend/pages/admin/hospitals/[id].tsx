/**
 * Review page for one hospital: everything an administrator needs to decide, and the
 * decision controls.
 *
 * Shows the hospital's details with a link to see its location on a map, the people who
 * registered it, and, once decided, the outcome. After a decision the page reloads so it
 * always shows the current state.
 */

import { ArrowLeft, ExternalLink } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";

import { DecisionPanel } from "@/components/admin/DecisionPanel";
import { VerificationBadge } from "@/components/hospital/VerificationBadge";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { RouteGuard } from "@/components/RouteGuard";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTimestamp } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { AdminHospital } from "@/types/api";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-ink-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

function BackLink() {
  return (
    <Link href="/admin" className={buttonVariants({ variant: "arrow" })}>
      <ArrowLeft className="!translate-x-0" /> Back to the queue
    </Link>
  );
}

function ReviewContent() {
  const router = useRouter();
  const id = router.isReady && typeof router.query.id === "string" ? router.query.id : null;
  const hospital = useResource<AdminHospital>(id ? `/admin/hospitals/${id}` : null);
  const [notice, setNotice] = useState<string | null>(null);

  function handleChanged(successMessage?: string) {
    setNotice(successMessage ?? null);
    hospital.reload();
  }

  if (!hospital.loaded) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading the hospital">
        <Skeleton className="h-10 w-80" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  // 404: no such hospital. 422: the address in the URL is not a valid identifier.
  if (hospital.error?.status === 404 || hospital.error?.status === 422) {
    return (
      <div className="space-y-5">
        <h1 className="text-title font-semibold text-ink">Hospital not found</h1>
        <p className="text-ink-muted">This hospital does not exist, or the link is not correct.</p>
        <BackLink />
      </div>
    );
  }

  if (hospital.error || !hospital.data) {
    return (
      <LoadError
        message="We could not load this hospital. Check your connection and try again."
        onRetry={hospital.reload}
      />
    );
  }

  const record = hospital.data;
  const mapLink = `https://www.openstreetmap.org/?mlat=${record.latitude}&mlon=${record.longitude}#map=15/${record.latitude}/${record.longitude}`;

  return (
    <div className="space-y-8">
      <BackLink />

      <Reveal className="flex flex-wrap items-center gap-4">
        <h1 className="text-title font-semibold text-ink">{record.name}</h1>
        <VerificationBadge status={record.verification_status} />
      </Reveal>

      {notice ? (
        <div role="status" className="rounded-2xl bg-trust-50 p-4 text-sm font-medium text-trust-700">
          {notice}
        </div>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[3fr_2fr]">
        <Reveal>
          <Card className="h-full">
            <CardHeader>
              <CardTitle>Details</CardTitle>
              <CardDescription>Registered on {formatTimestamp(record.created_at)}.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Detail label="Address" value={record.address} />
                <Detail label="City" value={`${record.city}, ${record.state}`} />
                <Detail label="Contact phone" value={record.contact_phone} />
                <Detail
                  label="Registration number"
                  value={record.registration_number ?? "Not provided"}
                />
                {record.verified_at ? (
                  <Detail label="Verified on" value={formatTimestamp(record.verified_at)} />
                ) : null}
              </dl>

              {record.rejection_reason ? (
                <div className="space-y-1 rounded-2xl bg-secondary p-4 text-sm">
                  <p className="font-medium text-ink">Reason given for the last rejection</p>
                  <p className="text-ink-muted">{record.rejection_reason}</p>
                </div>
              ) : null}

              <a
                href={mapLink}
                target="_blank"
                rel="noopener noreferrer"
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                View on map <ExternalLink />
                <span className="sr-only">(opens in a new tab)</span>
              </a>
            </CardContent>
          </Card>
        </Reveal>

        <div className="space-y-6">
          <Reveal delay={80}>
            <Card>
              <CardHeader>
                <CardTitle>Registered by</CardTitle>
                <CardDescription>The staff accounts linked to this hospital.</CardDescription>
              </CardHeader>
              <CardContent>
                {record.staff.length === 0 ? (
                  <p className="text-sm text-ink-muted">No staff accounts are linked.</p>
                ) : (
                  <ul className="divide-y divide-border">
                    {record.staff.map((member) => (
                      <li key={member.id} className="space-y-0.5 py-3 first:pt-0 last:pb-0">
                        <p className="text-sm font-medium text-ink">{member.full_name}</p>
                        <p className="text-sm text-ink-muted">
                          <a href={`mailto:${member.email}`} className="underline-offset-4 hover:underline">
                            {member.email}
                          </a>
                        </p>
                        {member.phone ? (
                          <p className="text-sm text-ink-muted">
                            <a href={`tel:${member.phone}`} className="underline-offset-4 hover:underline">
                              {member.phone}
                            </a>
                          </p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </Reveal>

          <Reveal delay={160}>
            <Card>
              <CardHeader>
                <CardTitle>Decision</CardTitle>
                <CardDescription>Every decision is recorded with your name.</CardDescription>
              </CardHeader>
              <CardContent>
                <DecisionPanel hospital={record} onChanged={handleChanged} />
              </CardContent>
            </Card>
          </Reveal>
        </div>
      </div>
    </div>
  );
}

export default function HospitalReviewPage() {
  return (
    <>
      <Head>
        <title>Review hospital | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["admin"]}>
            <ReviewContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
