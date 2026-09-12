"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { JobForm, type JobFormValues } from "@/components/JobForm";
import { Alert, Button, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";

export default function NewJobPage() {
  const router = useRouter();

  async function create(values: JobFormValues) {
    const job = await api.createJob(values as unknown as Record<string, unknown>);
    router.push(`/recruiter/jobs/${job.id}`);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Create a job"
        subtitle="Saving runs the Job Agent, which extracts structured requirements and indexes the posting for semantic matching."
        action={
          <Link href="/recruiter/jobs">
            <Button variant="secondary" size="sm">
              Cancel
            </Button>
          </Link>
        }
      />
      <Alert tone="blue">
        Creating a job calls the AI once. If no LLM is configured, a rule-based
        extractor runs instead and the job is marked accordingly.
      </Alert>
      <JobForm submitLabel="Create job" onSubmit={create} />
    </div>
  );
}
