import { motion } from "framer-motion";
import type { MatchResult } from "@/types/api";
import { ScoreGauge } from "./ScoreGauge";
import { SkillsBreakdown } from "./SkillsBreakdown";

interface Props {
  result: MatchResult;
}

const barVariant = {
  hidden: { width: 0 },
  visible: (pct: number) => ({
    width: `${pct}%`,
    transition: { duration: 0.8, ease: "easeOut" },
  }),
};

function SubScoreBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(value * 100, 100);
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-zinc-400">
        <span className="capitalize">{label}</span>
        <span>{pct.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
        <motion.div
          className="h-full rounded-full bg-accent"
          variants={barVariant}
          initial="hidden"
          animate="visible"
          custom={pct}
        />
      </div>
    </div>
  );
}

export function MatchResultCard({ result }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6 rounded-2xl border border-zinc-800 bg-surface-1 p-6"
    >
      {/* ── Top: Gauge + explanation ──────────────────────────── */}
      <div className="flex flex-col items-center gap-6 sm:flex-row">
        <ScoreGauge score={result.score} grade={result.grade} />
        <div className="flex-1 space-y-2">
          <h3 className="text-lg font-semibold text-white">Match Result</h3>
          <p className="text-sm leading-relaxed text-zinc-400">
            {result.explanation}
          </p>
        </div>
      </div>

      {/* ── Sub-scores ────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2">
        {Object.entries(result.subscores).map(([key, val]) => (
          <SubScoreBar key={key} label={key} value={val as number} />
        ))}
      </div>

      {/* ── Skills ────────────────────────────────────────────── */}
      <SkillsBreakdown
        matched={result.matched_skills}
        missing={result.missing_skills}
      />
    </motion.div>
  );
}
