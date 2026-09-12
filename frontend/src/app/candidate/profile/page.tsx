"use client";

import { useEffect, useState } from "react";

import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Spinner,
  Textarea,
} from "@/components/ui";
import { api } from "@/lib/api";
import { parseList } from "@/lib/format";
import type { CandidateProfile, EducationItem, ProjectItem } from "@/lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [location, setLocation] = useState("");
  const [headline, setHeadline] = useState("");
  const [years, setYears] = useState("");
  const [skills, setSkills] = useState("");
  const [education, setEducation] = useState<EducationItem[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);

  useEffect(() => {
    api
      .getProfile()
      .then((data) => {
        setProfile(data);
        setFullName(data.full_name);
        setPhone(data.phone ?? "");
        setLocation(data.location ?? "");
        setHeadline(data.headline ?? "");
        setYears(data.years_experience?.toString() ?? "");
        setSkills((data.skills ?? []).join(", "));
        setEducation(data.education?.length ? data.education : []);
        setProjects(data.projects?.length ? data.projects : []);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const updated = await api.updateProfile({
        full_name: fullName,
        phone,
        location,
        headline,
        // Empty string must become null, not 0 — "not stated" and "zero years"
        // are different answers.
        years_experience: years === "" ? null : Number(years),
        skills: parseList(skills),
        education: education.filter((item) => item.degree?.trim()),
        projects: projects.filter((item) => item.name?.trim()),
      } as Partial<CandidateProfile>);
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <Spinner />;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Your profile"
        subtitle="Recruiters see this alongside your resume. It is also indexed for semantic job matching."
      />

      <form onSubmit={save} className="space-y-6">
        <Card>
          <CardHeader title="Basics" />
          <CardBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name">
              <Input value={fullName} onChange={setFullName} required />
            </Field>
            <Field label="Email">
              <Input
                value={profile?.email ?? ""}
                onChange={() => undefined}
                disabled
              />
            </Field>
            <Field label="Phone">
              <Input value={phone} onChange={setPhone} placeholder="+91 …" />
            </Field>
            <Field label="Location">
              <Input
                value={location}
                onChange={setLocation}
                placeholder="Bengaluru, India"
              />
            </Field>
            <Field label="Headline">
              <Input
                value={headline}
                onChange={setHeadline}
                placeholder="Senior Backend Engineer"
              />
            </Field>
            <Field label="Years of experience">
              <Input
                type="number"
                min="0"
                step="0.5"
                value={years}
                onChange={setYears}
              />
            </Field>
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Skills"
            subtitle="Comma-separated. These are matched against each job's requirements."
          />
          <CardBody>
            <Textarea
              value={skills}
              onChange={setSkills}
              rows={3}
              placeholder="Node.js, TypeScript, PostgreSQL, AWS, Docker"
            />
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Education"
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setEducation([
                    ...education,
                    { degree: "", institution: "", year: "" },
                  ])
                }
              >
                + Add
              </Button>
            }
          />
          <CardBody className="space-y-3">
            {education.length === 0 ? (
              <p className="text-sm text-slate-400">No education added yet.</p>
            ) : null}
            {education.map((item, index) => (
              <div key={index} className="grid gap-3 sm:grid-cols-[2fr_2fr_1fr_auto]">
                <Input
                  value={item.degree ?? ""}
                  onChange={(value) =>
                    setEducation(replaceAt(education, index, { ...item, degree: value }))
                  }
                  placeholder="B.Tech Computer Science"
                />
                <Input
                  value={item.institution ?? ""}
                  onChange={(value) =>
                    setEducation(
                      replaceAt(education, index, { ...item, institution: value }),
                    )
                  }
                  placeholder="Institution"
                />
                <Input
                  value={item.year ?? ""}
                  onChange={(value) =>
                    setEducation(replaceAt(education, index, { ...item, year: value }))
                  }
                  placeholder="2019"
                />
                <Button
                  variant="ghost"
                  size="sm"
                  className="mt-1 self-start"
                  onClick={() => setEducation(removeAt(education, index))}
                >
                  Remove
                </Button>
              </div>
            ))}
          </CardBody>
        </Card>

        <Card>
          <CardHeader
            title="Projects"
            action={
              <Button
                variant="secondary"
                size="sm"
                onClick={() =>
                  setProjects([
                    ...projects,
                    { name: "", description: "", technologies: [] },
                  ])
                }
              >
                + Add
              </Button>
            }
          />
          <CardBody className="space-y-4">
            {projects.length === 0 ? (
              <p className="text-sm text-slate-400">No projects added yet.</p>
            ) : null}
            {projects.map((item, index) => (
              <div key={index} className="space-y-2 rounded-lg bg-slate-50 p-3">
                <div className="flex gap-3">
                  <div className="flex-1">
                    <Input
                      value={item.name ?? ""}
                      onChange={(value) =>
                        setProjects(replaceAt(projects, index, { ...item, name: value }))
                      }
                      placeholder="Project name"
                    />
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-1 self-start"
                    onClick={() => setProjects(removeAt(projects, index))}
                  >
                    Remove
                  </Button>
                </div>
                <Textarea
                  value={item.description ?? ""}
                  onChange={(value) =>
                    setProjects(
                      replaceAt(projects, index, { ...item, description: value }),
                    )
                  }
                  rows={2}
                  placeholder="What it did, and what you built"
                />
                <Input
                  value={(item.technologies ?? []).join(", ")}
                  onChange={(value) =>
                    setProjects(
                      replaceAt(projects, index, {
                        ...item,
                        technologies: parseList(value),
                      }),
                    )
                  }
                  placeholder="Technologies, comma-separated"
                />
              </div>
            ))}
          </CardBody>
        </Card>

        {error ? <Alert tone="red">{error}</Alert> : null}
        {saved ? (
          <Alert tone="green">
            Profile saved and re-indexed for semantic matching.
          </Alert>
        ) : null}

        <Button type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </Button>
      </form>
    </div>
  );
}

function replaceAt<T>(items: T[], index: number, value: T): T[] {
  return items.map((item, i) => (i === index ? value : item));
}

function removeAt<T>(items: T[], index: number): T[] {
  return items.filter((_, i) => i !== index);
}
