import { useMutation, useQuery } from "@tanstack/react-query";
import {
  batchMatch,
  fetchHealth,
  fetchSkills,
  matchResume,
  parseResume,
  submitFeedback,
} from "./client";
import type { FeedbackRequest } from "@/types/api";

export function useMatch() {
  return useMutation({
    mutationFn: ({
      resumeText,
      jobDescription,
    }: {
      resumeText: string;
      jobDescription: string;
    }) => matchResume(resumeText, jobDescription),
  });
}

export function useBatchMatch() {
  return useMutation({
    mutationFn: ({
      resumeTexts,
      jobDescription,
      page,
      perPage,
      resumeFilenames,
    }: {
      resumeTexts: string[];
      jobDescription: string;
      page?: number;
      perPage?: number;
      resumeFilenames?: string[];
    }) => batchMatch(resumeTexts, jobDescription, page, perPage, resumeFilenames),
  });
}

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });
}

export function useParse() {
  return useMutation({
    mutationFn: (resumeText: string) => parseResume(resumeText),
  });
}

export function useSkills() {
  return useQuery({
    queryKey: ["skills"],
    queryFn: fetchSkills,
    staleTime: 5 * 60_000,
  });
}

export function useFeedback() {
  return useMutation({
    mutationFn: (fb: FeedbackRequest) => submitFeedback(fb),
  });
}
