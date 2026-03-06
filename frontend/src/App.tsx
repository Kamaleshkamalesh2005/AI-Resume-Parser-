import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMatch } from "@/api/hooks";
import { useMatchStore } from "@/store/useMatchStore";
import { Layout } from "@/components/Layout";
import { UploadZone } from "@/components/UploadZone";
import { JobDescriptionEditor } from "@/components/JobDescriptionEditor";
import { MatchResultCard } from "@/components/MatchResultCard";
import { BatchUpload } from "@/components/BatchUpload";
import { ErrorBoundary } from "@/components/ErrorBoundary";

type Tab = "single" | "batch";

function App() {
  const [tab, setTab] = useState<Tab>("single");
  const match = useMatch();
  const { resumeText, jobDescription, result, setResult, setError, error } =
    useMatchStore();

  const canSubmit =
    resumeText.length >= 50 && jobDescription.length >= 50 && !match.isPending;

  const handleMatch = async () => {
    setError(null);
    try {
      const res = await match.mutateAsync({ resumeText, jobDescription });
      setResult(res.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Match failed");
    }
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "single", label: "Single Match" },
    { key: "batch", label: "Batch Compare" },
  ];

  return (
    <Layout>
      {/* ── Tabs ──────────────────────────────────────────────── */}
      <div className="mb-8 flex gap-1 rounded-xl bg-surface-2 p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`relative flex-1 rounded-lg px-4 py-2 text-sm font-medium transition ${
              tab === t.key
                ? "text-white"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {tab === t.key && (
              <motion.div
                layoutId="tab-bg"
                className="absolute inset-0 rounded-lg bg-surface-3"
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
            <span className="relative z-10">{t.label}</span>
          </button>
        ))}
      </div>

      <ErrorBoundary>
        <AnimatePresence mode="wait">
          {/* ── Single Match ────────────────────────────────────── */}
          {tab === "single" && (
            <motion.div
              key="single"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="space-y-6"
            >
              <div className="grid gap-6 md:grid-cols-2">
                <UploadZone />
                <JobDescriptionEditor />
              </div>

              <div className="flex items-center gap-4">
                <button
                  onClick={handleMatch}
                  disabled={!canSubmit}
                  className="rounded-xl bg-accent px-8 py-3 font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {match.isPending ? (
                    <span className="flex items-center gap-2">
                      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Matching…
                    </span>
                  ) : (
                    "Match Resume"
                  )}
                </button>

                {error && (
                  <p className="text-sm text-danger" role="alert">
                    {error}
                  </p>
                )}
              </div>

              <AnimatePresence>
                {result && (
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                  >
                    <MatchResultCard result={result} />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ── Batch ───────────────────────────────────────────── */}
          {tab === "batch" && (
            <motion.div
              key="batch"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <BatchUpload />
            </motion.div>
          )}
        </AnimatePresence>
      </ErrorBoundary>
    </Layout>
  );
}

export default App;
