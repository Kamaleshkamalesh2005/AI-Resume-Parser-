import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { HistoryEntry, MatchResult } from "@/types/api";

interface HistoryState {
  entries: HistoryEntry[];
  addEntry: (
    resumeSnippet: string,
    jobSnippet: string,
    result: MatchResult,
  ) => void;
  removeEntry: (id: string) => void;
  clearAll: () => void;
}

export const useHistoryStore = create<HistoryState>()(
  persist(
    (set) => ({
      entries: [],
      addEntry: (resumeSnippet, jobSnippet, result) =>
        set((s) => ({
          entries: [
            {
              id: crypto.randomUUID(),
              timestamp: Date.now(),
              resumeSnippet: resumeSnippet.slice(0, 120),
              jobSnippet: jobSnippet.slice(0, 120),
              result,
            },
            ...s.entries,
          ].slice(0, 50), // keep last 50
        })),
      removeEntry: (id) =>
        set((s) => ({ entries: s.entries.filter((e) => e.id !== id) })),
      clearAll: () => set({ entries: [] }),
    }),
    { name: "resume-matcher-history" },
  ),
);
