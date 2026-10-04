/**
 * Home page.
 *
 * Presents the product in one sentence and shows live connectivity to the API. The page is
 * kept intentionally small so the structure (routing, layout, API client, authentication
 * context) can be verified independently of any product screens.
 */

import Head from "next/head";

import { ApiStatus } from "@/components/ApiStatus";

export default function HomePage() {
  return (
    <>
      <Head>
        <title>BloodLink: urgent blood, matched to donors who can give</title>
        <meta
          name="description"
          content="BloodLink helps verified hospitals find compatible, eligible donors nearby when blood is needed urgently."
        />
      </Head>

      <section className="py-10">
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-foreground">
          When a hospital needs O-negative tonight, find donors who can actually give.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          BloodLink matches verified hospitals with compatible, eligible donors nearby, then
          tracks every pledge through to a confirmed donation.
        </p>

        <div className="mt-8">
          <ApiStatus />
        </div>
      </section>
    </>
  );
}
