"use client";

/** Wraps every candidate route in the RBAC guard and the portal chrome. */
import { Shell } from "@/components/Shell";
import { RequireRole } from "@/lib/auth";

export default function CandidateLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RequireRole role="CANDIDATE">
      <Shell role="CANDIDATE">{children}</Shell>
    </RequireRole>
  );
}
