"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  Alert,
  Badge,
  Button,
  Card,
  CardBody,
  EmptyState,
  Input,
  PageHeader,
  SkillChips,
  Spinner,
} from "@/components/ui";
import { api } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Job } from "@/lib/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Debounced so typing does not fire a request per keystroke.
    const timer = setTimeout(() => {
      setLoading(true);
      api
        .listJobs(search)
        .then(setJobs)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Open jobs"
        subtitle="Every active posting. Your dashboard ranks these by semantic fit."
      />

      <div className="max-w-sm">
        <Input
          value={search}
          onChange={setSearch}
          placeholder="Search by title, company or location"
        />
      </div>

      {error ? <Alert tone="red">{error}</Alert> : null}

      {loading ? (
        <Spinner />
      ) : jobs.length === 0 ? (
        <Card>
          <EmptyState
            title="No jobs found"
            hint={
              search
                ? "Try a different search term."
                : "No recruiter has posted a job yet."
            }
          />
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {jobs.map((job) => (
            <Card key={job.id}>
              <CardBody className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h3 className="truncate text-sm font-semibold text-slate-900">
                      {job.title}
                    </h3>
                    <p className="truncate text-xs text-slate-500">
                      {job.company}
                      {job.location ? ` · ${job.location}` : ""}
                    </p>
                  </div>
                  {job.already_applied ? (
                    <Badge tone="green">Applied</Badge>
                  ) : null}
                </div>

                <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                  {job.employment_type ? (
                    <span>{job.employment_type}</span>
                  ) : null}
                  {job.experience_required != null ? (
                    <span>· {job.experience_required}+ yrs</span>
                  ) : null}
                  <span>· posted {formatDate(job.created_at)}</span>
                </div>

                <SkillChips items={job.required_skills} tone="blue" max={5} />

                <p className="line-clamp-2 text-xs text-slate-500">
                  {job.description}
                </p>

                <Link href={`/candidate/jobs/${job.id}`}>
                  <Button variant="secondary" size="sm">
                    View details
                  </Button>
                </Link>
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
