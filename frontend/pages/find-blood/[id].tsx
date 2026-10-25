/**
 * A family's private page for following their appeal to a hospital.
 *
 * The address is the appeal's own unguessable id, so only someone with the link can open
 * it. It shows where the appeal stands and, once the hospital has confirmed it, how many
 * donors have pledged. It never shows any donor or any of the family's details.
 */

import { CircleCheck, CircleX, Clock, Phone } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";

import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTimestamp } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { FamilyRequestTracking } from "@/types/api";

function Progress({ tracking }: { tracking: FamilyRequestTracking }) {
  if (tracking.status === "pending") {
    return (
      <div className="flex items-start gap-3 rounded-2xl bg-surface p-5 ring-1 ring-border">
        <Clock className="mt-0.5 size-5 shrink-0 text-ink-muted" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-semibold text-ink">Waiting for the hospital to confirm</p>
          <p className="text-sm text-ink-muted">
            Staff will check your patient on the ward. You will get a text when they answer. No
            donor is alerted until then.
          </p>
        </div>
      </div>
    );
  }
  if (tracking.status === "declined") {
    return (
      <div className="flex items-start gap-3 rounded-2xl bg-primary-50 p-5">
        <CircleX className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden="true" />
        <div className="space-y-1">
          <p className="font-semibold text-ink">The hospital could not accept this request</p>
          {tracking.decline_reason ? (
            <p className="text-sm text-ink">Reason: {tracking.decline_reason}</p>
          ) : null}
          <p className="text-sm text-ink-muted">Call the hospital to talk it through.</p>
        </div>
      </div>
    );
  }

  const pledged = tracking.units_pledged ?? 0;
  const done = tracking.request_status === "fulfilled" || pledged >= tracking.units_needed;
  return (
    <div className="flex items-start gap-3 rounded-2xl bg-trust-50 p-5">
      <CircleCheck className="mt-0.5 size-5 shrink-0 text-trust-700" aria-hidden="true" />
      <div className="space-y-1">
        <p className="font-semibold text-ink">
          {done ? "Every unit has a donor" : "Confirmed. Donors are being alerted"}
        </p>
        <p className="text-sm text-ink">
          {pledged} of {tracking.units_needed} units pledged by donors.
        </p>
        <p className="text-sm text-ink-muted">
          Donors give at the hospital. The hospital calls you if anything changes.
        </p>
      </div>
    </div>
  );
}

function Tracking({ id }: { id: string }) {
  const tracking = useResource<FamilyRequestTracking>(`/public/family-requests/${id}`);

  if (!tracking.loaded) return <Skeleton className="h-64" />;
  if (tracking.error?.status === 404 || tracking.error?.status === 422) {
    return (
      <div className="space-y-4">
        <h1 className="text-title font-semibold text-ink">Request not found</h1>
        <p className="text-ink-muted">Check the link you were given.</p>
      </div>
    );
  }
  if (tracking.error || !tracking.data) {
    return (
      <LoadError
        message="We could not load your request. Check your connection and try again."
        onRetry={tracking.reload}
      />
    );
  }

  const data = tracking.data;
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <p className="text-sm text-ink-muted">Sent {formatTimestamp(data.created_at)}</p>
        <h1 className="text-title font-semibold text-ink">
          {data.units_needed} {data.units_needed === 1 ? "unit" : "units"} of {data.recipient_group}{" "}
          {data.component_name.toLowerCase()}
        </h1>
        <p className="text-ink-muted">
          At {data.hospital_name}
          {data.hospital_postcode ? ` · ${data.hospital_postcode}` : ""}
        </p>
      </div>

      <Progress tracking={data} />

      <div className="flex flex-wrap gap-3">
        <a href={`tel:${data.hospital_phone}`} className={buttonVariants({ variant: "outline" })}>
          <Phone />
          Call the hospital
        </a>
        <button
          type="button"
          onClick={tracking.reload}
          className={buttonVariants({ variant: "ghost" })}
        >
          Refresh
        </button>
      </div>

      <p className="text-sm text-ink-muted">
        Keep this page&apos;s link to check again later. Anyone with the link can see this page, but
        it shows nothing about you or the donors.
      </p>
      <Link href="/find-blood" className="text-sm font-medium text-primary hover:underline">
        Ask another hospital
      </Link>
    </div>
  );
}

export default function FamilyRequestPage() {
  const router = useRouter();
  const id = router.isReady && typeof router.query.id === "string" ? router.query.id : null;

  return (
    <>
      <Head>
        <title>Your request for blood | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container size="reading">
          {id ? <Tracking id={id} /> : <Skeleton className="h-64" />}
        </Container>
      </Section>
    </>
  );
}
