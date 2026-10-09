/**
 * Raise a new blood request.
 *
 * Only a verified hospital can raise requests, so the page loads the staff member's
 * hospital first and explains what to do when it is missing or still under review, instead
 * of showing a form the server would refuse.
 */

import { ArrowLeft } from "lucide-react";
import Head from "next/head";
import Link from "next/link";

import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { RequestForm } from "@/components/requests/RequestForm";
import { RouteGuard } from "@/components/RouteGuard";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { Hospital } from "@/types/api";

function NotReady({ title, message }: { title: string; message: string }) {
  return (
    <div className="space-y-5">
      <h1 className="text-title font-semibold text-ink">{title}</h1>
      <p className="text-ink-muted">{message}</p>
      <Link href="/hospital" className={buttonVariants({ variant: "outline" })}>
        Back to your hospital
      </Link>
    </div>
  );
}

function NewRequestContent() {
  const hospital = useResource<Hospital>("/hospitals/me");

  if (!hospital.loaded) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading your hospital">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (hospital.error?.status === 404) {
    return (
      <NotReady
        title="Register your hospital first"
        message="Requests are sent on behalf of a verified hospital. Register yours, and you can raise requests once an administrator has verified it."
      />
    );
  }

  if (hospital.error || !hospital.data) {
    return (
      <LoadError
        message="We could not load your hospital. Check your connection and try again."
        onRetry={hospital.reload}
      />
    );
  }

  if (hospital.data.verification_status !== "verified") {
    return (
      <NotReady
        title="Your hospital is not verified yet"
        message="Only verified hospitals can send requests to donors, so every alert they receive is trustworthy. You can raise requests as soon as an administrator verifies yours."
      />
    );
  }

  return (
    <div className="space-y-8">
      <Link href="/hospital/requests" className={buttonVariants({ variant: "arrow" })}>
        <ArrowLeft className="!translate-x-0" /> All requests
      </Link>
      <div>
        <h1 className="text-title font-semibold text-ink">Request blood</h1>
        <p className="mt-2 text-ink-muted">
          BloodLink finds compatible, eligible donors near {hospital.data.name}, nearest first.
        </p>
      </div>
      <RequestForm />
    </div>
  );
}

export default function NewRequestPage() {
  return (
    <>
      <Head>
        <title>Request blood | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container size="reading">
          <RouteGuard allow={["hospital_staff"]}>
            <NewRequestContent />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
