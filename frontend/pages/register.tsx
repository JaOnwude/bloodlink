/**
 * Registration page.
 *
 * The visitor chooses whether they are a donor or hospital staff, then supplies their name,
 * email, optional phone number and a password. The browser checks the obvious problems
 * first (missing fields, a password that is too short); the server applies the full rules and
 * any problem it finds is shown beside the field it concerns. Registering also signs the new
 * user in, after which the visitor is sent on.
 *
 * A link can preselect the account type with `?as=hospital`, as the landing page's
 * "Register your hospital" button does. Donor is the default.
 */

import { CircleAlert } from "lucide-react";
import Head from "next/head";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";
import type { FormEvent } from "react";

import { AuthShell } from "@/components/auth/AuthShell";
import { FormField } from "@/components/auth/FormField";
import { PasswordField } from "@/components/auth/PasswordField";
import { RoleChoice } from "@/components/auth/RoleChoice";
import type { SelfServiceRole } from "@/components/auth/RoleChoice";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import {
  PASSWORD_MIN_LENGTH,
  failureFromError,
  focusFirstInvalid,
} from "@/lib/forms";
import type { FieldErrors } from "@/lib/forms";
import { images } from "@/lib/images";
import { useRedirectIfSignedIn } from "@/lib/use-redirect-if-signed-in";

const FIELD_ORDER = ["full_name", "email", "phone", "password"];

function RegisterForm({ initialRole }: { initialRole: SelfServiceRole }) {
  const { refresh } = useAuth();
  // Signed-in visitors are redirected by this hook once the session is confirmed.
  const requestedPath = useRedirectIfSignedIn();

  const [role, setRole] = useState<SelfServiceRole>(initialRole);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting) return;

    const problems: FieldErrors = {};
    if (fullName.trim().length < 2) problems.full_name = "Enter your full name.";
    if (!email.trim()) problems.email = "Enter your email address.";
    // Counted in characters, not code units, to match the server's rule.
    if ([...password].length < PASSWORD_MIN_LENGTH) {
      problems.password = `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
    }
    if (Object.keys(problems).length > 0) {
      setErrors(problems);
      setGeneralError(null);
      focusFirstInvalid(problems, FIELD_ORDER);
      return;
    }

    setErrors({});
    setGeneralError(null);
    setSubmitting(true);
    try {
      await api.post("/auth/register", {
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        role,
        ...(phone.trim() ? { phone: phone.trim() } : {}),
      });
      const current = await refresh();
      if (!current) {
        setGeneralError(
          "Your account was created, but your browser did not keep the session. Check that cookies are allowed, then sign in.",
        );
        setSubmitting(false);
      }
      // On success the redirect hook navigates once the session is confirmed.
    } catch (error) {
      const failure = failureFromError(error);
      setErrors(failure.fields);
      setGeneralError(failure.general);
      setSubmitting(false);
      focusFirstInvalid(failure.fields, FIELD_ORDER);
    }
  }

  const signInHref = requestedPath
    ? `/login?next=${encodeURIComponent(requestedPath)}`
    : "/login";

  return (
    <>
      <Head>
        <title>Create an account | BloodLink</title>
        <meta name="robots" content="noindex" />
      </Head>

      <AuthShell
        title="Create your account"
        description="It takes about a minute. You choose what to share and when to be contacted."
        image={images.authRegister}
        panelHeading="Be ready when a patient needs you."
        panelPoints={[
          "You are contacted only when your blood group and location match a request.",
          "Pause alerts at any time from your profile.",
          "A hospital sees your contact details only after you pledge.",
        ]}
        footer={
          <p>
            Already have an account?{" "}
            <Link
              href={signInHref}
              className="font-semibold text-primary-600 underline-offset-4 hover:underline"
            >
              Sign in
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

          <RoleChoice value={role} onChange={setRole} />

          <FormField
            id="full_name"
            name="full_name"
            label="Full name"
            autoComplete="name"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            error={errors.full_name}
          />

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

          <FormField
            id="phone"
            name="phone"
            label="Phone number"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            optional
            hint="Used for alerts. For example +2348031234567."
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            error={errors.phone}
          />

          <PasswordField
            id="password"
            name="password"
            label="Password"
            autoComplete="new-password"
            hint={`At least ${PASSWORD_MIN_LENGTH} characters. A phrase of unrelated words is easy to remember and hard to guess.`}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errors.password}
          />

          <Button type="submit" size="lg" className="w-full" disabled={submitting}>
            {submitting ? "Creating your account..." : "Create account"}
          </Button>

          <p className="text-sm text-ink-muted">
            {role === "donor"
              ? "Next you will add your blood group and location, and choose when you can be contacted."
              : "Next you will register your hospital. An administrator verifies it before you can request blood."}
          </p>
        </form>
      </AuthShell>
    </>
  );
}

export default function RegisterPage() {
  const router = useRouter();
  // The address is only readable once the router is ready, after the first render. Keying the
  // form on the role remounts it with the right choice before the visitor has typed anything.
  const initialRole: SelfServiceRole =
    router.isReady && router.query.as === "hospital" ? "hospital_staff" : "donor";
  return <RegisterForm key={initialRole} initialRole={initialRole} />;
}
