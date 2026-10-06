/**
 * A small pill showing a hospital's verification state.
 *
 * Each state has its own colour, icon and wording, so the meaning never depends on colour
 * alone.
 */

import { CircleAlert, Clock, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import type { VerificationStatus } from "@/types/api";

const styles: Record<VerificationStatus, { label: string; tone: string; icon: ReactNode }> = {
  pending: {
    label: "Pending review",
    tone: "bg-primary-50 text-primary-700",
    icon: <Clock className="size-4" aria-hidden="true" />,
  },
  verified: {
    label: "Verified",
    tone: "bg-trust-50 text-trust-700",
    icon: <ShieldCheck className="size-4" aria-hidden="true" />,
  },
  rejected: {
    label: "Changes needed",
    tone: "bg-secondary text-ink",
    icon: <CircleAlert className="size-4" aria-hidden="true" />,
  },
};

export function VerificationBadge({ status }: { status: VerificationStatus }) {
  const style = styles[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${style.tone}`}
    >
      {style.icon}
      {style.label}
    </span>
  );
}
