/**
 * The appeal a family sends to the hospital their patient is in.
 *
 * It asks for what a doctor writes on the slip (blood group, what is needed, how many
 * units) and the ward or lab reference, so staff can find the patient. Nobody is alerted
 * when it is sent: the hospital confirms the patient first, then BloodLink alerts donors.
 * The family's name and phone number go only to that hospital, so it can call back.
 */

import { CircleAlert, ShieldCheck } from "lucide-react";
import { useRouter } from "next/router";
import { useState } from "react";
import type { FormEvent } from "react";

import { FormField } from "@/components/auth/FormField";
import { CheckboxField } from "@/components/form/CheckboxField";
import { SelectField } from "@/components/form/SelectField";
import { TextareaField } from "@/components/form/TextareaField";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { failureFromError, focusFirstInvalid } from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { useResource } from "@/lib/use-resource";
import { BLOOD_GROUPS } from "@/types/api";
import type { BloodComponent, FamilyRequestCreated, PublicHospital } from "@/types/api";

const FIELD_ORDER = [
  "requester_name",
  "requester_phone",
  "recipient_group",
  "component_code",
  "units_needed",
  "ward_reference",
  "patient_is_admitted",
];

// Same shape the server accepts: optional plus sign, then 7 to 15 digits.
const PHONE_PATTERN = /^\+?\d{7,15}$/;

/** Most units a family can ask for; larger needs are raised by the hospital itself. */
const MAX_UNITS = 10;

interface FormState {
  name: string;
  phone: string;
  group: string;
  component: string;
  units: string;
  ward: string;
  notes: string;
  admitted: boolean;
}

const EMPTY: FormState = {
  name: "",
  phone: "",
  group: "",
  component: "whole_blood",
  units: "1",
  ward: "",
  notes: "",
  admitted: false,
};

function validate(form: FormState): FieldErrors {
  const problems: FieldErrors = {};
  if (form.name.trim().length < 2) problems.requester_name = "Enter your name.";
  if (!PHONE_PATTERN.test(form.phone.replace(/[\s\-().]/g, ""))) {
    problems.requester_phone = "Enter a phone number the hospital can call, like 08031234567.";
  }
  if (!form.group) problems.recipient_group = "Choose the patient's blood group.";
  const units = Number(form.units);
  if (!Number.isInteger(units) || units < 1 || units > MAX_UNITS) {
    problems.units_needed = `Enter a number of units from 1 to ${MAX_UNITS}.`;
  }
  if (form.ward.trim().length < 2) {
    problems.ward_reference = "Enter the ward, bed or lab slip number.";
  }
  if (!form.admitted) {
    problems.patient_is_admitted = "Confirm the patient is admitted at this hospital.";
  }
  return problems;
}

export function FamilyRequestForm({
  hospital,
  onBack,
}: {
  hospital: PublicHospital;
  onBack: () => void;
}) {
  const router = useRouter();
  const components = useResource<BloodComponent[]>("/components");
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;
    const problems = validate(form);
    if (Object.keys(problems).length > 0) {
      setErrors(problems);
      focusFirstInvalid(problems, FIELD_ORDER);
      return;
    }
    setErrors({});
    setGeneralError(null);
    setSubmitting(true);
    try {
      const created = await api.post<FamilyRequestCreated>(
        `/public/hospitals/${hospital.id}/family-requests`,
        {
          requester_name: form.name.trim(),
          requester_phone: form.phone.trim(),
          recipient_group: form.group,
          component_code: form.component,
          units_needed: Number(form.units),
          ward_reference: form.ward.trim(),
          notes: form.notes.trim() || null,
          patient_is_admitted: form.admitted,
        },
      );
      await router.push(`/find-blood/${created.id}`);
    } catch (error) {
      const failure = failureFromError(error);
      setErrors(failure.fields);
      setGeneralError(failure.general);
      setSubmitting(false);
      focusFirstInvalid(failure.fields, FIELD_ORDER);
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-8">
      <div className="space-y-2 rounded-2xl border border-border bg-surface p-4">
        <p className="text-sm text-ink-muted">Asking</p>
        <p className="font-heading text-lg font-semibold text-ink">{hospital.name}</p>
        <p className="text-sm text-ink-muted">
          {hospital.address}, {hospital.city}
          {hospital.postcode ? ` · ${hospital.postcode}` : ""}
        </p>
        <Button type="button" variant="ghost" size="sm" onClick={onBack}>
          Choose another hospital
        </Button>
      </div>

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
        <h2 className="text-heading font-semibold text-ink">What the doctor asked for</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          <SelectField
            id="recipient_group"
            label="Patient's blood group"
            value={form.group}
            onChange={(event) => update("group", event.target.value)}
            error={errors.recipient_group}
          >
            <option value="">Select the blood group</option>
            {BLOOD_GROUPS.map((group) => (
              <option key={group} value={group}>
                {group}
              </option>
            ))}
          </SelectField>
          <SelectField
            id="component_code"
            label="What is needed"
            value={form.component}
            onChange={(event) => update("component", event.target.value)}
            error={errors.component_code}
          >
            {(components.data ?? [{ code: "whole_blood", name: "Whole blood" }]).map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </SelectField>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            id="units_needed"
            label="Units (pints)"
            type="number"
            inputMode="numeric"
            min={1}
            max={MAX_UNITS}
            value={form.units}
            onChange={(event) => update("units", event.target.value)}
            error={errors.units_needed}
          />
          <FormField
            id="ward_reference"
            label="Ward, bed or lab slip number"
            hint="So the hospital can find the patient."
            value={form.ward}
            onChange={(event) => update("ward", event.target.value)}
            error={errors.ward_reference}
          />
        </div>
        <TextareaField
          id="notes"
          label="Anything else the hospital should know"
          rows={3}
          value={form.notes}
          onChange={(event) => update("notes", event.target.value)}
        />
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">How the hospital can reach you</h2>
        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            id="requester_name"
            label="Your name"
            autoComplete="name"
            value={form.name}
            onChange={(event) => update("name", event.target.value)}
            error={errors.requester_name}
          />
          <FormField
            id="requester_phone"
            label="Your phone number"
            type="tel"
            autoComplete="tel"
            hint="Only this hospital sees it. You will get a text when it answers."
            value={form.phone}
            onChange={(event) => update("phone", event.target.value)}
            error={errors.requester_phone}
          />
        </div>
        <div className="space-y-2">
          <CheckboxField
            id="patient_is_admitted"
            label="The patient is admitted at this hospital"
            description="The hospital checks this before any donor is alerted."
            checked={form.admitted}
            onChange={(event) => update("admitted", event.target.checked)}
          />
          {errors.patient_is_admitted ? (
            <p className="text-sm text-danger">{errors.patient_is_admitted}</p>
          ) : null}
        </div>
      </section>

      <p className="flex items-start gap-2 text-sm text-ink-muted">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-trust-600" aria-hidden="true" />
        <span>
          BloodLink alerts donors only after the hospital confirms your patient. This keeps donors
          safe from false appeals, so they keep answering real ones.
        </span>
      </p>

      <Button type="submit" size="lg" disabled={submitting}>
        {submitting ? "Sending..." : "Send to the hospital"}
      </Button>
    </form>
  );
}
