/**
 * Display helpers shared by both portals.
 *
 * The status and recommendation colour maps live here rather than in the
 * components, so a SHORTLISTED badge looks the same on the dashboard, the
 * table and the screening page.
 */
import type { ApplicationStatus, Decision, Recommendation } from "./types";

export type Tone = "green" | "amber" | "red" | "blue" | "slate";

export const STATUS_TONE: Record<ApplicationStatus, Tone> = {
  APPLIED: "slate",
  SCREENING: "blue",
  SHORTLISTED: "green",
  ON_HOLD: "amber",
  REJECTED: "red",
};

export const STATUS_LABEL: Record<ApplicationStatus, string> = {
  APPLIED: "Applied",
  SCREENING: "In screening",
  SHORTLISTED: "Shortlisted",
  ON_HOLD: "On hold",
  REJECTED: "Rejected",
};

export const RECOMMENDATION_TONE: Record<Recommendation, Tone> = {
  STRONG_MATCH: "green",
  GOOD_MATCH: "blue",
  PARTIAL_MATCH: "amber",
  WEAK_MATCH: "red",
};

export const RECOMMENDATION_LABEL: Record<Recommendation, string> = {
  STRONG_MATCH: "Strong match",
  GOOD_MATCH: "Good match",
  PARTIAL_MATCH: "Partial match",
  WEAK_MATCH: "Weak match",
};

export const DECISION_TONE: Record<Decision, Tone> = {
  SHORTLIST: "green",
  HOLD: "amber",
  REJECT: "red",
};

/** Score colour, used by every progress bar and the match ring. */
export function scoreTone(value: number): Tone {
  if (value >= 85) return "green";
  if (value >= 70) return "blue";
  if (value >= 50) return "amber";
  return "red";
}

export function pct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Math.round(value)}%`;
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** Split a comma-separated input into a clean list of skills. */
export function parseList(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}
