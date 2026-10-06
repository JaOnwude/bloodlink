/**
 * Home page (interim version).
 *
 * States the product in one sentence and shows live connectivity to the API. The page is
 * deliberately small while the product screens are built; it already uses the shared
 * layout components and reveal animation so it matches the rest of the site.
 */

import Head from "next/head";

import { ApiStatus } from "@/components/ApiStatus";
import { Container } from "@/components/layout/Container";
import { Section } from "@/components/layout/Section";
import { Reveal } from "@/components/motion/Reveal";
import { siteConfig } from "@/lib/site";

export default function HomePage() {
  return (
    <>
      <Head>
        <title>BloodLink: urgent blood, matched to donors who can give</title>
        <meta name="description" content={siteConfig.description} />
      </Head>

      <Section>
        <Container>
          <Reveal>
            <p className="mb-4 text-sm font-semibold tracking-wider text-primary-600 uppercase">
              Urgent blood, matched to people who can give
            </p>
            <h1 className="max-w-3xl text-display font-semibold text-ink">
              When a hospital needs O-negative tonight, find donors who can actually give.
            </h1>
            <p className="mt-6 max-w-2xl text-lead text-ink-muted">
              BloodLink matches verified hospitals with compatible, eligible donors nearby, then
              tracks every pledge through to a confirmed donation.
            </p>
          </Reveal>

          <Reveal delay={120} className="mt-10 max-w-xl">
            <ApiStatus />
          </Reveal>
        </Container>
      </Section>
    </>
  );
}
