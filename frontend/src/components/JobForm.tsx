"use client";

/**
 * Shared create/edit form for a job.
 *
 * "Preview AI analysis" calls the Job Agent without saving, so a recruiter can
 * see what the system will extract from their description — and fix a vague
 * posting — before it becomes the basis for screening every applicant.
 */
import { useState } from "react";

import { api } from "@/lib/api";
import { parseList } from "@/lib/format";
import type { Job, JobAnalysis } from "@/lib/types";
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  Select,
  SkillChips,
  Textarea,
} from "./ui";

const EMPLOYMENT_TYPES = [
  { value: "Full-time", label: "Full-time" },
  { value: "Part-time", label: "Part-time" },
  { value: "Contract", label: "Contract" },
  { value: "Internship", label: "Internship" },
];

export interface JobFormValues {
  title: string;
  company: string;
  location: string;
  employment_type: string;
  experience_required: number | null;
  required_skills: string[];
  preferred_skills: string[];
  description: string;
  status?: "ACTIVE" | "CLOSED";
}

export function JobForm({
  initial,
  submitLabel,
  onSubmit,
  showStatus = false,
}: {
  initial?: Job | null;
  submitLabel: string;
  onSubmit: (values: JobFormValues) => Promise<void>;
  showStatus?: boolean;
}) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [company, setCompany] = useState(initial?.company ?? "");
  const [location, setLocation] = useState(initial?.location ?? "");
  const [employmentType, setEmploymentType] = useState(
    initial?.employment_type ?? "Full-time",
  );
  const [experience, setExperience] = useState(
    initial?.experience_required?.toString() ?? "",
  );
  const [required, setRequired] = useState(
    (initial?.required_skills ?? []).join(", "),
  );
  const [preferred, setPreferred] = useState(
    (initial?.preferred_skills ?? []).join(", "),
  );
  const [description, setDescription] = useState(initial?.description ?? "");
  const [status, setStatus] = useState<"ACTIVE" | "CLOSED">(
    initial?.status ?? "ACTIVE",
  );

  const [preview, setPreview] = useState<JobAnalysis | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handlePreview() {
    if (description.trim().length < 20) {
      setError("Write a description of at least 20 characters first.");
      return;
    }
    setPreviewing(true);
    setError("");
    try {
      setPreview(await api.analyzeJobText(description));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      await onSubmit({
        title,
        company,
        location,
        employment_type: employmentType,
        experience_required: experience === "" ? null : Number(experience),
        required_skills: parseList(required),
        preferred_skills: parseList(preferred),
        description,
        ...(showStatus ? { status } : {}),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the job");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Card>
        <CardHeader title="Job details" />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Job title">
            <Input
              value={title}
              onChange={setTitle}
              required
              placeholder="Senior Backend Engineer"
            />
          </Field>
          <Field label="Company">
            <Input value={company} onChange={setCompany} required />
          </Field>
          <Field label="Location">
            <Input
              value={location}
              onChange={setLocation}
              placeholder="Bengaluru, India / Remote"
            />
          </Field>
          <Field label="Employment type">
            <Select
              value={employmentType}
              onChange={setEmploymentType}
              options={EMPLOYMENT_TYPES}
            />
          </Field>
          <Field label="Experience required (years)">
            <Input
              type="number"
              min="0"
              step="0.5"
              value={experience}
              onChange={setExperience}
            />
          </Field>
          {showStatus ? (
            <Field label="Status">
              <Select
                value={status}
                onChange={(value) => setStatus(value as "ACTIVE" | "CLOSED")}
                options={[
                  { value: "ACTIVE", label: "Active — accepting applications" },
                  { value: "CLOSED", label: "Closed" },
                ]}
              />
            </Field>
          ) : null}
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Skills"
          subtitle="Comma-separated. Anything you enter here is always kept — the Job Agent may add to it, never replace it."
        />
        <CardBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Required skills">
            <Textarea
              value={required}
              onChange={setRequired}
              rows={2}
              placeholder="Node.js, TypeScript, PostgreSQL, AWS"
            />
          </Field>
          <Field label="Preferred skills">
            <Textarea
              value={preferred}
              onChange={setPreferred}
              rows={2}
              placeholder="Kubernetes, GraphQL"
            />
          </Field>
        </CardBody>
      </Card>

      <Card>
        <CardHeader
          title="Job description"
          subtitle="The Job Agent reads this to extract requirements, responsibilities and technologies."
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={handlePreview}
              disabled={previewing}
            >
              {previewing ? "Analysing…" : "Preview AI analysis"}
            </Button>
          }
        />
        <CardBody>
          <Textarea
            value={description}
            onChange={setDescription}
            rows={12}
            required
            placeholder={
              "We are hiring a Senior Backend Engineer…\n\nYou will:\n- …\n\nRequirements:\n- 5+ years of backend experience\n- …"
            }
          />
        </CardBody>
      </Card>

      {preview ? (
        <Card>
          <CardHeader
            title="AI analysis preview"
            subtitle="Not saved. This is what the Job Agent extracts from the text above."
          />
          <CardBody className="space-y-4">
            <PreviewRow label="Required skills">
              <SkillChips items={preview.required_skills} tone="blue" />
            </PreviewRow>
            <PreviewRow label="Preferred skills">
              <SkillChips items={preview.preferred_skills} tone="slate" />
            </PreviewRow>
            <PreviewRow label="Technologies">
              <SkillChips items={preview.technologies} tone="green" />
            </PreviewRow>
            <PreviewRow label="Experience">
              <span className="text-sm text-slate-700">
                {preview.experience_requirement || "Not specified"}
              </span>
            </PreviewRow>
            <PreviewRow label="Education">
              <span className="text-sm text-slate-700">
                {preview.education_requirement || "Not required"}
              </span>
            </PreviewRow>
            {preview.responsibilities.length ? (
              <PreviewRow label="Responsibilities">
                <ul className="space-y-1">
                  {preview.responsibilities.map((item) => (
                    <li key={item} className="text-sm text-slate-700">
                      · {item}
                    </li>
                  ))}
                </ul>
              </PreviewRow>
            ) : null}
          </CardBody>
        </Card>
      ) : null}

      {error ? <Alert tone="red">{error}</Alert> : null}

      <Button type="submit" disabled={submitting}>
        {submitting ? "Saving…" : submitLabel}
      </Button>
    </form>
  );
}

function PreviewRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
        {label}
      </p>
      {children}
    </div>
  );
}
