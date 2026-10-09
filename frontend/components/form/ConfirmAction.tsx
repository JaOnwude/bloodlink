/**
 * A button that asks for confirmation before doing something that matters.
 *
 * The first click opens a short panel that spells out the consequence; the action runs only
 * from the panel's confirm button. While it runs, both buttons are disabled so it cannot be
 * sent twice. A failure is shown in place, using the server's message when there is one, and
 * the panel stays open so the person can try again or back out.
 */

import { CircleAlert } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

type ButtonVariant = "default" | "outline" | "secondary" | "ghost" | "destructive";

interface ConfirmActionProps {
  /** Text of the button that opens the confirmation. */
  label: ReactNode;
  variant?: ButtonVariant;
  size?: "sm" | "default" | "lg";
  /** Short question at the top of the panel. */
  title: string;
  /** What will happen, in plain words. */
  description: ReactNode;
  confirmLabel: string;
  workingLabel: string;
  confirmVariant?: ButtonVariant;
  cancelLabel?: string;
  /** Runs the action. A rejected promise is shown as an error. */
  onConfirm: () => Promise<void>;
}

export function ConfirmAction({
  label,
  variant = "outline",
  size = "sm",
  title,
  description,
  confirmLabel,
  workingLabel,
  confirmVariant = "default",
  cancelLabel = "Not now",
  onConfirm,
}: ConfirmActionProps) {
  const [open, setOpen] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirm() {
    setWorking(true);
    setError(null);
    try {
      await onConfirm();
      // The caller usually reloads and replaces this component; if not, close the panel.
      setOpen(false);
    } catch (failure) {
      setError(
        failure instanceof ApiError ? failure.message : "Something went wrong. Please try again.",
      );
    } finally {
      setWorking(false);
    }
  }

  if (!open) {
    return (
      <Button variant={variant} size={size} onClick={() => setOpen(true)}>
        {label}
      </Button>
    );
  }

  return (
    <div className="space-y-3 rounded-2xl bg-secondary p-4 text-sm text-ink" role="group" aria-label={title}>
      <p className="font-medium">{title}</p>
      <div className="text-ink-muted">{description}</div>
      {error ? (
        <p role="alert" className="flex items-start gap-1.5 text-danger">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button variant={confirmVariant} size="sm" disabled={working} onClick={() => void confirm()}>
          {working ? workingLabel : confirmLabel}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          disabled={working}
          onClick={() => {
            setOpen(false);
            setError(null);
          }}
        >
          {cancelLabel}
        </Button>
      </div>
    </div>
  );
}
