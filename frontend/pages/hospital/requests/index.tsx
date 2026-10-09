/**
 * The hospital's blood requests, newest first, filtered by state.
 *
 * Open requests are shown by default because they are the ones that need attention. The
 * server moves overdue requests to "expired" whenever the list is read, so the states shown
 * are always current without waiting for a scheduled job.
 */

import { ChevronLeft, ChevronRight, Inbox, Plus } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useState } from "react";

import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { RequestSummaryCard } from "@/components/requests/RequestSummaryCard";
import { RouteGuard } from "@/components/RouteGuard";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { RequestPage, RequestStatus } from "@/types/api";

const PAGE_SIZE = 10;

type Filter = RequestStatus | "all";

const TABS: { value: Filter; label: string; empty: string }[] = [
  { value: "open", label: "Open", empty: "You have no open requests." },
  { value: "fulfilled", label: "Fulfilled", empty: "No requests have been fulfilled yet." },
  { value: "expired", label: "Expired", empty: "No requests have expired." },
  { value: "closed", label: "Closed", empty: "You have not closed any requests." },
  { value: "all", label: "All", empty: "You have not raised any requests yet." },
];

function FilterTabs({ active, onChange }: { active: Filter; onChange: (value: Filter) => void }) {
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

function RequestsContent() {
  const [filter, setFilter] = useState<Filter>("open");
  const [offset, setOffset] = useState(0);
  const statusQuery = filter === "all" ? "" : `&status=${filter}`;
  const page = useResource<RequestPage>(
    `/requests?limit=${PAGE_SIZE}&offset=${offset}${statusQuery}`,
  );

  function changeFilter(next: Filter) {
    setFilter(next);
    setOffset(0);
  }

  const tab = TABS.find((entry) => entry.value === filter) ?? TABS[0];

  return (
    <div className="space-y-8">
      <Reveal className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title font-semibold text-ink">Blood requests</h1>
          <p className="mt-2 max-w-2xl text-ink-muted">
            Every request your hospital has raised. Open one to see the donors who can answer
            it.
          </p>
        </div>
        <Link href="/hospital/requests/new" className={buttonVariants({ size: "lg" })}>
          <Plus /> New request
        </Link>
      </Reveal>

      <FilterTabs active={filter} onChange={changeFilter} />

      {!page.loaded ? (
        <div className="space-y-4" role="status" aria-label="Loading requests">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      ) : page.error || !page.data ? (
        <LoadError
          message="We could not load your requests. Check your connection and try again."
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
            {page.data.items.map((request) => (
              <li key={request.id}>
                <RequestSummaryCard request={request} />
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

export default function HospitalRequestsPage() {
  return (
    <>
      <Head>
        <title>Blood requests | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container>
          <RouteGuard allow={["hospital_staff"]}>
            <RequestsContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
