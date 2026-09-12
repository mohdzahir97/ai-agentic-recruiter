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
  Spinner,
  StatCard,
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
import type { Application } from "@/lib/types";

export default function ScreeningQueuePage() {
  const [queue, setQueue] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .screeningQueue()
      .then(setQueue)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function runScreening(applicationId: number) {
    setBusy(applicationId);
    setError("");
    try {
      await api.screen(applicationId);
      setQueue(await api.screeningQueue());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Screening failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Spinner />;

  const screened = queue.filter((item) => item.screening);
  const unscreened = queue.filter((item) => !item.screening);

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI screening"
        subtitle="The AI produces a score, an explanation and a recommendation. Every one of them still needs a human decision."
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Waiting on you" value={queue.length} tone={queue.length ? "amber" : "slate"} />
        <StatCard label="Screened, undecided" value={screened.length} tone="blue" />
        <StatCard label="Not yet screened" value={unscreened.length} />
      </div>

      {queue.length === 0 ? (
        <Card>
          <EmptyState
            title="The queue is empty"
            hint="Every application has a recorded human decision. New applications will appear here."
            action={
              <Link href="/recruiter/applications">
                <Button variant="secondary">View all applications</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-4">
          {queue.map((application) => (
            <Card key={application.id}>
              <CardHeader
                title={application.candidate_name}
                subtitle={`${application.job_title} · applied ${formatDate(application.created_at)}`}
                action={
                  <div className="flex items-center gap-2">
                    <Badge tone={STATUS_TONE[application.status]}>
                      {STATUS_LABEL[application.status]}
                    </Badge>
                    {!application.screening ? (
                      <Button
                        size="sm"
                        onClick={() => runScreening(application.id)}
                        disabled={busy !== null}
                      >
                        {busy === application.id ? "Screening…" : "Run AI screening"}
                      </Button>
                    ) : null}
                    <Link href={`/recruiter/screening/${application.id}`}>
                      <Button size="sm" variant="secondary">
                        Review
                      </Button>
                    </Link>
                  </div>
                }
              />
              {application.screening ? (
                <CardBody className="grid gap-5 sm:grid-cols-[1fr_1.4fr]">
                  <div className="space-y-3">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl font-semibold text-slate-900 tabular-nums">
                        {pct(application.screening.overall_match)}
                      </span>
                      <div>
                        <Badge
                          tone={RECOMMENDATION_TONE[application.screening.recommendation]}
                        >
                          {RECOMMENDATION_LABEL[application.screening.recommendation]}
                        </Badge>
                        <p className="mt-1 text-xs text-slate-500">
                          {pct(application.screening.confidence)} confidence
                        </p>
                      </div>
                    </div>
                    <ProgressBar
                      label="Skills"
                      value={application.screening.skills_match}
                    />
                    <ProgressBar
                      label="Experience"
                      value={application.screening.experience_match}
                    />
                    <ProgressBar
                      label="Technology"
                      value={application.screening.technology_match}
                    />
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm leading-relaxed text-slate-700">
                      {application.screening.explanation}
                    </p>
                    {application.screening.skill_gaps.length ? (
                      <div>
                        <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
                          Gaps
                        </p>
                        <ul className="space-y-0.5">
                          {application.screening.skill_gaps.slice(0, 3).map((gap) => (
                            <li key={gap} className="text-xs text-slate-600">
                              ⚠ {gap}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                  </div>
                </CardBody>
              ) : (
                <CardBody>
                  <p className="text-sm text-slate-500">
                    Not screened yet. Run the agent to get a match score, an
                    explanation and a recommendation for this candidate.
                  </p>
                </CardBody>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
