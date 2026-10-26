/**
 * Custom App component: wraps every page with fonts, global styles, authentication state and
 * the shared layout.
 *
 * Fonts are loaded with next/font, which downloads them at build time and serves them from
 * the site's own domain, so visitors make no request to a third-party font host. Their
 * names are published as CSS variables on :root so the design tokens in styles/globals.css
 * (and elements rendered outside the page tree, such as menus) can use them.
 */

import type { AppProps } from "next/app";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";

import { Layout } from "@/components/Layout";
import { AuthProvider } from "@/context/AuthContext";
import "@/styles/globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });
const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], display: "swap" });

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <style jsx global>{`
        :root {
          --font-inter: ${inter.style.fontFamily};
          --font-jakarta: ${jakarta.style.fontFamily};
        }
      `}</style>
      <AuthProvider>
        <Layout>
          <Component {...pageProps} />
        </Layout>
      </AuthProvider>
    </>
  );
}
