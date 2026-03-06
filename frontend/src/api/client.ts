import type {
  ApiEnvelope,
  BatchMatchData,
  FeedbackRequest,
  HealthData,
  MatchResult,
  ResumeProfile,
  SkillsTaxonomy,
} from "@/types/api";

const BASE = "/api/v1";

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiEnvelope<T>> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
    
    // Check if response is OK before parsing
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`API error (${res.status}): ${text.substring(0, 200)}`);
    }
    
    // Check if response has content
    const text = await res.text();
    if (!text || text.trim() === "") {
      throw new Error("API returned empty response");
    }
    
    // Parse JSON
    let body: ApiEnvelope<T>;
    try {
      body = JSON.parse(text);
    } catch (e) {
      throw new Error(`Invalid JSON response: ${text.substring(0, 200)}`);
    }
    
    if (!body.success) {
      throw new Error(body.errors.join("; ") || "Unknown API error");
    }
    return body;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Network error: ${String(error)}`);
  }
}

export async function matchResume(
  resumeText: string,
  jobDescription: string,
): Promise<ApiEnvelope<MatchResult>> {
  return request<MatchResult>("/match", {
    method: "POST",
    body: JSON.stringify({
      resume_text: resumeText,
      job_description: jobDescription,
    }),
  });
}

export async function batchMatch(
  resumeTexts: string[],
  jobDescription: string,
  page = 1,
  perPage = 20,
  resumeFilenames?: string[],
): Promise<ApiEnvelope<BatchMatchData>> {
  const body: Record<string, unknown> = {
    resume_texts: resumeTexts,
    job_description: jobDescription,
    page,
    per_page: perPage,
  };
  
  if (resumeFilenames && resumeFilenames.length === resumeTexts.length) {
    body.resume_filenames = resumeFilenames;
  }
  
  return request<BatchMatchData>("/match/batch", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function fetchHealth(): Promise<ApiEnvelope<HealthData>> {
  return request<HealthData>("/health");
}

export async function parseResume(
  resumeText: string,
): Promise<ApiEnvelope<ResumeProfile>> {
  return request<ResumeProfile>("/parse", {
    method: "POST",
    body: JSON.stringify({ resume_text: resumeText }),
  });
}

export async function fetchSkills(): Promise<ApiEnvelope<SkillsTaxonomy>> {
  return request<SkillsTaxonomy>("/skills");
}

export async function submitFeedback(
  fb: FeedbackRequest,
): Promise<ApiEnvelope<{ status: string }>> {
  return request<{ status: string }>("/feedback", {
    method: "POST",
    body: JSON.stringify(fb),
  });
}
