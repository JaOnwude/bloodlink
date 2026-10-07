/**
 * Custom Document: the HTML shell around every page.
 *
 * A tiny inline script marks the page as JavaScript-enabled before the first paint. The
 * scroll-reveal styles only hide content when this marker is present, so visitors without
 * JavaScript still see everything.
 */

import { Head, Html, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <script
          dangerouslySetInnerHTML={{
            __html: "document.documentElement.classList.add('js')",
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
