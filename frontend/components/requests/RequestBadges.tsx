/**
 * Small pills showing a blood request's state, how urgent it is, and where a pledge stands.
 *
 * Each value has its own colour, icon and wording, so the meaning never depends on colour
 * alone.
 */

import {
  CircleCheck,
  CircleSlash,
  Clock,
  Flame,
  HeartHandshake,
  Hourglass,
  Siren,
  TimerOff,
  UserX,
} from "lucide-react";
import type { ReactNode } from "react";

import type { PledgeStatus, RequestStatus, RequestUrgency } from "@/types/api";

interface PillStyle {
  label: string;
  tone: string;
  icon: ReactNode;
}

function Pill({ style }: { style: PillStyle }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${style.tone}`}
    >
      {style.icon}
      {style.label}
    </span>
  );
}

const statusStyles: Record<RequestStatus, PillStyle> = {
  open: {
    label: "Open",
    tone: "bg-primary-50 text-primary-700",
    icon: <Hourglass className="size-4" aria-hidden="true" />,
  },
  fulfilled: {
    label: "Fulfilled",
    tone: "bg-trust-50 text-trust-700",
    icon: <CircleCheck className="size-4" aria-hidden="true" />,
  },
  closed: {
    label: "Closed",
    tone: "bg-secondary text-ink",
    icon: <CircleSlash className="size-4" aria-hidden="true" />,
  },
  expired: {
    label: "Expired",
    tone: "bg-secondary text-ink-muted",
    icon: <TimerOff className="size-4" aria-hidden="true" />,
  },
};

const urgencyStyles: Record<RequestUrgency, PillStyle> = {
  critical: {
    label: "Critical",
    tone: "bg-primary-600 text-white",
    icon: <Siren className="size-4" aria-hidden="true" />,
  },
  urgent: {
    label: "Urgent",
    tone: "bg-primary-100 text-primary-900",
    icon: <Flame className="size-4" aria-hidden="true" />,
  },
  routine: {
    label: "Routine",
    tone: "bg-secondary text-ink",
    icon: <Clock className="size-4" aria-hidden="true" />,
  },
};

/** Human-readable labels for each urgency, shared with the form. */
export const URGENCY_LABELS: Record<RequestUrgency, string> = {
  critical: urgencyStyles.critical.label,
  urgent: urgencyStyles.urgent.label,
  routine: urgencyStyles.routine.label,
};

export function RequestStatusBadge({ status }: { status: RequestStatus }) {
  return <Pill style={statusStyles[status]} />;
}

export function UrgencyBadge({ urgency }: { urgency: RequestUrgency }) {
  return <Pill style={urgencyStyles[urgency]} />;
}

const pledgeStyles: Record<PledgeStatus, PillStyle> = {
  pledged: {
    label: "Pledged",
    tone: "bg-primary-50 text-primary-700",
    icon: <HeartHandshake className="size-4" aria-hidden="true" />,
  },
  donated: {
    label: "Donated",
    tone: "bg-trust-50 text-trust-700",
    icon: <CircleCheck className="size-4" aria-hidden="true" />,
  },
  no_show: {
    label: "Did not attend",
    tone: "bg-secondary text-ink",
    icon: <UserX className="size-4" aria-hidden="true" />,
  },
  cancelled: {
    label: "Cancelled",
    tone: "bg-secondary text-ink-muted",
    icon: <CircleSlash className="size-4" aria-hidden="true" />,
  },
};

export function PledgeStatusBadge({ status }: { status: PledgeStatus }) {
  return <Pill style={pledgeStyles[status]} />;
}
