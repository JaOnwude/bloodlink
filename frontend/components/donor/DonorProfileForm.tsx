/**
 * The form a donor uses to create or edit their profile.
 *
 * Location is chosen from a list of Nigerian cities (easy and private). A donor who wants a
 * closer match can add their device location, which is rounded to about one kilometre before
 * it is sent, so their exact position is never stored.
 *
 * The browser checks the obvious problems first. The server applies the full rules, and
 * anything it rejects is shown beside the field it concerns.
 */

import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";
import type { FormEvent } from "react";

import { FormField } from "@/components/auth/FormField";
import { CheckboxField } from "@/components/form/CheckboxField";
import { ChoiceCards } from "@/components/form/ChoiceCards";
import { LocationPicker } from "@/components/form/LocationPicker";
import { SelectField } from "@/components/form/SelectField";
import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { failureFromError, focusFirstInvalid } from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { todayIso } from "@/lib/format";
import { findCity } from "@/lib/locations";
import type { Coordinates } from "@/lib/locations";
import { BLOOD_GROUPS } from "@/types/api";
import type { BloodGroup, DonorProfile, Sex } from "@/types/api";

interface FormState {
  bloodGroup: BloodGroup | "";
  dateOfBirth: string;
  sex: Sex | "";
  weight: string;
  city: string;
  lastDonation: string;
  isAvailable: boolean;
  consent: boolean;
  /** Device location, when the donor chose to use it. Null means "use the city centre". */
  precise: Coordinates | null;
}

/** Field names in the order they appear, used to move focus to the first problem. */
const FIELD_ORDER = [
  "blood_group",
  "date_of_birth",
  "sex",
  "weight_kg",
  "city",
  "last_donation_date",
];

const SEX_OPTIONS = [
  { value: "male" as const, title: "Male" },
  { value: "female" as const, title: "Female" },
];

function initialState(initial: DonorProfile | null): FormState {
  if (!initial) {
    return {
      bloodGroup: "",
      dateOfBirth: "",
      sex: "",
      weight: "",
      city: "",
      lastDonation: "",
      isAvailable: true,
      consent: false,
      precise: null,
    };
  }

  // If the saved coordinates are not the centre of the saved city, the donor used their
  // device location, so keep it.
  const match = findCity(initial.city);
  const atCityCentre =
    match !== undefined &&
    Math.abs(match.latitude - initial.latitude) < 0.0005 &&
    Math.abs(match.longitude - initial.longitude) < 0.0005;

  return {
    bloodGroup: initial.blood_group,
    dateOfBirth: initial.date_of_birth,
    sex: initial.sex,
    weight: String(initial.weight_kg),
    city: initial.city,
    lastDonation: initial.last_donation_date ?? "",
    isAvailable: initial.is_available,
    consent: initial.consent_to_contact,
    precise: atCityCentre ? null : { latitude: initial.latitude, longitude: initial.longitude },
  };
}

function parseWeight(text: string): number | null {
  const value = Number(text.replace(",", ".").trim());
  return text.trim() !== "" && Number.isFinite(value) ? value : null;
}

function validate(form: FormState): FieldErrors {
  const problems: FieldErrors = {};
  const today = todayIso();

  if (!form.bloodGroup) problems.blood_group = "Choose your blood group.";

  if (!form.dateOfBirth) problems.date_of_birth = "Enter your date of birth.";
  else if (form.dateOfBirth > today) problems.date_of_birth = "Date of birth cannot be in the future.";

  if (!form.sex) problems.sex = "Choose one option.";

  const weight = parseWeight(form.weight);
  if (weight === null) problems.weight_kg = "Enter your weight in kilograms.";
  else if (weight < 20 || weight > 300) problems.weight_kg = "Enter a weight between 20 and 300 kg.";

  if (!form.city) problems.city = "Choose your city.";

  if (form.lastDonation) {
    if (form.lastDonation > today) {
      problems.last_donation_date = "The last donation date cannot be in the future.";
    } else if (form.dateOfBirth && form.lastDonation < form.dateOfBirth) {
      problems.last_donation_date = "The last donation cannot be before your date of birth.";
    }
  }
  return problems;
}

export function DonorProfileForm({ initial }: { initial: DonorProfile | null }) {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(() => initialState(initial));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  // A city saved earlier that is not in the list is kept as an extra choice, so editing
  // an old profile never loses its city.
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
    if (!coordinates) {
      const missing = { city: "Choose your city." };
      setErrors(missing);
      focusFirstInvalid(missing, FIELD_ORDER);
      return;
    }

    setErrors({});
    setGeneralError(null);
    setSubmitting(true);
    try {
      await api.put("/donors/me", {
        blood_group: form.bloodGroup,
        date_of_birth: form.dateOfBirth,
        weight_kg: parseWeight(form.weight),
        sex: form.sex,
        latitude: coordinates.latitude,
        longitude: coordinates.longitude,
        city: form.city,
        last_donation_date: form.lastDonation || null,
        is_available: form.isAvailable,
        consent_to_contact: form.consent,
      });
      await router.push("/donor");
    } catch (error) {
      const failure = failureFromError(error);
      // A coordinate problem is best explained next to the location choice.
      const fields = { ...failure.fields };
      fields.city ??= fields.latitude ?? fields.longitude;
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
        <h2 className="text-heading font-semibold text-ink">About you</h2>

        <SelectField
          id="blood_group"
          name="blood_group"
          label="Blood group"
          hint="If you are not sure, a clinic or blood bank can tell you."
          value={form.bloodGroup}
          onChange={(event) => update("bloodGroup", event.target.value as BloodGroup | "")}
          error={errors.blood_group}
        >
          <option value="">Select your blood group</option>
          {BLOOD_GROUPS.map((group) => (
            <option key={group} value={group}>
              {group}
            </option>
          ))}
        </SelectField>

        <div className="grid gap-5 sm:grid-cols-2">
          <FormField
            id="date_of_birth"
            name="date_of_birth"
            label="Date of birth"
            type="date"
            max={todayIso()}
            autoComplete="bday"
            hint="Used to check the age range for donating."
            value={form.dateOfBirth}
            onChange={(event) => update("dateOfBirth", event.target.value)}
            error={errors.date_of_birth}
          />
          <FormField
            id="weight_kg"
            name="weight_kg"
            label="Weight (kg)"
            type="text"
            inputMode="decimal"
            hint="Used to check the minimum weight."
            value={form.weight}
            onChange={(event) => update("weight", event.target.value)}
            error={errors.weight_kg}
          />
        </div>

        <ChoiceCards
          name="sex"
          legend="Sex"
          options={SEX_OPTIONS}
          value={form.sex}
          onChange={(value) => update("sex", value)}
          hint="Used only to apply the correct waiting period between donations."
          error={errors.sex}
        />
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">Where you are</h2>

        <LocationPicker
          city={form.city}
          unlistedCity={unlistedCity}
          precise={form.precise}
          onCityChange={(value) => update("city", value)}
          onPreciseChange={(value) => update("precise", value)}
          error={errors.city}
        />
      </section>

      <section className="space-y-5">
        <h2 className="text-heading font-semibold text-ink">Your donation history</h2>
        <FormField
          id="last_donation_date"
          name="last_donation_date"
          label="Date of your last donation"
          type="date"
          max={todayIso()}
          optional
          hint="Leave empty if you have never donated or do not remember."
          value={form.lastDonation}
          onChange={(event) => update("lastDonation", event.target.value)}
          error={errors.last_donation_date}
        />
      </section>

      <section className="space-y-4">
        <h2 className="text-heading font-semibold text-ink">Contact preferences</h2>
        <CheckboxField
          id="consent"
          name="consent"
          label="You may contact me about matching blood requests"
          description="Without this, you will not receive requests. You can change it at any time."
          checked={form.consent}
          onChange={(event) => update("consent", event.target.checked)}
        />
        <CheckboxField
          id="available"
          name="available"
          label="I am available to donate"
          description="Turn this off to pause alerts without losing your profile."
          checked={form.isAvailable}
          onChange={(event) => update("isAvailable", event.target.checked)}
        />
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" size="lg" disabled={submitting}>
          {submitting ? "Saving..." : initial ? "Save changes" : "Create profile"}
        </Button>
        <Link href="/donor" className={buttonVariants({ variant: "ghost", size: "lg" })}>
          Cancel
        </Link>
      </div>
    </form>
  );
}
