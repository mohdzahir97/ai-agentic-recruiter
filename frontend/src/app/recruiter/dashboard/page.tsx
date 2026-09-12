"use client";

import Link from "next/link";
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
  Spinner,
  StatCard,
  Table,
  Td,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  RECOMMENDATION_LABEL,
  RECOMMENDATION_TONE,
  STATUS_LABEL,
  STATUS_TONE,
  formatDate,
  pct,
} from "@/lib/format";
import type { Application, Job, RecruiterMetrics } from "@/lib/types";

export default function RecruiterDashboard() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<RecruiterMetrics | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [queue, setQueue] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.recruiterMetrics(), api.recruiterJobs(), api.screeningQueue()])
      .then(([m, j, q]) => {
        setMetrics(m);
        setJobs(j);
        setQueue(q);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;
  if (error) return <Alert tone="red">{error}</Alert>;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Welcome, ${user?.full_name?.split(" ")[0] ?? "there"}`}
        subtitle="Your jobs, applications and the reviews waiting on you."
        action={
          <Link href="/recruiter/jobs/new">
            <Button>+ Create job</Button>
          </Link>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard label="Total jobs" value={metrics?.total_jobs ?? 0} />
        <StatCard
          label="Active jobs"
          value={metrics?.active_jobs ?? 0}
          tone="green"
        />
        <StatCard
          label="Applications"
          value={metrics?.total_applications ?? 0}
        />
        <StatCard
          label="To review"
          value={metrics?.candidates_to_review ?? 0}
          tone={metrics?.candidates_to_review ? "amber" : "slate"}
        />
        <StatCard
          label="Shortlisted"
          value={metrics?.shortlisted_candidates ?? 0}
          tone="green"
        />
      </div>

      {metrics && metrics.pending_hitl_reviews > 0 ? (
        <Alert tone="amber">
          <span className="font-medium">
            {metrics.pending_hitl_reviews} screened{" "}
            {metrics.pending_hitl_reviews === 1 ? "candidate is" : "candidates are"}{" "}
            waiting on your decision.
          </span>{" "}
          The AI has produced a recommendation; nothing moves forward until a
          human decides.{" "}
          <Link
            href="/recruiter/screening"
            className="font-medium underline underline-offset-2"
          >
            Review now
          </Link>
        </Alert>
      ) : null}

      <Card>
        <CardHeader
          title="AI screening queue"
          subtitle="Screened candidates first, ranked by match. Unscreened ones below."
          action={
            <Link href="/recruiter/screening">
              <Button variant="secondary" size="sm">
                Open queue
              </Button>
            </Link>
          }
        />
        {queue.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            hint="Every application has a human decision recorded against it."
          />
        ) : (
          <Table headers={["Candidate", "Job", "AI recommendation", "Match", "Status", ""]}>
            {queue.slice(0, 8).map((application) => (
              <tr key={application.id} className="hover:bg-slate-50">
                <Td label="Candidate">
                  <p className="text-sm font-medium text-slate-900">
                    {application.candidate_name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {application.candidate_location || "—"}
                  </p>
                </Td>
                <Td label="Job" className="text-sm text-slate-600">{application.job_title}</Td>
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
                <Td label="Status">
                  <Badge tone={STATUS_TONE[application.status]}>
                    {STATUS_LABEL[application.status]}
                  </Badge>
                </Td>
                <Td label="">
                  <Link href={`/recruiter/screening/${application.id}`}>
                    <Button size="sm" variant="secondary">
                      Review
                    </Button>
                  </Link>
                </Td>
              </tr>
            ))}
          </Table>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Your jobs"
          action={
            <Link href="/recruiter/jobs">
              <Button variant="secondary" size="sm">
                View all
              </Button>
            </Link>
          }
        />
        {jobs.length === 0 ? (
          <EmptyState
            title="No jobs posted"
            hint="Create a job and the Job Agent will extract its structured requirements automatically."
            action={
              <Link href="/recruiter/jobs/new">
                <Button>Create your first job</Button>
              </Link>
            }
          />
        ) : (
          <CardBody className="space-y-2">
            {jobs.slice(0, 5).map((job) => (
              <Link
                key={job.id}
                href={`/recruiter/jobs/${job.id}`}
                className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2.5 hover:bg-slate-100"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {job.title}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {job.location || "—"} · posted {formatDate(job.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Badge tone={job.status === "ACTIVE" ? "green" : "slate"}>
                    {job.status}
                  </Badge>
                  <span className="text-xs text-slate-500">
                    {job.application_count} applicant
                    {job.application_count === 1 ? "" : "s"}
                  </span>
                </div>
              </Link>
            ))}
          </CardBody>
        )}
      </Card>
    </div>
  );
}
