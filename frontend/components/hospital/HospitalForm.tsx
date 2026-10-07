/**
 * The form hospital staff use to register their facility, or to correct its details.
 *
 * With no existing hospital it creates one; with an existing one it replaces its details. A
 * rejected hospital that is saved goes back to review, which the server handles.
 *
 * The state is not asked for: it follows from the chosen city.
 */

import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";
import type { FormEvent } from "react";

import { FormField } from "@/components/auth/FormField";
import { LocationPicker } from "@/components/form/LocationPicker";
import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { failureFromError, focusFirstInvalid } from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { findCity } from "@/lib/locations";
import type { Coordinates } from "@/lib/locations";
import type { Hospital } from "@/types/api";

interface FormState {
  name: string;
  address: string;
  registrationNumber: string;
  phone: string;
  city: string;
  /** Device location, when used instead of the centre of the city. */
  precise: Coordinates | null;
}

const FIELD_ORDER = ["name", "address", "registration_number", "contact_phone", "city"];

// Same shape the server accepts: optional plus sign, then 7 to 15 digits.
const PHONE_PATTERN = /^\+?\d{7,15}$/;

function initialState(initial: Hospital | null): FormState {
  if (!initial) {
    return { name: "", address: "", registrationNumber: "", phone: "", city: "", precise: null };
  }

  // Saved coordinates that are not the city centre mean the device location was used.
  const match = findCity(initial.city);
  const atCityCentre =
    match !== undefined &&
    Math.abs(match.latitude - initial.latitude) < 0.0005 &&
    Math.abs(match.longitude - initial.longitude) < 0.0005;

  return {
    name: initial.name,
    address: initial.address,
    registrationNumber: initial.registration_number ?? "",
    phone: initial.contact_phone,
    city: initial.city,
    precise: atCityCentre ? null : { latitude: initial.latitude, longitude: initial.longitude },
  };
}

function validate(form: FormState): FieldErrors {
  const problems: FieldErrors = {};
  if (form.name.trim().length < 2) problems.name = "Enter the name of the hospital.";
  if (form.address.trim().length < 5) problems.address = "Enter the street address.";
  if (!form.phone.trim()) {
    problems.contact_phone = "Enter a phone number.";
  } else if (!PHONE_PATTERN.test(form.phone.replace(/[\s\-().]/g, ""))) {
    problems.contact_phone = "Enter a valid phone number, for example +2348031234567.";
  }
  if (!form.city) problems.city = "Choose the city.";
  return problems;
}

export function HospitalForm({ initial }: { initial: Hospital | null }) {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(() => initialState(initial));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  // A city saved earlier that is not in the list stays available as a choice.
  const unlistedCity = initial && !findCity(initial.city) ? initial.city : null;
  const selectedCity = findCity(form.city);

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

    const coordinates: Coordinates | null =
      form.precise ??
      (selectedCity
        ? { latitude: selectedCity.latitude, longitude: selectedCity.longitude }
        : initial
          ? { latitude: initial.latitude, longitude: initial.longitude }
          : null);
    const state = selectedCity?.state ?? initial?.state;
    if (!coordinates || !state) {
      const missing = { city: "Choose the city." };
      setErrors(missing);
      focusFirstInvalid(missing, FIELD_ORDER);
      return;
    }

    setErrors({});
    setGeneralError(null);
    setSubmitting(true);

    const body = {
      name: form.name.trim(),
      address: form.address.trim(),
      city: form.city,
      state,
      latitude: coordinates.latitude,
      longitude: coordinates.longitude,
      registration_number: form.registrationNumber.trim() || null,
      contact_phone: form.phone.trim(),
    };

    try {
      if (initial) {
        await api.put("/hospitals/me", body);
      } else {
        await api.post("/hospitals", body);
      }
      await router.push("/hospital");
    } catch (error) {
      const failure = failureFromError(error);
      // Problems with the derived fields are best explained next to the city choice.
      const fields = { ...failure.fields };
      fields.city ??= fields.state ?? fields.latitude ?? fields.longitude;
      setErrors(fields);
      setGeneralError(failure.general);
      setSubmitting(false);
      focusFirstInvalid(fields, FIELD_ORDER);
    }
  }

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
        <h2 className="text-heading font-semibold text-ink">About the hospital</h2>

        <FormField
          id="name"
          name="name"
          label="Hospital name"
          autoComplete="organization"
          hint="As it appears on your registration documents."
          value={form.name}
          onChange={(event) => update("name", event.target.value)}
          error={errors.name}
        />
        <FormField
          id="address"
          name="address"
          label="Street address"
          autoComplete="street-address"
          value={form.address}
          onChange={(event) => update("address", event.target.value)}
          error={errors.address}
        />
        <FormField
          id="registration_number"
          name="registration_number"
          label="Registration or licence number"
          optional
          hint="It helps the administrator verify your hospital faster."
          value={form.registrationNumber}
          onChange={(event) => update("registrationNumber", event.target.value)}
          error={errors.registration_number}
        />
        <FormField
          id="contact_phone"
          name="contact_phone"
          label="Contact phone number"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          hint="A number the administrator or a donor can call, for example +2348031234567."
          value={form.phone}
          onChange={(event) => update("phone", event.target.value)}
          error={errors.contact_phone}
        />
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">Where it is</h2>
        <LocationPicker
          city={form.city}
          unlistedCity={unlistedCity}
          precise={form.precise}
          onCityChange={(value) => update("city", value)}
          onPreciseChange={(value) => update("precise", value)}
          error={errors.city}
          deviceButtonLabel="Use my current location (if you are at the hospital)"
        />
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" disabled={submitting}>
          {submitting
            ? "Saving..."
            : !initial
              ? "Register hospital"
              : initial.verification_status === "rejected"
                ? "Save and resubmit"
                : "Save changes"}
        </Button>
        {initial ? (
          <Link href="/hospital" className={buttonVariants({ variant: "ghost", size: "lg" })}>
            Cancel
          </Link>
        ) : null}
      </div>
    </form>
  );
}
