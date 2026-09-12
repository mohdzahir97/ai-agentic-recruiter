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
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Job } from "@/lib/types";

export default function RecruiterJobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .recruiterJobs()
      .then(setJobs)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        subtitle="Every posting you own, with its application count."
        action={
          <Link href="/recruiter/jobs/new">
            <Button>+ Create job</Button>
          </Link>
        }
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      <Card>
        <CardHeader title={`${jobs.length} job${jobs.length === 1 ? "" : "s"}`} />
        {jobs.length === 0 ? (
          <EmptyState
            title="No jobs yet"
            hint="Create one and the Job Agent will break the description into structured requirements."
            action={
              <Link href="/recruiter/jobs/new">
                <Button>Create job</Button>
              </Link>
            }
          />
        ) : (
          <Table
            headers={[
              "Title",
              "Location",
              "Applicants",
              "AI analysis",
              "Status",
              "Posted",
              "",
            ]}
          >
            {jobs.map((job) => (
              <tr key={job.id} className="hover:bg-slate-50">
                <Td label="Title">
                  <Link
                    href={`/recruiter/jobs/${job.id}`}
                    className="text-sm font-medium text-slate-900 hover:underline"
                  >
                    {job.title}
                  </Link>
                  <p className="text-xs text-slate-500">{job.company}</p>
                </Td>
                <Td label="Location" className="text-sm text-slate-600">{job.location || "—"}</Td>
                <Td label="Applicants" className="text-sm tabular-nums text-slate-700">
                  {job.application_count}
                </Td>
                <Td label="AI analysis">
                  <Badge tone={job.jd_analysis ? "green" : "slate"}>
                    {job.jd_analysis ? "Analysed" : "Not analysed"}
                  </Badge>
                </Td>
                <Td label="Status">
                  <Badge tone={job.status === "ACTIVE" ? "green" : "slate"}>
                    {job.status}
                  </Badge>
                </Td>
                <Td label="Posted" className="text-sm text-slate-500">
                  {formatDate(job.created_at)}
                </Td>
                <Td label="">
                  <div className="flex flex-wrap gap-2">
                    <Link href={`/recruiter/jobs/${job.id}`}>
                      <Button size="sm" variant="secondary">
                        View
                      </Button>
                    </Link>
                    <Link href={`/recruiter/jobs/${job.id}/edit`}>
                      <Button size="sm" variant="ghost">
                        Edit
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
