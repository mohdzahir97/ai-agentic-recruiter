"use client";

/** Wraps every recruiter route in the RBAC guard and the portal chrome. */
import { Shell } from "@/components/Shell";
import { RequireRole } from "@/lib/auth";

export default function RecruiterLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireRole role="RECRUITER">
      <Shell role="RECRUITER">{children}</Shell>
    </RequireRole>
  );
}
