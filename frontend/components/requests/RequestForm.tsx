/**
 * The form hospital staff use to raise a blood request.
 *
 * The blood components on offer are loaded from the API, which reads them from the
 * database, so a component added or retired there appears here without a code change.
 *
 * The deadline is picked in the browser's local time and sent as an exact UTC moment, so
 * the server and every donor read the same instant. Quick choices ("in 2 hours", "in 24
 * hours") cover the common emergency cases without fiddling with a date picker.
 *
 * The checks here mirror the server's rules only to give instant feedback; the server
 * remains the authority and its messages are shown next to the matching fields.
 */

import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";
import type { FormEvent } from "react";

import { FormField } from "@/components/auth/FormField";
import { ChoiceCards } from "@/components/form/ChoiceCards";
import type { ChoiceOption } from "@/components/form/ChoiceCards";
import { SelectField } from "@/components/form/SelectField";
import { TextareaField } from "@/components/form/TextareaField";
import { LoadError } from "@/components/layout/LoadError";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError, api } from "@/lib/api";
import { toLocalInputValue } from "@/lib/format";
import { failureFromError, focusFirstInvalid } from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { useResource } from "@/lib/use-resource";
import { BLOOD_GROUPS } from "@/types/api";
import type { BloodComponent, BloodGroup, BloodRequest, RequestUrgency } from "@/types/api";

// The same limits the server applies.
const MAX_UNITS = 20;
const MIN_DEADLINE_MINUTES = 5;
const MAX_DEADLINE_DAYS = 30;
const MAX_NOTES_LENGTH = 1000;

const FIELD_ORDER = [
  "recipient_group",
  "component_code",
  "units_needed",
  "urgency",
  "deadline",
  "notes",
];

const URGENCY_OPTIONS: ChoiceOption<RequestUrgency>[] = [
  { value: "critical", title: "Critical", description: "A life is at risk in the next few hours." },
  { value: "urgent", title: "Urgent", description: "Needed today or tonight." },
  { value: "routine", title: "Routine", description: "Planned care, such as a scheduled surgery." },
];

/** Quick deadline choices, in hours from now. */
const DEADLINE_PRESETS = [2, 6, 12, 24, 72];

interface FormState {
  recipientGroup: BloodGroup | "";
  componentCode: string;
  units: string;
  urgency: RequestUrgency | "";
  /** Local date and time in the "YYYY-MM-DDTHH:mm" form of a datetime-local input. */
  deadline: string;
  notes: string;
}

const EMPTY_FORM: FormState = {
  recipientGroup: "",
  componentCode: "whole_blood",
  units: "1",
  urgency: "",
  deadline: "",
  notes: "",
};

function hoursFromNow(hours: number): Date {
  return new Date(Date.now() + hours * 3_600_000);
}

function presetLabel(hours: number): string {
  return hours < 48 ? `In ${hours} hours` : `In ${hours / 24} days`;
}

function validate(form: FormState): FieldErrors {
  const problems: FieldErrors = {};
  if (!form.recipientGroup) problems.recipient_group = "Choose the patient's blood group.";
  if (!form.componentCode) problems.component_code = "Choose what is needed.";

  const units = Number(form.units);
  if (!Number.isInteger(units) || units < 1 || units > MAX_UNITS) {
    problems.units_needed = `Enter a whole number of units from 1 to ${MAX_UNITS}.`;
  }

  if (!form.urgency) problems.urgency = "Choose how urgent this is.";

  if (!form.deadline) {
    problems.deadline = "Choose when the blood is needed by.";
  } else {
    const deadline = new Date(form.deadline).getTime();
    const now = Date.now();
    if (Number.isNaN(deadline)) {
      problems.deadline = "Enter a valid date and time.";
    } else if (deadline <= now + MIN_DEADLINE_MINUTES * 60_000) {
      problems.deadline = `The deadline must be at least ${MIN_DEADLINE_MINUTES} minutes from now.`;
    } else if (deadline > now + MAX_DEADLINE_DAYS * 86_400_000) {
      problems.deadline = `The deadline cannot be more than ${MAX_DEADLINE_DAYS} days away.`;
    }
  }

  if (form.notes.length > MAX_NOTES_LENGTH) {
    problems.notes = `Keep notes to ${MAX_NOTES_LENGTH} characters or fewer.`;
  }
  return problems;
}

function FormSkeleton() {
  return (
    <div className="space-y-6" role="status" aria-label="Loading the form">
      <Skeleton className="h-12" />
      <Skeleton className="h-28" />
      <Skeleton className="h-40" />
    </div>
  );
}

export function RequestForm() {
  const router = useRouter();
  const components = useResource<BloodComponent[]>("/components");
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // Bounds for the date picker, fixed when the form opens so rendering stays pure. They
  // only guide the picker; the check on submit uses the current time and is the precise one.
  const [deadlineBounds] = useState(() => ({
    min: toLocalInputValue(hoursFromNow(MIN_DEADLINE_MINUTES / 60)),
    max: toLocalInputValue(hoursFromNow(MAX_DEADLINE_DAYS * 24)),
  }));

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const problems = validate(form);
    if (Object.keys(problems).length > 0) {
      setErrors(problems);
      setGeneralError(null);
      focusFirstInvalid(problems, FIELD_ORDER);
      return;
    }

    setErrors({});
    setGeneralError(null);
    setSubmitting(true);

    try {
      const created = await api.post<BloodRequest>("/requests", {
        recipient_group: form.recipientGroup,
        component_code: form.componentCode,
        units_needed: Number(form.units),
        urgency: form.urgency,
        // The input holds local time; toISOString gives the same instant in UTC.
        deadline: new Date(form.deadline).toISOString(),
        notes: form.notes.trim() || null,
      });
      await router.push(`/hospital/requests/${created.id}`);
    } catch (error) {
      setSubmitting(false);
      // A conflict here means the hospital is at its limit of open requests, and a refusal
      // means it is not verified: neither belongs to a single field.
      if (error instanceof ApiError && (error.status === 409 || error.status === 403)) {
        setGeneralError(error.message);
        return;
      }
      const failure = failureFromError(error);
      setErrors(failure.fields);
      setGeneralError(failure.general);
      focusFirstInvalid(failure.fields, FIELD_ORDER);
    }
  }

  if (!components.loaded) return <FormSkeleton />;
  if (components.error || !components.data) {
    return (
      <LoadError
        message="We could not load the form. Check your connection and try again."
        onRetry={components.reload}
      />
    );
  }

  const componentOptions: ChoiceOption<string>[] = components.data.map((component) => ({
    value: component.code,
    title: component.name,
  }));

  const { min: minDeadline, max: maxDeadline } = deadlineBounds;

  return (
    <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-10">
      {generalError ? (
        <div
          role="alert"
          className="flex items-start gap-2.5 rounded-xl bg-primary-50 p-4 text-sm text-primary-900"
        >
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>{generalError}</span>
        </div>
      ) : null}

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">What is needed</h2>

        <SelectField
          id="recipient_group"
          name="recipient_group"
          label="Patient's blood group"
          hint="Donors with a compatible group are found from the compatibility chart."
          value={form.recipientGroup}
          onChange={(event) => update("recipientGroup", event.target.value as BloodGroup)}
          error={errors.recipient_group}
        >
          <option value="" disabled>
            Choose a blood group
          </option>
          {BLOOD_GROUPS.map((group) => (
            <option key={group} value={group}>
              {group}
            </option>
          ))}
        </SelectField>

        <ChoiceCards
          name="component_code"
          legend="Component"
          options={componentOptions}
          value={form.componentCode}
          onChange={(value) => update("componentCode", value)}
          error={errors.component_code}
        />

        <FormField
          id="units_needed"
          name="units_needed"
          label="Units needed"
          type="number"
          inputMode="numeric"
          min={1}
          max={MAX_UNITS}
          step={1}
          hint={`One donor gives one unit. Up to ${MAX_UNITS} per request.`}
          value={form.units}
          onChange={(event) => update("units", event.target.value)}
          error={errors.units_needed}
        />
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">How soon</h2>

        <ChoiceCards
          name="urgency"
          legend="Urgency"
          options={URGENCY_OPTIONS}
          value={form.urgency}
          onChange={(value) => update("urgency", value)}
          error={errors.urgency}
        />

        <div className="space-y-3">
          <FormField
            id="deadline"
            name="deadline"
            label="Needed by"
            type="datetime-local"
            min={minDeadline}
            max={maxDeadline}
            hint="Your local time. The request expires automatically after this moment."
            value={form.deadline}
            onChange={(event) => update("deadline", event.target.value)}
            error={errors.deadline}
          />
          <div role="group" aria-label="Quick deadline choices" className="flex flex-wrap gap-2">
            {DEADLINE_PRESETS.map((hours) => (
              <Button
                key={hours}
                type="button"
                variant="secondary"
                size="xs"
                onClick={() => update("deadline", toLocalInputValue(hoursFromNow(hours)))}
              >
                {presetLabel(hours)}
              </Button>
            ))}
          </div>
        </div>
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">For donors</h2>
        <TextareaField
          id="notes"
          name="notes"
          label="Notes (optional)"
          hint="For example, the ward or the desk to report to. Do not include patient details."
          maxLength={MAX_NOTES_LENGTH}
          value={form.notes}
          onChange={(event) => update("notes", event.target.value)}
          error={errors.notes}
        />
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? "Raising request..." : "Raise request"}
        </Button>
        <Link href="/hospital/requests" className={buttonVariants({ variant: "ghost", size: "lg" })}>
          Cancel
        </Link>
      </div>
    </form>
  );
}
