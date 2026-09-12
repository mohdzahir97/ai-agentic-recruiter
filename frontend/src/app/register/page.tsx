"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert, Button, Card, CardBody, Field, Input, cx } from "@/components/ui";
import { homeFor, useAuth } from "@/lib/auth";
import type { Role } from "@/lib/types";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  const [role, setRole] = useState<Role>("CANDIDATE");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [company, setCompany] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const user = await register({
        email,
        password,
        full_name: fullName,
        role,
        company: role === "RECRUITER" ? company : undefined,
      });
      router.replace(homeFor(user.role));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-sm font-bold text-white">
            AI
          </div>
          <h1 className="text-lg font-semibold text-slate-900">
            Create your account
          </h1>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <span className="text-xs font-medium text-slate-700">
                  I am a
                </span>
                <div className="mt-1.5 grid grid-cols-2 gap-2">
                  {(["CANDIDATE", "RECRUITER"] as Role[]).map((option) => (
                    <button
                      key={option}
                      type="button"
                      onClick={() => setRole(option)}
                      className={cx(
                        "rounded-lg px-3 py-2 text-sm ring-1 ring-inset transition-colors",
                        role === option
                          ? "bg-slate-900 font-medium text-white ring-slate-900"
                          : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50",
                      )}
                    >
                      {option === "CANDIDATE" ? "Candidate" : "Recruiter"}
                    </button>
                  ))}
                </div>
              </div>

              <Field label="Full name">
                <Input value={fullName} onChange={setFullName} required />
              </Field>
              <Field label="Email">
                <Input type="email" value={email} onChange={setEmail} required />
              </Field>
              <Field label="Password" hint="At least 8 characters.">
                <Input
                  type="password"
                  value={password}
                  onChange={setPassword}
                  required
                />
              </Field>

              {role === "RECRUITER" ? (
                <Field label="Company">
                  <Input value={company} onChange={setCompany} />
                </Field>
              ) : null}

              {error ? <Alert tone="red">{error}</Alert> : null}

              <Button type="submit" disabled={submitting} className="w-full">
                {submitting ? "Creating…" : "Create account"}
              </Button>
            </form>
          </CardBody>
        </Card>

        <p className="mt-4 text-center text-sm text-slate-500">
          Already registered?{" "}
          <Link
            href="/login"
            className="font-medium text-slate-900 underline underline-offset-2"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
