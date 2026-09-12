/**
 * The single place the frontend talks to the backend.
 *
 * Every call goes through `request()`, so the bearer token, the JSON handling
 * and the error shape are defined once. A 401 clears the stored session and
 * bounces to /login — an expired token should not leave the UI stuck showing
 * empty panels.
 */
import type {
  AIStatus,
  Application,
  Candidate360,
  CandidateMetrics,
  CandidateProfile,
  Decision,
  Job,
  JobAnalysis,
  RecommendedJob,
  RecruiterMetrics,
  Resume,
  Review,
  Role,
  Screening,
  TokenResponse,
  User,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

const TOKEN_KEY = "air.token";
const USER_KEY = "air.user";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

// --- Session storage ---------------------------------------------------------
// localStorage, not a cookie: this is a learning project with a stateless JWT
// API and no SSR data fetching. A production build would want httpOnly cookies.

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: User): void {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

// --- Core request ------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit & { raw?: boolean } = {},
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (response.status === 401 && typeof window !== "undefined") {
    clearSession();
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Your session has expired. Please sign in again.");
  }

  if (!response.ok) {
    // FastAPI returns {detail: string} for our errors and {detail: [...]} for
    // request-validation failures; flatten both into one message.
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        message = body.detail
          .map((item: { loc?: string[]; msg?: string }) =>
            `${item.loc?.slice(1).join(".") ?? "field"}: ${item.msg ?? "invalid"}`,
          )
          .join("; ");
      }
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

// --- Auth --------------------------------------------------------------------

export const api = {
  register: (payload: {
    email: string;
    password: string;
    full_name: string;
    role: Role;
    company?: string;
  }) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me"),

  aiStatus: () => request<AIStatus>("/ai/status"),

  // --- Candidate -------------------------------------------------------------

  getProfile: () => request<CandidateProfile>("/candidates/me"),

  updateProfile: (payload: Partial<CandidateProfile>) =>
    request<CandidateProfile>("/candidates/me", {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  candidateMetrics: () => request<CandidateMetrics>("/candidates/me/metrics"),

  getResume: () => request<Resume>("/candidates/resume"),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Resume>("/candidates/resume", { method: "POST", body: form });
  },

  analyzeResume: () => request<Resume>("/ai/resume/analyze", { method: "POST" }),

  resumeFileUrl: () => `${API_URL}/candidates/resume/file`,

  recommendedJobs: () => request<RecommendedJob[]>("/candidates/recommended-jobs"),

  myApplications: () => request<Application[]>("/candidates/applications"),

  myApplication: (id: number) => request<Application>(`/candidates/applications/${id}`),

  // --- Jobs ------------------------------------------------------------------

  listJobs: (search = "") =>
    request<Job[]>(`/jobs${search ? `?search=${encodeURIComponent(search)}` : ""}`),

  getJob: (id: number) => request<Job>(`/jobs/${id}`),

  createJob: (payload: Record<string, unknown>) =>
    request<Job>("/jobs", { method: "POST", body: JSON.stringify(payload) }),

  updateJob: (id: number, payload: Record<string, unknown>) =>
    request<Job>(`/jobs/${id}`, { method: "PUT", body: JSON.stringify(payload) }),

  applyToJob: (id: number, coverNote: string) =>
    request<Application>(`/jobs/${id}/apply`, {
      method: "POST",
      body: JSON.stringify({ cover_note: coverNote || null }),
    }),

  jobApplications: (id: number) => request<Application[]>(`/jobs/${id}/applications`),

  analyzeJobText: (text: string) =>
    request<JobAnalysis>("/ai/job/analyze", {
      method: "POST",
      body: JSON.stringify({ text }),
    }),

  // --- Recruiter -------------------------------------------------------------

  recruiterMetrics: () => request<RecruiterMetrics>("/recruiter/metrics"),

  recruiterJobs: () => request<Job[]>("/recruiter/jobs"),

  recruiterApplications: (status?: string) =>
    request<Application[]>(
      `/recruiter/applications${status ? `?status=${status}` : ""}`,
    ),

  screeningQueue: () => request<Application[]>("/recruiter/screening-queue"),

  recruiterCandidates: () => request<CandidateProfile[]>("/recruiter/candidates"),

  candidate360: (applicationId: number) =>
    request<Candidate360>(`/applications/${applicationId}/candidate-360`),

  candidateResumeUrl: (candidateId: number) =>
    `${API_URL}/candidates/${candidateId}/resume/file`,

  // --- AI and HITL -----------------------------------------------------------

  screen: (applicationId: number, force = false) =>
    request<Screening>(`/ai/screen/${applicationId}`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),

  review: (applicationId: number, decision: Decision, comment: string) =>
    request<Review>(`/applications/${applicationId}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, comment: comment || null }),
    }),
};

/**
 * Fetch a protected file and open it.
 *
 * A plain <a href> cannot carry the Authorization header, so the file is
 * fetched as a blob and handed to the browser from an object URL.
 */
export async function openProtectedFile(url: string): Promise<void> {
  const token = getToken();
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new ApiError(response.status, "Could not open that file");
  }
  const blobUrl = URL.createObjectURL(await response.blob());
  window.open(blobUrl, "_blank", "noopener");
  // Revoking immediately would race the new tab; a minute is ample.
  setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}
