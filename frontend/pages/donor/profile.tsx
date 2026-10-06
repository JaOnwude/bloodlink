/**
 * Create or edit the donor profile.
 *
 * Loads the existing profile first. If there is none (the API answers 404) the form opens
 * empty; otherwise it opens filled in.
 */

import Head from "next/head";

import { DonorProfileForm } from "@/components/donor/DonorProfileForm";
import { Container } from "@/components/layout/Container";
import { LoadError } from "@/components/layout/LoadError";
import { Section } from "@/components/layout/Section";
import { RouteGuard } from "@/components/RouteGuard";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { DonorProfile } from "@/types/api";

function ProfileEditor() {
  const profile = useResource<DonorProfile>("/donors/me");

  if (!profile.loaded) {
    return (
      <div className="space-y-6" role="status" aria-label="Loading your profile">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (profile.error && profile.error.status !== 404) {
    return (
      <LoadError
        message="We could not load your profile. Check your connection and try again."
        onRetry={profile.reload}
      />
    );
  }

  const existing = profile.data;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-title font-semibold text-ink">
          {existing ? "Edit your profile" : "Create your donor profile"}
        </h1>
        <p className="mt-2 text-ink-muted">
          Only you can see these details until you pledge to a request.
        </p>
      </div>
      <DonorProfileForm initial={existing} />
    </div>
  );
}

export default function DonorProfilePage() {
  return (
    <>
      <Head>
        <title>Donor profile | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>
      <Section>
        <Container size="reading">
          <RouteGuard allow={["donor"]}>
            <ProfileEditor />
          </RouteGuard>
        </Container>
      </Section>
    </>
  );
}
