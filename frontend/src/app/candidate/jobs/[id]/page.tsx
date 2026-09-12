"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  CardHeader,
  PageHeader,
  SkillChips,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Job } from "@/lib/types";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [coverNote, setCoverNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getJob(jobId)
      .then(setJob)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [jobId]);

  async function apply() {
    setApplying(true);
    setError("");
    try {
      await api.applyToJob(jobId, coverNote);
      router.push("/candidate/applications");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply");
      setApplying(false);
    }
  }

  if (loading) return <Spinner />;
  if (!job) return <Alert tone="red">{error || "Job not found"}</Alert>;

  const analysis = job.jd_analysis;

  return (
    <div className="space-y-6">
      <PageHeader
        title={job.title}
        subtitle={`${job.company}${job.location ? ` · ${job.location}` : ""}${
          job.employment_type ? ` · ${job.employment_type}` : ""
        }`}
        action={
          <Link href="/candidate/jobs">
            <Button variant="secondary" size="sm">
              Back to jobs
            </Button>
          </Link>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader title="Job description" />
            <CardBody>
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">
                {job.description}
              </p>
            </CardBody>
          </Card>

          {analysis ? (
            <Card>
              <CardHeader
                title="AI job analysis"
                subtitle="Structured requirements extracted from the description by the Job Agent."
              />
              <CardBody className="space-y-4">
                {analysis.responsibilities?.length ? (
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

                <div>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Technologies
                  </p>
                  <SkillChips items={analysis.technologies} tone="green" />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Detail
                    label="Experience"
                    value={analysis.experience_requirement || "Not specified"}
                  />
                  <Detail
                    label="Education"
                    value={analysis.education_requirement || "Not required"}
                  />
                  <Detail label="Seniority" value={analysis.seniority || "—"} />
                </div>
              </CardBody>
            </Card>
          ) : null}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader title="Requirements" />
            <CardBody className="space-y-4">
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Required skills
                </p>
                <SkillChips items={job.required_skills} tone="blue" />
              </div>
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Preferred skills
                </p>
                <SkillChips items={job.preferred_skills} tone="slate" />
              </div>
              <Detail
                label="Experience required"
                value={
                  job.experience_required != null
                    ? `${job.experience_required}+ years`
                    : "Not specified"
                }
              />
              <Detail label="Posted" value={formatDate(job.created_at)} />
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Apply" />
            <CardBody className="space-y-3">
              {job.already_applied ? (
                <>
                  <Badge tone="green">You have applied to this job</Badge>
                  <Link href="/candidate/applications">
                    <Button variant="secondary" size="sm">
                      Track your application
                    </Button>
                  </Link>
                </>
              ) : (
                <>
                  <Textarea
                    value={coverNote}
                    onChange={setCoverNote}
                    rows={4}
                    placeholder="Optional: why you are a fit for this role."
                  />
                  {error ? <Alert tone="red">{error}</Alert> : null}
                  <Button onClick={apply} disabled={applying} className="w-full">
                    {applying ? "Applying…" : "Apply now"}
                  </Button>
                  <p className="text-xs text-slate-500">
                    You need an uploaded resume to apply — the recruiter&apos;s AI
                    screening reads it.
                  </p>
                </>
              )}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className="mt-0.5 text-sm text-slate-700">{value}</p>
    </div>
  );
}
