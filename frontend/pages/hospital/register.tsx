/**
 * Register a hospital, or correct its details.
 *
 * Loads the staff member's hospital first. With none (the API answers 404) the form opens
 * empty to register one; with one it opens filled in. A verified hospital cannot be edited
 * here, so the page explains that instead of showing a form.
 */

import Head from "next/head";
import Link from "next/link";

import { HospitalForm } from "@/components/hospital/HospitalForm";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { RouteGuard } from "@/components/RouteGuard";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { Hospital } from "@/types/api";

function Editor() {
  const hospital = useResource<Hospital>("/hospitals/me");

  if (!hospital.loaded) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading your hospital">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (hospital.error && hospital.error.status !== 404) {
    return (
      <LoadError
        message="We could not load your hospital. Check your connection and try again."
        onRetry={hospital.reload}
      />
    );
  }

  const existing = hospital.data;

  if (existing?.verification_status === "verified") {
    return (
      <div className="space-y-5">
        <h1 className="text-title font-semibold text-ink">Your hospital is verified</h1>
        <p className="text-ink-muted">
          The details of a verified hospital can only be changed by an administrator, because
          donors rely on them. Contact an administrator if something needs correcting.
        </p>
        <Link href="/hospital" className={buttonVariants({ variant: "outline" })}>
          Back to your hospital
        </Link>
      </div>
    );
  }

  const heading = !existing
    ? "Register your hospital"
    : existing.verification_status === "rejected"
      ? "Correct your details"
      : "Edit your hospital";
  const intro = !existing
    ? "An administrator will review these details before your hospital can send requests."
    : existing.verification_status === "rejected"
      ? "Update what the administrator asked for, then resubmit for review."
      : "You can correct these details while the review is in progress.";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-title font-semibold text-ink">{heading}</h1>
        <p className="mt-2 text-ink-muted">{intro}</p>
      </div>
      <HospitalForm initial={existing} />
    </div>
  );
}

export default function HospitalRegisterPage() {
  return (
    <>
      <Head>
        <title>Register your hospital | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container size="reading">
          <RouteGuard allow={["hospital_staff"]}>
            <Editor />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
