/**
 * Administrator dashboard: the hospital review queue.
 *
 * Shows hospitals by verification state (waiting for review by default), oldest first, so
 * the one that has waited longest is at the top. Each entry opens its own review page. Data
 * loads only after the route guard has confirmed the visitor is an administrator.
 */

import { ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useState } from "react";

import { VerificationBadge } from "@/components/hospital/VerificationBadge";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { RouteGuard } from "@/components/RouteGuard";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatTimestamp } from "@/lib/format";
import { useResource } from "@/lib/use-resource";
import type { HospitalPage, VerificationStatus } from "@/types/api";

const PAGE_SIZE = 10;

const TABS: { value: VerificationStatus; label: string; empty: string }[] = [
  { value: "pending", label: "Waiting for review", empty: "No hospitals are waiting for review." },
  { value: "verified", label: "Verified", empty: "No hospitals have been verified yet." },
  { value: "rejected", label: "Changes needed", empty: "No hospitals are waiting on corrections." },
];

function StatusTabs({
  active,
  onChange,
}: {
  active: VerificationStatus;
  onChange: (status: VerificationStatus) => void;
}) {
  return (
    <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-2">
      {TABS.map((tab) => (
        <button
          key={tab.value}
          type="button"
          aria-pressed={active === tab.value}
          onClick={() => onChange(tab.value)}
          className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background ${
            active === tab.value
              ? "border-ink bg-ink text-background"
              : "border-input bg-surface text-ink hover:bg-muted"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function QueueSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="Loading hospitals">
      <Skeleton className="h-24" />
      <Skeleton className="h-24" />
      <Skeleton className="h-24" />
    </div>
  );
}

function QueueContent() {
  const [status, setStatus] = useState<VerificationStatus>("pending");
  const [offset, setOffset] = useState(0);
  const page = useResource<HospitalPage>(
    `/admin/hospitals?status=${status}&limit=${PAGE_SIZE}&offset=${offset}`,
  );

  function changeStatus(next: VerificationStatus) {
    setStatus(next);
    setOffset(0);
  }

  const tab = TABS.find((entry) => entry.value === status) ?? TABS[0];

  return (
    <div className="space-y-8">
      <Reveal>
        <h1 className="text-title font-semibold text-ink">Hospital verification</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Check each hospital before it can send blood requests to donors. Open an entry to see
          its details and the people who registered it.
        </p>
      </Reveal>

      <StatusTabs active={status} onChange={changeStatus} />

      {!page.loaded ? (
        <QueueSkeleton />
      ) : page.error || !page.data ? (
        <LoadError
          message="We could not load the hospitals. Check your connection and try again."
          onRetry={page.reload}
        />
      ) : page.data.items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-14 text-center">
          <Inbox className="size-8 text-ink-muted" aria-hidden="true" />
          <p className="text-ink">{tab.empty}</p>
        </div>
      ) : (
        <>
          <ul className="space-y-4">
            {page.data.items.map((hospital) => (
              <li key={hospital.id}>
                <Card>
                  <CardContent className="flex flex-wrap items-center justify-between gap-4">
                    <div className="min-w-0 space-y-1">
                      <p className="font-heading text-lg font-semibold text-ink">{hospital.name}</p>
                      <p className="text-sm text-ink-muted">
                        {hospital.city}, {hospital.state} &middot; registered{" "}
                        {formatTimestamp(hospital.created_at)}
                      </p>
                      <p className="text-sm text-ink-muted">
                        By{" "}
                        {hospital.staff.length > 0
                          ? hospital.staff.map((member) => member.full_name).join(", ")
                          : "unknown"}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <VerificationBadge status={hospital.verification_status} />
                      <Link
                        href={`/admin/hospitals/${hospital.id}`}
                        className={buttonVariants({ variant: "outline", size: "sm" })}
                      >
                        Review
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>

          <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm text-ink-muted">
              Showing {offset + 1} to {Math.min(offset + PAGE_SIZE, page.data.total)} of{" "}
              {page.data.total}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
              >
                <ChevronLeft /> Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={offset + PAGE_SIZE >= page.data.total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
              >
                Next <ChevronRight />
              </Button>
            </div>
          </nav>
        </>
      )}
    </div>
  );
}

export default function AdminDashboardPage() {
  return (
    <>
      <Head>
        <title>Hospital verification | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["admin"]}>
            <QueueContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
