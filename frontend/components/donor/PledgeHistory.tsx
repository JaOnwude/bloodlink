/**
 * The donor's pledges and donations, most recent first.
 *
 * Each entry shows the hospital, what was asked for and how it ended. A pledge that is still
 * waiting shows where to go and whom to call, and can be cancelled from here as well as from
 * the request card.
 */

import { History } from "lucide-react";

import { HospitalContact } from "@/components/donor/HospitalContact";
import { ConfirmAction } from "@/components/form/ConfirmAction";
import { PledgeStatusBadge } from "@/components/requests/RequestBadges";
import { api } from "@/lib/api";
import { formatDateTime, withArticle } from "@/lib/format";
import type { DonorPledge } from "@/types/api";

interface PledgeHistoryProps {
  pledges: DonorPledge[];
  total: number;
  onChanged: () => void;
}

function outcomeText(pledge: DonorPledge): string {
  switch (pledge.status) {
    case "donated":
      return `You donated on ${formatDateTime(pledge.resolved_at ?? pledge.pledged_at)}. Thank you.`;
    case "no_show":
      return "The hospital recorded that you did not attend.";
    case "cancelled":
      return "You cancelled this pledge.";
    case "standby":
      return "You are on standby. If a pledged donor cannot give, you will be texted and asked to come.";
    case "released":
      return "Every unit was covered, so you were not needed this time. Thank you for standing by.";
    case "deferred":
      // The server's message is written for the donor and never reveals the reason itself.
      return pledge.outcome_message ?? "The hospital could not take your donation this time.";
    default:
      return `Pledged on ${formatDateTime(pledge.pledged_at)}. Go before ${formatDateTime(pledge.request.deadline)}.`;
  }
}

export function PledgeHistory({ pledges, total, onChanged }: PledgeHistoryProps) {
  if (pledges.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-3xl border border-dashed border-input bg-surface px-6 py-10 text-center">
        <History className="size-8 text-ink-muted" aria-hidden="true" />
        <p className="text-ink">Your pledges and donations will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">
        {pledges.map((pledge) => (
          <li key={pledge.id} className="space-y-3 px-5 py-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-ink">{pledge.hospital.name}</p>
              <PledgeStatusBadge status={pledge.status} />
            </div>
            <p className="text-sm text-ink-muted">
              {pledge.request.component_name} for {withArticle(pledge.request.recipient_group)} patient
            </p>
            <p className="text-sm text-ink">{outcomeText(pledge)}</p>
            {pledge.status === "deferred" ? <HospitalContact hospital={pledge.hospital} /> : null}
            {pledge.status === "pledged" || pledge.status === "standby" ? (
              <>
                <HospitalContact hospital={pledge.hospital} />
                <ConfirmAction
                  label={pledge.status === "standby" ? "Step down from standby" : "Cancel my pledge"}
                  variant="ghost"
                  title={pledge.status === "standby" ? "Step down from standby?" : "Cancel your pledge?"}
                  description={
                    pledge.status === "standby"
                      ? "Your standby place goes back to other donors."
                      : "The hospital will be told you are no longer coming, and your unit goes to a standby donor or back to other donors."
                  }
                  confirmLabel={pledge.status === "standby" ? "Yes, step down" : "Yes, cancel it"}
                  workingLabel="Cancelling..."
                  confirmVariant="destructive"
                  cancelLabel={pledge.status === "standby" ? "Stay on standby" : "Keep my pledge"}
                  onConfirm={async () => {
                    await api.delete(`/pledges/${pledge.id}`);
                    onChanged();
                  }}
                />
              </>
            ) : null}
          </li>
        ))}
      </ul>
      {total > pledges.length ? (
        <p className="text-sm text-ink-muted">
          Showing your {pledges.length} most recent of {total}.
        </p>
      ) : null}
    </div>
  );
}
