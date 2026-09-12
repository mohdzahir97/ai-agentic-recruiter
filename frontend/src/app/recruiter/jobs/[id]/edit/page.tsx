"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { JobForm, type JobFormValues } from "@/components/JobForm";
import { Alert, Button, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { Job } from "@/lib/types";

export default function EditJobPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const jobId = Number(params.id);

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getJob(jobId)
      .then(setJob)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [jobId]);

  async function save(values: JobFormValues) {
    await api.updateJob(jobId, values as unknown as Record<string, unknown>);
    router.push(`/recruiter/jobs/${jobId}`);
  }

  if (loading) return <Spinner />;
  if (!job) return <Alert tone="red">{error || "Job not found"}</Alert>;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Edit job"
        subtitle="Changing the description or skills re-runs the Job Agent and re-indexes the posting."
        action={
          <Link href={`/recruiter/jobs/${jobId}`}>
            <Button variant="secondary" size="sm">
              Cancel
            </Button>
          </Link>
        }
      />
      <JobForm initial={job} submitLabel="Save changes" onSubmit={save} showStatus />
    </div>
  );
}
