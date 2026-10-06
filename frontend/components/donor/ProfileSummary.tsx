/**
 * A read-only summary of the donor's profile with a link to edit it.
 */

import Link from "next/link";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { formatDate } from "@/lib/format";
import type { DonorProfile } from "@/types/api";

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs tracking-wide text-ink-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

export function ProfileSummary({ profile }: { profile: DonorProfile }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Your profile</CardTitle>
        <CardDescription>Only you can see this, until you pledge to a request.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center gap-4">
          <div
            className="flex size-16 items-center justify-center rounded-2xl bg-primary-600 font-heading text-2xl font-semibold text-primary-foreground"
            aria-hidden="true"
          >
            {profile.blood_group}
          </div>
          <div>
            <p className="text-sm text-ink-muted">Blood group</p>
            <p className="font-heading text-lg font-semibold text-ink">{profile.blood_group}</p>
          </div>
        </div>

        <dl className="grid grid-cols-2 gap-4">
          <Detail label="City" value={profile.city} />
          <Detail label="Weight" value={`${profile.weight_kg} kg`} />
          <Detail
            label="Last donation"
            value={profile.last_donation_date ? formatDate(profile.last_donation_date) : "Not recorded"}
          />
          <Detail label="Contact" value={profile.consent_to_contact ? "Allowed" : "Not allowed"} />
        </dl>

        <Link href="/donor/profile" className={buttonVariants({ variant: "outline", size: "sm" })}>
          Edit profile
        </Link>
      </CardContent>
    </Card>
  );
}
