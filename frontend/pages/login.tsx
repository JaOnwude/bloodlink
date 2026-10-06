/**
 * Sign-in page.
 *
 * Checks the form locally for empty fields, sends the credentials to the API (which sets the
 * session cookie), then asks the API who is signed in. Once the session is confirmed, an
 * hook sends the visitor on to the page they were trying to reach, or to the landing page
 * for their role. Visitors who are already signed in are sent on immediately.
 */

import { CircleAlert } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useState } from "react";
import type { FormEvent } from "react";

import { AuthShell } from "@/components/auth/AuthShell";
import { FormField } from "@/components/auth/FormField";
import { PasswordField } from "@/components/auth/PasswordField";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import { failureFromError, focusFirstInvalid } from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { images } from "@/lib/images";
import { useRedirectIfSignedIn } from "@/lib/use-redirect-if-signed-in";

export default function LoginPage() {
  const { refresh } = useAuth();
  // Signed-in visitors are redirected by this hook once the session is confirmed.
  const requestedPath = useRedirectIfSignedIn();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const problems: FieldErrors = {};
    if (!email.trim()) problems.email = "Enter your email address.";
    if (!password) problems.password = "Enter your password.";
    if (Object.keys(problems).length > 0) {
      setErrors(problems);
      setGeneralError(null);
      focusFirstInvalid(problems, ["email", "password"]);
      return;
    }

    setErrors({});
    setGeneralError(null);
    setSubmitting(true);
    try {
      await api.post("/auth/login", { email: email.trim(), password });
      const current = await refresh();
      if (!current) {
        setGeneralError(
          "You were signed in, but your browser did not keep the session. Check that cookies are allowed and try again.",
        );
        setSubmitting(false);
      }
      // On success the redirect hook navigates once the session is confirmed.
    } catch (error) {
      const failure = failureFromError(error);
      setErrors(failure.fields);
      setGeneralError(failure.general);
      setSubmitting(false);
    }
  }

  const registerHref = requestedPath
    ? `/register?next=${encodeURIComponent(requestedPath)}`
    : "/register";

  return (
    <>
      <Head>
        <title>Sign in | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>

      <AuthShell
        title="Welcome back"
        description="Sign in to manage requests, pledges and your profile."
        image={images.authSignIn}
        panelHeading="Every alert comes from a hospital we have verified."
        panelPoints={[
          "An administrator checks each hospital before it can send a request.",
          "Donors choose when they can be contacted.",
          "Every pledge is tracked through to a confirmed donation.",
        ]}
        footer={
          <p>
            New to BloodLink?{" "}
            <Link
              href={registerHref}
              className="font-semibold text-primary-600 underline-offset-4 hover:underline"
            >
              Create an account
            </Link>
          </p>
        }
      >
        <form onSubmit={(event) => void handleSubmit(event)} noValidate className="space-y-5">
          {generalError ? (
            <div
              role="alert"
              className="flex items-start gap-2.5 rounded-xl bg-primary-50 p-4 text-sm text-primary-900"
            >
              <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
              <span>{generalError}</span>
            </div>
          ) : null}

          <FormField
            id="email"
            name="email"
            label="Email address"
            type="email"
            autoComplete="email"
            inputMode="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            error={errors.email}
          />

          <PasswordField
            id="password"
            name="password"
            label="Password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errors.password}
          />

          <Button type="submit" size="lg" className="w-full" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>
      </AuthShell>
    </>
  );
}
