/**
 * Mirrors of the backend's Pydantic schemas.
 *
 * Kept hand-written rather than generated: it is a short list, and having it
 * here makes the API contract readable next to the components that consume it.
 */

export type Role = "CANDIDATE" | "RECRUITER";

export type ApplicationStatus =
  | "APPLIED"
  | "SCREENING"
  | "SHORTLISTED"
  | "ON_HOLD"
  | "REJECTED";

export type Recommendation =
  | "STRONG_MATCH"
  | "GOOD_MATCH"
  | "PARTIAL_MATCH"
  | "WEAK_MATCH";

export type Decision = "SHORTLIST" | "HOLD" | "REJECT";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface EducationItem {
  degree?: string;
  institution?: string;
  year?: string;
}

export interface ProjectItem {
  name?: string;
  description?: string;
  technologies?: string[];
}

export interface CandidateProfile {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  phone?: string | null;
  location?: string | null;
  headline?: string | null;
  years_experience?: number | null;
  skills: string[];
  education: EducationItem[];
  projects: ProjectItem[];
  has_resume: boolean;
  resume_analyzed: boolean;
}

export interface ResumeAnalysis {
  skills: string[];
  technologies: string[];
  experience_years: number;
  education: string[];
  projects: string[];
  certifications: string[];
  summary: string;
  current_title: string;
  location: string;
}

export interface Resume {
  id: number;
  candidate_id: number;
  filename: string;
  size_bytes: number;
  page_count: number;
  content_type: string;
  created_at: string;
  analyzed_at?: string | null;
  analysis_model?: string | null;
  ai_analysis?: ResumeAnalysis | null;
  text_preview?: string | null;
}

export interface JobAnalysis {
  required_skills: string[];
  preferred_skills: string[];
  technologies: string[];
  experience_requirement: string;
  minimum_years: number;
  education_requirement: string;
  responsibilities: string[];
  seniority: string;
}

export interface Job {
  id: number;
  title: string;
  company: string;
  location?: string | null;
  employment_type?: string | null;
  experience_required?: number | null;
  required_skills: string[];
  preferred_skills: string[];
  description: string;
  status: "ACTIVE" | "CLOSED";
  created_at: string;
  jd_analysis?: JobAnalysis | null;
  analyzed_at?: string | null;
  application_count: number;
  already_applied: boolean;
}

export interface RecommendedJob extends Job {
  relevance: number;
  reason: string;
}

export interface Evidence {
  claim: string;
  source: string;
  quote: string;
}

export interface RetrievedChunk {
  source: string;
  score: number;
  text: string;
}

export interface TraceStep {
  step: string;
  detail: string;
  [key: string]: unknown;
}

export interface Screening {
  id: number;
  application_id: number;
  skills_match: number;
  experience_match: number;
  technology_match: number;
  education_match: number;
  semantic_match: number;
  overall_match: number;
  confidence: number;
  recommendation: Recommendation;
  strengths: string[];
  skill_gaps: string[];
  explanation: string;
  evidence: Evidence[];
  retrieved_context: RetrievedChunk[];
  agent_trace: TraceStep[];
  model_used: string;
  safety_notes: string[];
  created_at: string;
}

export interface Review {
  id: number;
  application_id: number;
  reviewer_user_id: number;
  reviewer_name?: string | null;
  ai_recommendation?: Recommendation | null;
  ai_score?: number | null;
  ai_confidence?: number | null;
  decision: Decision;
  comment?: string | null;
  overrode_ai: boolean;
  created_at: string;
}

export interface Application {
  id: number;
  status: ApplicationStatus;
  cover_note?: string | null;
  created_at: string;
  updated_at: string;
  job_id: number;
  job_title: string;
  company: string;
  location?: string | null;
  candidate_id: number;
  candidate_name: string;
  candidate_email?: string | null;
  candidate_location?: string | null;
  candidate_years_experience?: number | null;
  candidate_skills: string[];
  has_resume: boolean;
  screening?: Screening | null;
  review?: Review | null;
}

export interface Candidate360 {
  application: Application;
  job: Job & { jd_analysis?: JobAnalysis | null };
  candidate: CandidateProfile;
  resume?: Resume | null;
  screening?: Screening | null;
  reviews: Review[];
}

export interface RecruiterMetrics {
  total_jobs: number;
  active_jobs: number;
  total_applications: number;
  candidates_to_review: number;
  shortlisted_candidates: number;
  pending_hitl_reviews: number;
}

export interface CandidateMetrics {
  total_applications: number;
  in_screening: number;
  shortlisted: number;
  rejected: number;
  profile_completeness: number;
  has_resume: boolean;
  resume_analyzed: boolean;
}

export interface AIStatus {
  llm_available: boolean;
  llm: string;
  embeddings: string;
  using_fallback: boolean;
  retrieval_top_k: number;
  chunk_size: number;
  vector_store: Record<string, number | string>;
}
