/**
 * Public page for a family looking for blood for a patient in hospital.
 *
 * No account is needed. The family finds the verified hospital the patient is in (by its
 * NIPOST postcode or their location), then sends it an appeal. The hospital confirms the
 * patient before BloodLink alerts any donor, and the family follows progress at a private
 * link.
 */

import Head from "next/head";
import { useState } from "react";

import { FamilyRequestForm } from "@/components/family/FamilyRequestForm";
import { HospitalFinder } from "@/components/family/HospitalFinder";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import type { PublicHospital } from "@/types/api";

const STEPS = [
  "Find the hospital your patient is in.",
  "Tell it what the doctor asked for.",
  "The hospital confirms, and nearby donors are alerted.",
];

export default function FindBloodPage() {
  const [hospital, setHospital] = useState<PublicHospital | null>(null);

  return (
    <>
      <Head>
        <title>Find blood for a patient | BloodLink</title>
        <meta
          name="description"
          content="Ask a verified hospital to find blood donors for your patient. No account needed."
        />
      </Head>
      <Section>
        <Container size="reading">
          <div className="space-y-8">
            <div className="space-y-3">
              <h1 className="text-title font-semibold text-ink">
                Need blood for someone in hospital?
              </h1>
              <p className="text-ink-muted">
                Ask the hospital through BloodLink instead of searching alone. Once the hospital
                confirms your patient, we alert eligible donors nearby, starting with those in the
                hospital&apos;s own postcode area.
              </p>
              <ol className="grid gap-2 text-sm text-ink sm:grid-cols-3">
                {STEPS.map((step, index) => (
                  <li key={step} className="rounded-xl bg-surface p-3 ring-1 ring-border">
                    <span className="font-semibold text-primary">{index + 1}. </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>

            {hospital ? (
              <FamilyRequestForm hospital={hospital} onBack={() => setHospital(null)} />
            ) : (
              <HospitalFinder onChoose={setHospital} />
            )}
          </div>
        </Container>
      </Section>
    </>
  );
}
