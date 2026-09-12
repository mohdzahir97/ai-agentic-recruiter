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
  ProgressBar,
  SkillChips,
  Spinner,
  StatCard,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { STATUS_LABEL, STATUS_TONE, formatDate } from "@/lib/format";
import type {
  Application,
  CandidateMetrics,
  CandidateProfile,
  RecommendedJob,
} from "@/lib/types";

export default function CandidateDashboard() {
  const { user } = useAuth();
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [metrics, setMetrics] = useState<CandidateMetrics | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [recommended, setRecommended] = useState<RecommendedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // One pass so the whole dashboard appears at once rather than in stages.
    Promise.all([
      api.getProfile(),
      api.candidateMetrics(),
      api.myApplications(),
      api.recommendedJobs().catch(() => [] as RecommendedJob[]),
    ])
      .then(([p, m, a, r]) => {
        setProfile(p);
        setMetrics(m);
        setApplications(a);
        setRecommended(r);
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
        subtitle="Your profile, resume analysis, matching jobs and application status."
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Applications" value={metrics?.total_applications ?? 0} />
        <StatCard
          label="In screening"
          value={metrics?.in_screening ?? 0}
          tone="blue"
        />
        <StatCard
          label="Shortlisted"
          value={metrics?.shortlisted ?? 0}
          tone="green"
        />
        <StatCard
          label="Not selected"
          value={metrics?.rejected ?? 0}
          tone={metrics?.rejected ? "red" : "slate"}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader
            title="Your profile"
            action={
              <Link href="/candidate/profile">
                <Button variant="secondary" size="sm">
                  Edit
                </Button>
              </Link>
            }
          />
          <CardBody className="space-y-4">
            <div>
              <p className="text-sm font-medium text-slate-900">
                {profile?.full_name}
              </p>
              <p className="text-xs text-slate-500">
                {profile?.headline || "No headline yet"}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {profile?.location || "Location not set"}
                {profile?.years_experience != null
                  ? ` · ${profile.years_experience} yrs experience`
                  : ""}
              </p>
            </div>

            <ProgressBar
              label="Profile completeness"
              value={metrics?.profile_completeness ?? 0}
            />

            <div>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                Skills
              </p>
              <SkillChips
                items={profile?.skills ?? []}
                max={10}
                empty="Add skills, or upload a resume and let the AI extract them."
              />
            </div>
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Resume and AI analysis"
            action={
              <Link href="/candidate/resume">
                <Button variant="secondary" size="sm">
                  Manage
                </Button>
              </Link>
            }
          />
          <CardBody>
            {!metrics?.has_resume ? (
              <EmptyState
                title="No resume uploaded"
                hint="Upload a PDF to unlock AI analysis, job recommendations and applying."
                action={
                  <Link href="/candidate/resume">
                    <Button>Upload resume</Button>
                  </Link>
                }
              />
            ) : !metrics.resume_analyzed ? (
              <EmptyState
                title="Resume uploaded, not yet analysed"
                hint="Run the Resume Agent to extract your skills, technologies, experience and education."
                action={
                  <Link href="/candidate/resume">
                    <Button>Run AI analysis</Button>
                  </Link>
                }
              />
            ) : (
              <div className="space-y-3">
                <Badge tone="green">Analysed by the Resume Agent</Badge>
                <p className="text-sm text-slate-600">
                  Your resume has been parsed into a structured profile. It is
                  used to match you against jobs and shown to recruiters you
                  apply to.
                </p>
                <Link href="/candidate/resume">
                  <Button variant="secondary" size="sm">
                    View the extracted profile
                  </Button>
                </Link>
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader
          title="Recommended for you"
          subtitle="Semantic search over open jobs, using your profile and resume as the query."
          action={
            <Link href="/candidate/jobs">
              <Button variant="secondary" size="sm">
                Browse all jobs
              </Button>
            </Link>
          }
        />
        {recommended.length === 0 ? (
          <EmptyState
            title="No recommendations yet"
            hint="Complete your profile and upload a resume, and jobs will appear here."
          />
        ) : (
          <CardBody className="grid gap-3 sm:grid-cols-2">
            {recommended.map((job) => (
              <Link
                key={job.id}
                href={`/candidate/jobs/${job.id}`}
                className="block rounded-lg border border-slate-200 px-4 py-3 transition-colors hover:border-slate-300 hover:bg-slate-50"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-900">
                      {job.title}
                    </p>
                    <p className="truncate text-xs text-slate-500">
                      {job.company}
                      {job.location ? ` · ${job.location}` : ""}
                    </p>
                  </div>
                  {job.relevance > 0 ? (
                    <Badge tone="blue">{job.relevance.toFixed(0)}% match</Badge>
                  ) : null}
                </div>
                <p className="mt-2 text-xs text-slate-500">{job.reason}</p>
                {job.already_applied ? (
                  <span className="mt-2 inline-block text-xs text-emerald-600">
                    ✓ Applied
                  </span>
                ) : null}
              </Link>
            ))}
          </CardBody>
        )}
      </Card>

      <Card>
        <CardHeader
          title="Recent applications"
          action={
            <Link href="/candidate/applications">
              <Button variant="secondary" size="sm">
                View all
              </Button>
            </Link>
          }
        />
        {applications.length === 0 ? (
          <EmptyState
            title="You have not applied to anything yet"
            hint="Browse open jobs and apply — you will be able to track each application here."
          />
        ) : (
          <CardBody className="space-y-2">
            {applications.slice(0, 5).map((application) => (
              <div
                key={application.id}
                className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {application.job_title}
                  </p>
                  <p className="truncate text-xs text-slate-500">
                    {application.company} · applied{" "}
                    {formatDate(application.created_at)}
                  </p>
                </div>
                <Badge tone={STATUS_TONE[application.status]}>
                  {STATUS_LABEL[application.status]}
                </Badge>
              </div>
            ))}
          </CardBody>
        )}
      </Card>
    </div>
  );
}
