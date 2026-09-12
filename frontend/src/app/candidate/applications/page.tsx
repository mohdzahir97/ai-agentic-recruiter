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
  Table,
  Td,
  cx,
} from "@/components/ui";
import { api } from "@/lib/api";
import { STATUS_LABEL, STATUS_TONE, formatDate } from "@/lib/format";
import type { Application, ApplicationStatus } from "@/lib/types";

// The lifecycle as the candidate sees it. ON_HOLD and REJECTED are ends, not
// steps, so they are rendered as a terminal marker rather than a stage.
const STAGES: ApplicationStatus[] = ["APPLIED", "SCREENING", "SHORTLISTED"];

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .myApplications()
      .then(setApplications)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="My applications"
        subtitle="Track where each application stands."
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      {applications.length === 0 ? (
        <Card>
          <EmptyState
            title="No applications yet"
            hint="Browse open jobs and apply to start tracking them here."
            action={
              <Link href="/candidate/jobs">
                <Button>Browse jobs</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader title="All applications" />
            <Table headers={["Job", "Company", "Applied", "Status"]}>
              {applications.map((application) => (
                <tr key={application.id} className="hover:bg-slate-50">
                  <Td label="Job">
                    <Link
                      href={`/candidate/jobs/${application.job_id}`}
                      className="text-sm font-medium text-slate-900 hover:underline"
                    >
                      {application.job_title}
                    </Link>
                  </Td>
                  <Td label="Company" className="text-sm text-slate-600">
                    {application.company}
                  </Td>
                  <Td label="Applied" className="text-sm text-slate-500">
                    {formatDate(application.created_at)}
                  </Td>
                  <Td label="Status">
                    <Badge tone={STATUS_TONE[application.status]}>
                      {STATUS_LABEL[application.status]}
                    </Badge>
                  </Td>
                </tr>
              ))}
            </Table>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2">
            {applications.map((application) => (
              <Card key={application.id}>
                <CardBody className="space-y-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      {application.job_title}
                    </p>
                    <p className="text-xs text-slate-500">
                      {application.company}
                    </p>
                  </div>
                  <StatusTrack status={application.status} />
                  {application.cover_note ? (
                    <p className="border-l-2 border-slate-200 pl-2 text-xs italic text-slate-500">
                      {application.cover_note}
                    </p>
                  ) : null}
                </CardBody>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function StatusTrack({ status }: { status: ApplicationStatus }) {
  if (status === "REJECTED" || status === "ON_HOLD") {
    return (
      <div className="space-y-1.5">
        <div className="flex items-center gap-2">
          <Badge tone={STATUS_TONE[status]}>{STATUS_LABEL[status]}</Badge>
        </div>
        <p className="text-xs text-slate-500">
          {status === "REJECTED"
            ? "A recruiter reviewed your application and did not move it forward."
            : "A recruiter has put your application on hold for now."}
        </p>
      </div>
    );
  }

  const reached = STAGES.indexOf(status);
  return (
    <div className="flex items-center gap-1">
      {STAGES.map((stage, index) => (
        <div key={stage} className="flex flex-1 items-center gap-1">
          <div className="flex-1">
            <div
              className={cx(
                "h-1.5 rounded-full",
                index <= reached ? "bg-emerald-500" : "bg-slate-200",
              )}
            />
            <p
              className={cx(
                "mt-1 text-[10px]",
                index <= reached ? "text-slate-700" : "text-slate-400",
              )}
            >
              {STATUS_LABEL[stage]}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
