"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  EmptyState,
  PageHeader,
  SkillChips,
  Spinner,
  Table,
  Td,
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
import type { Application, Job } from "@/lib/types";

export default function RecruiterJobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [screening, setScreening] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([api.getJob(jobId), api.jobApplications(jobId)])
      .then(([j, a]) => {
        setJob(j);
        setApplications(a);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [jobId]);

  async function runScreening(applicationId: number) {
    setScreening(applicationId);
    setError("");
    try {
      await api.screen(applicationId);
      setApplications(await api.jobApplications(jobId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Screening failed");
    } finally {
      setScreening(null);
    }
  }

  if (loading) return <Spinner />;
  if (!job) return <Alert tone="red">{error || "Job not found"}</Alert>;

  const analysis = job.jd_analysis;
  const unscreened = applications.filter((a) => !a.screening).length;

  return (
    <div className="space-y-6">
      <PageHeader
        title={job.title}
        subtitle={`${job.company}${job.location ? ` · ${job.location}` : ""} · posted ${formatDate(job.created_at)}`}
        action={
          <div className="flex flex-wrap gap-2">
            <Link href="/recruiter/jobs">
              <Button variant="secondary" size="sm">
                Back
              </Button>
            </Link>
            <Link href={`/recruiter/jobs/${jobId}/edit`}>
              <Button size="sm">Edit job</Button>
            </Link>
          </div>
        }
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Description"
            action={
              <Badge tone={job.status === "ACTIVE" ? "green" : "slate"}>
                {job.status}
              </Badge>
            }
          />
          <CardBody>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
              {job.description}
            </p>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="AI job analysis"
            subtitle="Extracted by the Job Agent when the job was saved."
          />
          <CardBody className="space-y-4">
            {!analysis ? (
              <p className="text-sm text-slate-400">
                Not analysed. Edit and save the job to run the agent.
              </p>
            ) : (
              <>
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Required skills
                  </p>
                  <SkillChips items={analysis.required_skills} tone="blue" />
                </div>
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Preferred skills
                  </p>
                  <SkillChips items={analysis.preferred_skills} tone="slate" />
                </div>
                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Technologies
                  </p>
                  <SkillChips items={analysis.technologies} tone="green" />
                </div>
                <div className="space-y-1 text-sm text-slate-700">
                  <p>
                    <span className="text-slate-500">Experience:</span>{" "}
                    {analysis.experience_requirement || "Not specified"}
                  </p>
                  <p>
                    <span className="text-slate-500">Education:</span>{" "}
                    {analysis.education_requirement || "Not required"}
                  </p>
                  <p>
                    <span className="text-slate-500">Seniority:</span>{" "}
                    {analysis.seniority || "—"}
                  </p>
                </div>
                {analysis.responsibilities.length ? (
                  <div>
                    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                      Responsibilities
                    </p>
                    <ul className="space-y-1">
                      {analysis.responsibilities.map((item) => (
                        <li key={item} className="text-sm text-slate-700">
                          · {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </>
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          title={`Applications (${applications.length})`}
          subtitle={
            unscreened
              ? `${unscreened} not yet screened by the AI.`
              : "All applicants have been screened."
          }
        />
        {applications.length === 0 ? (
          <EmptyState
            title="No applications yet"
            hint="Candidates who apply will appear here, ready for AI screening."
          />
        ) : (
          <Table
            headers={[
              "Candidate",
              "Experience",
              "AI recommendation",
              "Match",
              "Confidence",
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
                    {application.candidate_location || "—"}
                  </p>
                </Td>
                <Td label="Experience" className="text-sm text-slate-600">
                  {application.candidate_years_experience != null
                    ? `${application.candidate_years_experience} yrs`
                    : "—"}
                </Td>
                <Td label="AI recommendation">
                  {application.screening ? (
                    <Badge
                      tone={RECOMMENDATION_TONE[application.screening.recommendation]}
                    >
                      {RECOMMENDATION_LABEL[application.screening.recommendation]}
                    </Badge>
                  ) : (
                    <span className="text-xs text-slate-400">Not screened</span>
                  )}
                </Td>
                <Td label="Match" className="text-sm tabular-nums text-slate-700">
                  {application.screening
                    ? pct(application.screening.overall_match)
                    : "—"}
                </Td>
                <Td label="Confidence" className="text-sm tabular-nums text-slate-500">
                  {application.screening
                    ? pct(application.screening.confidence)
                    : "—"}
                </Td>
                <Td label="Status">
                  <Badge tone={STATUS_TONE[application.status]}>
                    {STATUS_LABEL[application.status]}
                  </Badge>
                </Td>
                <Td label="">
                  <div className="flex flex-wrap gap-2">
                    {!application.screening ? (
                      <Button
                        size="sm"
                        onClick={() => runScreening(application.id)}
                        disabled={screening !== null}
                      >
                        {screening === application.id
                          ? "Screening…"
                          : "Run AI screening"}
                      </Button>
                    ) : null}
                    <Link href={`/recruiter/screening/${application.id}`}>
                      <Button size="sm" variant="secondary">
                        Candidate 360
                      </Button>
                    </Link>
                  </div>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>
    </div>
  );
}
