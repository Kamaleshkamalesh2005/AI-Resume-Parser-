import { create } from "zustand";
import type { MatchResult } from "@/types/api";

interface MatchState {
  resumeText: string;
  jobDescription: string;
  result: MatchResult | null;
  isLoading: boolean;
  error: string | null;
  setResumeText: (t: string) => void;
  setJobDescription: (t: string) => void;
  setResult: (r: MatchResult | null) => void;
  setLoading: (v: boolean) => void;
  setError: (e: string | null) => void;
  reset: () => void;
}

export const useMatchStore = create<MatchState>((set) => ({
  resumeText: "",
  jobDescription: "",
  result: null,
  isLoading: false,
  error: null,
  setResumeText: (resumeText) => set({ resumeText }),
  setJobDescription: (jobDescription) => set({ jobDescription }),
  setResult: (result) => set({ result }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      resumeText: "",
      jobDescription: "",
      result: null,
      isLoading: false,
      error: null,
    }),
}));
