/**
 * What NIPOST records about a hospital's building, beside what the hospital registered.
 *
 * An administrator compares the two before verifying: a "hospital" whose postcode is a
 * residential building, or an address in another town, deserves a closer look before it
 * can alert donors. The detail shown depends on the lookup level NIPOST has granted
 * BloodLink; the card says which level answered, so a missing field is never mistaken for a
 * problem with the hospital.
 */

import { CircleCheck, CircleX } from "lucide-react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useResource } from "@/lib/use-resource";
import type { PostcodeRecord } from "@/types/api";

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
      <dd className="text-sm text-ink">{value ?? "Not available at this level"}</dd>
    </div>
  );
}

function SourceNote({ record }: { record: PostcodeRecord }) {
  const source =
    record.source === "mock"
      ? "sample data"
      : record.source === "test"
        ? "the NIPOST sandbox"
        : "NIPOST";
  return (
    <p className="text-xs text-ink-muted">
      Answered by {source} at lookup level {record.level}.
    </p>
  );
}

export function PostcodeRecordCard({
  hospitalId,
  postcode,
}: {
  hospitalId: string;
  postcode: string | null;
}) {
  const record = useResource<PostcodeRecord>(
    postcode ? `/admin/hospitals/${hospitalId}/postcode-record` : null,
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>NIPOST record</CardTitle>
        <CardDescription>
          What NIPOST holds for the building at this hospital&apos;s postcode.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!postcode ? (
          <p className="text-sm text-ink-muted">
            This hospital gave no postcode, so there is nothing to compare. Ask for one before
            verifying.
          </p>
        ) : !record.loaded ? (
          <Skeleton className="h-32" />
        ) : record.error || !record.data ? (
          <p className="text-sm text-danger">
            {record.error?.message ?? "The NIPOST record could not be loaded."}
          </p>
        ) : (
          <>
            {record.data.valid ? (
              <p className="flex items-center gap-1.5 text-sm font-medium text-success">
                <CircleCheck className="size-4" aria-hidden="true" />
                {record.data.postcode} is assigned by NIPOST
              </p>
            ) : (
              <p className="flex items-center gap-1.5 text-sm font-medium text-danger">
                <CircleX className="size-4" aria-hidden="true" />
                NIPOST has no building with the postcode {record.data.postcode}
              </p>
            )}
            {record.data.valid ? (
              <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <Row label="LGA" value={record.data.lga_name} />
                <Row label="State" value={record.data.state_name} />
                <Row label="Locality" value={record.data.locality_name} />
                <Row label="Building use" value={record.data.building_use_status} />
                <div className="sm:col-span-2">
                  <Row label="Address on record" value={record.data.house_address} />
                </div>
              </dl>
            ) : null}
            <SourceNote record={record.data} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
