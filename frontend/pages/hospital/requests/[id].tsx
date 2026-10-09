/**
 * One blood request: what was asked for, how far it has got, and the donors who can answer.
 *
 * While the request is open, the ranked, anonymous list of matching donors is shown with a
 * radius control. Once it is fulfilled, closed or expired, matching stops and the page says
 * why. Staff can close an open or fulfilled request from here; the page then reloads so it
 * always shows the current state.
 */

import { ArrowLeft } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";

import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { CloseRequestPanel } from "@/components/requests/CloseRequestPanel";
import { MatchList } from "@/components/requests/MatchList";
import {
  RequestStatusBadge,
  URGENCY_LABELS,
  UrgencyBadge,
} from "@/components/requests/RequestBadges";
import { UnitsProgress } from "@/components/requests/UnitsProgress";
import { RouteGuard } from "@/components/RouteGuard";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { BloodRequest, RequestStatus } from "@/types/api";

/** Why matching has stopped, for each state other than open. */
const NOT_MATCHING: Record<Exclude<RequestStatus, "open">, string> = {
  fulfilled: "Enough donors have pledged, so the request no longer goes to new donors.",
  closed: "This request was closed, so it no longer goes to donors.",
  expired: "The deadline passed before enough donors pledged, so the request has expired.",
};

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
    <Link href="/hospital/requests" className={buttonVariants({ variant: "arrow" })}>
      <ArrowLeft className="!translate-x-0" /> All requests
    </Link>
  );
}

function RequestContent() {
  const router = useRouter();
  const id = router.isReady && typeof router.query.id === "string" ? router.query.id : null;
  const request = useResource<BloodRequest>(id ? `/requests/${id}` : null);

  if (!request.loaded) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading the request">
        <Skeleton className="h-10 w-80" />
        <div className="grid gap-6 lg:grid-cols-5">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80 lg:col-span-3" />
        </div>
      </div>
    );
  }

  // 404: no such request, or another hospital's. 422: the address is not a valid identifier.
  if (request.error?.status === 404 || request.error?.status === 422) {
    return (
      <div className="space-y-5">
        <h1 className="text-title font-semibold text-ink">Request not found</h1>
        <p className="text-ink-muted">This request does not exist, or the link is not correct.</p>
        <BackLink />
      </div>
    );
  }

  if (request.error || !request.data) {
    return (
      <LoadError
        message="We could not load this request. Check your connection and try again."
        onRetry={request.reload}
      />
    );
  }

  const record = request.data;
  const canClose = record.status === "open" || record.status === "fulfilled";

  return (
    <div className="space-y-8">
      <BackLink />

      <Reveal className="flex flex-wrap items-center gap-4">
        <h1 className="text-title font-semibold text-ink">
          {record.recipient_group} {record.component_name.toLowerCase()}
        </h1>
        <RequestStatusBadge status={record.status} />
        {record.status === "open" ? <UrgencyBadge urgency={record.urgency} /> : null}
      </Reveal>

      <div className="grid items-start gap-6 lg:grid-cols-5">
        <Reveal className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Progress</CardTitle>
              <CardDescription>Raised on {formatDateTime(record.created_at)}.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <UnitsProgress needed={record.units_needed} pledged={record.units_pledged} />
              <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                <Detail
                  label="Needed by"
                  value={
                    record.status === "open"
                      ? `${formatDateTime(record.deadline)} (${formatRelative(record.deadline)})`
                      : formatDateTime(record.deadline)
                  }
                />
                <Detail label="Urgency" value={URGENCY_LABELS[record.urgency]} />
                {record.fulfilled_at ? (
                  <Detail label="Fulfilled" value={formatDateTime(record.fulfilled_at)} />
                ) : null}
              </dl>
              {record.notes ? (
                <div>
                  <p className="text-xs tracking-wide text-ink-muted uppercase">Notes for donors</p>
                  <p className="mt-1 text-sm whitespace-pre-line text-ink">{record.notes}</p>
                </div>
              ) : null}
              {canClose ? (
                <CloseRequestPanel request={record} onClosed={request.reload} />
              ) : null}
            </CardContent>
          </Card>
        </Reveal>

        <Reveal className="lg:col-span-3" delay={80}>
          <Card>
            <CardHeader>
              <CardTitle>Matching donors</CardTitle>
              <CardDescription>
                Compatible, eligible and available donors near your hospital, nearest first.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {record.status === "open" ? (
                <MatchList requestId={record.id} />
              ) : (
                <p className="rounded-2xl bg-secondary p-4 text-sm text-ink">
                  {NOT_MATCHING[record.status]}
                </p>
              )}
            </CardContent>
          </Card>
        </Reveal>
      </div>
    </div>
  );
}

export default function RequestDetailPage() {
  return (
    <>
      <Head>
        <title>Blood request | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["hospital_staff"]}>
            <RequestContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
