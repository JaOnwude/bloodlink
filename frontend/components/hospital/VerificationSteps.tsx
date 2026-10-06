/**
 * A three-step progress list: registered, reviewed, verified.
 *
 * The current step is marked for assistive technology with `aria-current="step"`. A
 * rejected hospital stops at the review step, which is relabelled "Changes needed".
 */

import { Check, CircleAlert } from "lucide-react";

import type { VerificationStatus } from "@/types/api";

type StepState = "done" | "current" | "attention" | "upcoming";

interface Step {
  label: string;
  state: StepState;
}

function stepsFor(status: VerificationStatus): Step[] {
  switch (status) {
    case "verified":
      return [
        { label: "Registered", state: "done" },
        { label: "Reviewed by an administrator", state: "done" },
        { label: "Verified", state: "done" },
      ];
    case "rejected":
      return [
        { label: "Registered", state: "done" },
        { label: "Changes needed", state: "attention" },
        { label: "Verified", state: "upcoming" },
      ];
    default:
      return [
        { label: "Registered", state: "done" },
        { label: "Under review", state: "current" },
        { label: "Verified", state: "upcoming" },
      ];
  }
}

const markers: Record<StepState, string> = {
  done: "bg-trust-600 text-white",
  current: "bg-primary-600 text-white",
  attention: "bg-warning text-white",
  upcoming: "border border-input bg-surface text-ink-muted",
};

export function VerificationSteps({ status }: { status: VerificationStatus }) {
  const steps = stepsFor(status);

  return (
    <ol className="space-y-4">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className="flex items-center gap-3"
          aria-current={step.state === "current" || step.state === "attention" ? "step" : undefined}
        >
          <span
            className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${markers[step.state]}`}
          >
            {step.state === "done" ? (
              <Check className="size-4" aria-hidden="true" />
            ) : step.state === "attention" ? (
              <CircleAlert className="size-4" aria-hidden="true" />
            ) : (
              index + 1
            )}
          </span>
          <span
            className={
              step.state === "upcoming" ? "text-ink-muted" : "font-medium text-ink"
            }
          >
            {step.label}
          </span>
        </li>
      ))}
    </ol>
  );
}
