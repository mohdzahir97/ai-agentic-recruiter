"use client";

import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  PageHeader,
  SkillChips,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { initials } from "@/lib/format";
import type { CandidateProfile } from "@/lib/types";

export default function RecruiterCandidatesPage() {
  const [candidates, setCandidates] = useState<CandidateProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .recruiterCandidates()
      .then(setCandidates)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Candidates"
        subtitle="Everyone who has applied to one of your jobs. A candidate becomes visible to you only by applying."
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      {candidates.length === 0 ? (
        <Card>
          <EmptyState
            title="No candidates yet"
            hint="Once someone applies to one of your jobs, their profile appears here."
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {candidates.map((candidate) => (
            <Card key={candidate.id}>
              <CardHeader
                title={
                  <span className="flex items-center gap-2.5">
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
                      {initials(candidate.full_name)}
                    </span>
                    {candidate.full_name}
                  </span>
                }
                subtitle={candidate.headline || candidate.email}
                action={
                  <div className="flex flex-col items-end gap-1">
                    <Badge tone={candidate.has_resume ? "green" : "slate"}>
                      {candidate.has_resume ? "Resume" : "No resume"}
                    </Badge>
                    {candidate.resume_analyzed ? (
                      <Badge tone="blue">AI analysed</Badge>
                    ) : null}
                  </div>
                }
              />
              <CardBody className="space-y-3">
                <div className="flex flex-wrap gap-3 text-xs text-slate-500">
                  <span>{candidate.location || "Location not set"}</span>
                  {candidate.years_experience != null ? (
                    <span>· {candidate.years_experience} yrs experience</span>
                  ) : null}
                </div>
                <SkillChips items={candidate.skills} tone="blue" max={8} />
                {candidate.education?.length ? (
                  <p className="text-xs text-slate-500">
                    {candidate.education[0]?.degree}
                    {candidate.education[0]?.institution
                      ? ` · ${candidate.education[0].institution}`
                      : ""}
                  </p>
                ) : null}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
