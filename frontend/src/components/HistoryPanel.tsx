import { motion, AnimatePresence } from "framer-motion";
import { useHistoryStore } from "@/store/useHistoryStore";

export function HistoryPanel() {
  const entries = useHistoryStore((s) => s.entries);
  const removeEntry = useHistoryStore((s) => s.removeEntry);
  const clearAll = useHistoryStore((s) => s.clearAll);

  if (entries.length === 0) {
    return (
      <div className="rounded-2xl border border-zinc-800 bg-surface-1 p-6 text-center text-sm text-zinc-500">
        No match history yet. Results will appear here after matching.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">History</h2>
        <button
          onClick={clearAll}
          className="text-xs text-zinc-500 transition hover:text-danger"
        >
          Clear all
        </button>
      </div>

      <AnimatePresence>
        {entries.map((e) => (
          <motion.div
            key={e.id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            className="rounded-xl border border-zinc-800 bg-surface-2 p-4"
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-zinc-500">
                {new Date(e.timestamp).toLocaleString()}
              </span>
              <div className="flex items-center gap-3">
                <span
                  className="text-sm font-bold"
                  style={{
                    color:
                      e.result.grade === "A"
                        ? "#22c55e"
                        : e.result.grade === "B"
                          ? "#84cc16"
                          : e.result.grade === "C"
                            ? "#f59e0b"
                            : e.result.grade === "D"
                              ? "#f97316"
                              : "#ef4444",
                  }}
                >
                  {e.result.score.toFixed(0)}% ({e.result.grade})
                </span>
                <button
                  onClick={() => removeEntry(e.id)}
                  className="text-zinc-600 transition hover:text-danger"
                  aria-label="Remove history entry"
                >
                  &times;
                </button>
              </div>
            </div>
            <p className="text-xs text-zinc-400 line-clamp-2">
              <strong>Resume:</strong> {e.resumeSnippet}
            </p>
            <p className="mt-1 text-xs text-zinc-400 line-clamp-2">
              <strong>JD:</strong> {e.jobSnippet}
            </p>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
