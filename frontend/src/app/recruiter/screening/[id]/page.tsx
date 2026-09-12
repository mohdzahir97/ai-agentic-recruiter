"use client";

/**
 * Candidate 360 — the recruiter's screening page.
 *
 * Reading order is deliberate and matches spec section 10: who the candidate
 * is, what their resume says, what the AI found, how sure it is, and only then
 * the decision controls. The AI's conclusion never appears without its
 * confidence and its evidence next to it.
 */
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AIExplanation, AgentTrace, DecisionHistory, HitlPanel, MatchBreakdown } from "@/components/ai";
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
} from "@/components/ui";
import { api, openProtectedFile } from "@/lib/api";
import { STATUS_LABEL, STATUS_TONE, formatDate, pct } from "@/lib/format";
import type { Candidate360, Decision } from "@/lib/types";

export default function Candidate360Page() {
  const params = useParams<{ id: string }>();
  const applicationId = Number(params.id);

  const [data, setData] = useState<Candidate360 | null>(null);
  const [loading, setLoading] = useState(true);
  const [screening, setScreening] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [reviewError, setReviewError] = useState("");

  const load = useCallback(async () => {
    try {
      setData(await api.candidate360(applicationId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load");
    } finally {
      setLoading(false);
    }
  }, [applicationId]);

  useEffect(() => {
    load();
  }, [load]);

  async function runScreening(force: boolean) {
    setScreening(true);
    setError("");
    try {
      await api.screen(applicationId, force);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Screening failed");
    } finally {
      setScreening(false);
    }
  }

  async function submitDecision(decision: Decision, comment: string) {
    setSubmitting(true);
    setReviewError("");
    try {
      await api.review(applicationId, decision, comment);
      await load();
    } catch (err) {
      setReviewError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <Spinner />;
  if (!data) return <Alert tone="red">{error || "Not found"}</Alert>;

  const { application, candidate, job, resume, screening: result, reviews } = data;
  const analysis = resume?.ai_analysis;

  return (
    <div className="space-y-6">
      <PageHeader
        title={candidate.full_name}
        subtitle={`Applied to ${job.title} at ${job.company} on ${formatDate(application.created_at)}`}
        action={
          <div className="flex flex-wrap gap-2">
            <Link href="/recruiter/screening">
              <Button variant="secondary" size="sm">
                Back to queue
              </Button>
            </Link>
            {result ? (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => runScreening(true)}
                disabled={screening}
              >
                {screening ? "Re-screening…" : "Re-run AI screening"}
              </Button>
            ) : null}
          </div>
        }
      />

      {error ? <Alert tone="red">{error}</Alert> : null}

      <div className="flex flex-wrap items-center gap-3">
        <Badge tone={STATUS_TONE[application.status]}>
          {STATUS_LABEL[application.status]}
        </Badge>
        {application.review ? (
          <span className="text-xs text-slate-500">
            Decided by a human · {application.review.decision}
          </span>
        ) : (
          <span className="text-xs text-amber-600">Awaiting a human decision</span>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* --- Left column: who the candidate is ------------------------- */}
        <div className="space-y-6">
          <Card>
            <CardHeader title="Candidate information" />
            <CardBody className="space-y-3 text-sm">
              <Detail label="Name" value={candidate.full_name} />
              <Detail label="Email" value={candidate.email} />
              <Detail label="Phone" value={candidate.phone || "—"} />
              <Detail label="Location" value={candidate.location || "—"} />
              <Detail label="Headline" value={candidate.headline || "—"} />
              <Detail
                label="Experience"
                value={
                  candidate.years_experience != null
                    ? `${candidate.years_experience} years`
                    : "—"
                }
              />
              {application.cover_note ? (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    Cover note
                  </p>
                  <p className="mt-1 border-l-2 border-slate-200 pl-2 text-sm italic text-slate-600">
                    {application.cover_note}
                  </p>
                </div>
              ) : null}
            </CardBody>
          </Card>

          <Card>
            <CardHeader
              title="Resume"
              action={
                resume ? (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      openProtectedFile(api.candidateResumeUrl(candidate.id)).catch(
                        (err) => setError(err.message),
                      )
                    }
                  >
                    View PDF
                  </Button>
                ) : null
              }
            />
            <CardBody>
              {!resume ? (
                <p className="text-sm text-slate-400">No resume on file.</p>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-slate-700">{resume.filename}</p>
                  <p className="text-xs text-slate-500">
                    {resume.page_count} page(s) · uploaded{" "}
                    {formatDate(resume.created_at)}
                  </p>
                  <pre className="max-h-44 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                    {resume.text_preview}
                  </pre>
                </div>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Skills and experience" />
            <CardBody className="space-y-4">
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Profile skills
                </p>
                <SkillChips items={candidate.skills} tone="blue" />
              </div>
              {analysis ? (
                <>
                  <div>
                    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                      AI-extracted technologies
                    </p>
                    <SkillChips items={analysis.technologies} tone="green" />
                  </div>
                  <div>
                    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                      Education
                    </p>
                    {analysis.education.length ? (
                      <ul className="space-y-1">
                        {analysis.education.map((item) => (
                          <li key={item} className="text-sm text-slate-700">
                            · {item}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-sm text-slate-400">None found</p>
                    )}
                  </div>
                  {analysis.certifications.length ? (
                    <div>
                      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                        Certifications
                      </p>
                      <SkillChips items={analysis.certifications} tone="slate" />
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="text-xs text-slate-400">
                  This candidate has not run the AI resume analysis.
                </p>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Job requirements" />
            <CardBody className="space-y-3">
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Required
                </p>
                <SkillChips items={job.required_skills} tone="blue" />
              </div>
              <div>
                <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                  Preferred
                </p>
                <SkillChips items={job.preferred_skills} tone="slate" />
              </div>
            </CardBody>
          </Card>
        </div>

        {/* --- Right column: what the AI found, then the decision -------- */}
        <div className="space-y-6 lg:col-span-2">
          {!result ? (
            <Card>
              <EmptyState
                title="Not screened yet"
                hint="Run the screening agent: it analyses the job, retrieves the most relevant parts of this candidate's documents, compares them and explains its reasoning."
                action={
                  <Button onClick={() => runScreening(false)} disabled={screening}>
                    {screening ? "Screening…" : "Run AI screening"}
                  </Button>
                }
              />
            </Card>
          ) : (
            <>
              <Card>
                <CardHeader
                  title="AI match score"
                  subtitle="A recommendation from the matching agent. It does not decide anything."
                  action={
                    <Badge
                      tone={result.model_used.includes("fallback") ? "amber" : "green"}
                    >
                      {result.model_used}
                    </Badge>
                  }
                />
                <CardBody>
                  <MatchBreakdown screening={result} />
                </CardBody>
              </Card>

              <Card>
                <CardHeader
                  title="AI analysis"
                  subtitle={`Confidence ${pct(result.confidence)} — how much the evidence supports this, not how good the candidate is.`}
                />
                <CardBody className="space-y-5">
                  <AIExplanation screening={result} />
                  <AgentTrace screening={result} />
                </CardBody>
              </Card>
            </>
          )}

          <HitlPanel
            screening={result ?? null}
            onSubmit={submitDecision}
            submitting={submitting}
            error={reviewError}
          />

          <DecisionHistory reviews={reviews} />
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
