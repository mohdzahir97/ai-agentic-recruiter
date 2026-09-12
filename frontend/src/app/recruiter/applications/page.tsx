"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Spinner,
  Table,
  Td,
  cx,
} from "@/components/ui";
import { api } from "@/lib/api";
import {
  RECOMMENDATION_LABEL,
  RECOMMENDATION_TONE,
  STATUS_LABEL,
  STATUS_TONE,
  formatDate,
  pct,
} from "@/lib/format";
import type { Application, ApplicationStatus } from "@/lib/types";

const FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "APPLIED", label: "Applied" },
  { value: "SCREENING", label: "In screening" },
  { value: "SHORTLISTED", label: "Shortlisted" },
  { value: "ON_HOLD", label: "On hold" },
  { value: "REJECTED", label: "Rejected" },
];

export default function RecruiterApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .recruiterApplications(filter || undefined)
      .then(setApplications)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Applications"
        subtitle="Every application across your jobs, with the AI's recommendation and the human decision side by side."
      />

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((option) => (
          <button
            key={option.value}
            onClick={() => setFilter(option.value)}
            className={cx(
              "rounded-lg px-3 py-1.5 text-xs ring-1 ring-inset transition-colors",
              filter === option.value
                ? "bg-slate-900 font-medium text-white ring-slate-900"
                : "bg-white text-slate-600 ring-slate-300 hover:bg-slate-50",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>

      {error ? <Alert tone="red">{error}</Alert> : null}

      <Card>
        <CardHeader
          title={`${applications.length} application${applications.length === 1 ? "" : "s"}`}
        />
        {loading ? (
          <Spinner />
        ) : applications.length === 0 ? (
          <EmptyState
            title="Nothing here"
            hint={
              filter
                ? "No applications with that status."
                : "No one has applied to your jobs yet."
            }
          />
        ) : (
          <Table
            headers={[
              "Candidate",
              "Job",
              "Applied",
              "AI says",
              "Match",
              "Human decision",
              "Status",
              "",
            ]}
          >
            {applications.map((application) => (
              <tr key={application.id} className="hover:bg-slate-50">
                <Td label="Candidate">
                  <p className="text-sm font-medium text-slate-900">
                    {application.candidate_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {application.candidate_email}
                  </p>
                </Td>
                <Td label="Job" className="text-sm text-slate-600">{application.job_title}</Td>
                <Td label="Applied" className="text-sm text-slate-500">
                  {formatDate(application.created_at)}
                </Td>
                <Td label="AI says">
                  {application.screening ? (
                    <Badge
                      tone={RECOMMENDATION_TONE[application.screening.recommendation]}
                    >
                      {RECOMMENDATION_LABEL[application.screening.recommendation]}
                    </Badge>
                  ) : (
                    <span className="text-xs text-slate-400">—</span>
                  )}
                </Td>
                <Td label="Match" className="text-sm tabular-nums text-slate-700">
                  {application.screening
                    ? pct(application.screening.overall_match)
                    : "—"}
                </Td>
                <Td label="Human decision">
                  {application.review ? (
                    <div className="flex flex-col gap-1">
                      <span className="text-sm text-slate-700">
                        {application.review.decision}
                      </span>
                      {application.review.overrode_ai ? (
                        <Badge tone="amber">Override</Badge>
                      ) : null}
                    </div>
                  ) : (
                    <span className="text-xs text-amber-600">Pending</span>
                  )}
                </Td>
                <Td label="Status">
                  <Badge tone={STATUS_TONE[application.status as ApplicationStatus]}>
                    {STATUS_LABEL[application.status as ApplicationStatus]}
                  </Badge>
                </Td>
                <Td label="">
                  <Link href={`/recruiter/screening/${application.id}`}>
                    <Button size="sm" variant="secondary">
                      Open
                    </Button>
                  </Link>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
