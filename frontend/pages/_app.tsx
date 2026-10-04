/**
 * Custom App component: wraps every page with global styles, authentication state and the
 * shared layout.
 */

import type { AppProps } from "next/app";

import { Layout } from "@/components/Layout";
import { AuthProvider } from "@/context/AuthContext";
import "@/styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <AuthProvider>
      <Layout>
        <Component {...pageProps} />
      </Layout>
    </AuthProvider>
  );
}
