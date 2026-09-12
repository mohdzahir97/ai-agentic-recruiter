"use client";

import { useEffect, useRef, useState } from "react";

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
  StatCard,
} from "@/components/ui";
import { ApiError, api, openProtectedFile } from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { Resume } from "@/lib/types";

export default function ResumePage() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<"upload" | "analyze" | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api
      .getResume()
      .then(setResume)
      // A 404 here just means "no resume yet", which is a normal empty state
      // rather than an error worth showing.
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 404)) setError(err.message);
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy("upload");
    setError("");
    setNotice("");
    try {
      const uploaded = await api.uploadResume(file);
      setResume(uploaded);
      setNotice(
        `Uploaded and parsed ${uploaded.page_count} page(s). Run the AI analysis to extract your structured profile.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function handleAnalyze() {
    setBusy("analyze");
    setError("");
    setNotice("");
    try {
      const analyzed = await api.analyzeResume();
      setResume(analyzed);
      setNotice("Resume analysed. Empty profile fields were filled in from it.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setBusy(null);
    }
  }

  if (loading) return <Spinner />;

  const analysis = resume?.ai_analysis;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Resume"
        subtitle="Upload a PDF. The text is extracted, indexed for semantic search, and parsed by the Resume Agent."
        action={
          <>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf"
              onChange={handleUpload}
              className="hidden"
            />
            <Button
              onClick={() => fileInput.current?.click()}
              disabled={busy !== null}
            >
              {busy === "upload"
                ? "Uploading…"
                : resume
                  ? "Replace resume"
                  : "Upload resume"}
            </Button>
          </>
        }
      />

      {error ? <Alert tone="red">{error}</Alert> : null}
      {notice ? <Alert tone="green">{notice}</Alert> : null}

      {!resume ? (
        <Card>
          <EmptyState
            title="No resume uploaded"
            hint="A text-based PDF, up to 10 MB. Scanned images cannot be read — this MVP has no OCR."
            action={
              <Button onClick={() => fileInput.current?.click()}>
                Choose a PDF
              </Button>
            }
          />
        </Card>
      ) : (
        <>
          <Card>
            <CardHeader
              title={resume.filename}
              subtitle={`${formatBytes(resume.size_bytes)} · ${resume.page_count} page(s) · uploaded ${formatDateTime(resume.created_at)}`}
              action={
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      openProtectedFile(api.resumeFileUrl()).catch((err) =>
                        setError(err.message),
                      )
                    }
                  >
                    View PDF
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleAnalyze}
                    disabled={busy !== null}
                  >
                    {busy === "analyze"
                      ? "Analysing…"
                      : analysis
                        ? "Re-run AI analysis"
                        : "Run AI analysis"}
                  </Button>
                </div>
              }
            />
            <CardBody>
              <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                Extracted text (preview)
              </p>
              <pre className="max-h-56 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-xs leading-relaxed text-slate-600">
                {resume.text_preview || "No text preview available."}
              </pre>
            </CardBody>
          </Card>

          {!analysis ? (
            <Card>
              <EmptyState
                title="Not analysed yet"
                hint="Run the Resume Agent to turn this document into a structured profile of skills, technologies, experience and education."
                action={
                  <Button onClick={handleAnalyze} disabled={busy !== null}>
                    {busy === "analyze" ? "Analysing…" : "Run AI analysis"}
                  </Button>
                }
              />
            </Card>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-3">
                <StatCard
                  label="Experience found"
                  value={`${analysis.experience_years} yrs`}
                />
                <StatCard
                  label="Skills extracted"
                  value={analysis.skills.length + analysis.technologies.length}
                />
                <StatCard
                  label="Certifications"
                  value={analysis.certifications.length}
                />
              </div>

              <Card>
                <CardHeader
                  title="AI resume analysis"
                  subtitle="Structured JSON produced by the Resume Agent — not free-form text."
                  action={
                    <Badge tone={resume.analysis_model?.includes("fallback") ? "amber" : "green"}>
                      {resume.analysis_model}
                    </Badge>
                  }
                />
                <CardBody className="space-y-5">
                  {analysis.summary ? (
                    <p className="text-sm leading-relaxed text-slate-700">
                      {analysis.summary}
                    </p>
                  ) : null}

                  <Section title="Skills">
                    <SkillChips items={analysis.skills} tone="blue" />
                  </Section>
                  <Section title="Technologies">
                    <SkillChips items={analysis.technologies} tone="green" />
                  </Section>
                  <Section title="Education">
                    <List items={analysis.education} />
                  </Section>
                  <Section title="Projects">
                    <List items={analysis.projects} />
                  </Section>
                  <Section title="Certifications">
                    <List items={analysis.certifications} />
                  </Section>
                </CardBody>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
        {title}
      </p>
      {children}
    </div>
  );
}

function List({ items }: { items: string[] }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-400">None found</p>;
  }
  return (
    <ul className="space-y-1">
      {items.map((item) => (
        <li key={item} className="text-sm text-slate-700">
          · {item}
        </li>
      ))}
    </ul>
  );
}
