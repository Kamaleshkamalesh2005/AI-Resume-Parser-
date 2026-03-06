/* ── API Response Envelope ─────────────────────────────────────────── */

export interface ApiEnvelope<T = unknown> {
  success: boolean;
  data: T;
  errors: string[];
  meta: { latency_ms: number };
}

/* ── Match ────────────────────────────────────────────────────────── */

export interface Subscores {
  semantic: number;
  keyword: number;
  tfidf: number;
  structural: number;
  skills?: number;
  experience?: number;
  education?: number;
}

export interface MatchResult {
  rank?: number;
  candidate_name?: string;
  score: number;
  similarity_score?: number;
  ml_probability?: number;
  grade: string;
  matched_skills: string[];
  missing_skills: string[];
  subscores: Subscores;
  explanation: string;
}

/* ── Batch Match ──────────────────────────────────────────────────── */

export interface BatchMatchData {
  results: MatchResult[];
  page: number;
  per_page: number;
  total: number;
}

/* ── Parse / Resume Profile ───────────────────────────────────────── */

export interface ContactInfo {
  emails: string[];
  phones: string[];
  linkedin: string;
}

export interface Education {
  degree: string;
  institution: string;
  year: string;
}

export interface Experience {
  title: string;
  company: string;
  duration: string;
  years: number;
  responsibilities: string;
}

export interface ResumeProfile {
  name: string;
  contact: ContactInfo;
  skills: string[];
  education: Education[];
  experience: Experience[];
  certifications: string[];
  organizations: string[];
  completeness_score: number;
}

/* ── Health ────────────────────────────────────────────────────────── */

export interface HealthData {
  status: "healthy" | "degraded";
  nlp_model: { ok: boolean };
  ml_service: { ok: boolean };
  storage: { ok: boolean };
}

/* ── Skills Taxonomy ──────────────────────────────────────────────── */

export interface SkillsTaxonomy {
  skills: Record<string, string[]>;
  total: number;
}

/* ── Feedback ─────────────────────────────────────────────────────── */

export interface FeedbackRequest {
  resume_text: string;
  job_description: string;
  corrected_score: number;
  comment?: string;
}

/* ── History (local) ──────────────────────────────────────────────── */

export interface HistoryEntry {
  id: string;
  timestamp: number;
  resumeSnippet: string;
  jobSnippet: string;
  result: MatchResult;
}
