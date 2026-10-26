/**
 * A crimson band of short facts under the landing page hero.
 *
 * Every figure here is a property of how BloodLink works, not a usage statistic: there are
 * no users yet to count, and an invented "10,000 donors" would mislead the hospitals and
 * officials reading the page. Replace these with real figures once the pilot has them.
 */

import { Reveal } from "@/components/motion/Reveal";
import { Container } from "@/components/layout/Container";

const FACTS = [
  { value: "8", label: "blood groups matched by the transfusion compatibility chart" },
  { value: "4", label: "postcode rings, so the donors nearest the hospital hear first" },
  { value: "0", label: "units overbooked, even when donors answer at the same moment" },
  { value: "₦0", label: "for donors and families. Always." },
];

export function FactStrip() {
  return (
    <section className="bg-primary-600 text-white" aria-label="BloodLink in numbers">
      <Container>
        <ul className="grid grid-cols-2 gap-x-6 gap-y-8 py-10 lg:grid-cols-4 lg:py-12">
          {FACTS.map((fact, index) => (
            <Reveal as="li" key={fact.label} delay={index * 60} className="space-y-1">
              <p className="font-heading text-4xl font-semibold tabular-nums">{fact.value}</p>
              <p className="max-w-[16rem] text-sm text-white/85">{fact.label}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
