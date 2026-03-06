import { motion } from "framer-motion";

interface Props {
  score: number;
  grade: string;
  size?: number;
}

const GRADE_COLORS: Record<string, string> = {
  A: "#22c55e",
  B: "#84cc16",
  C: "#f59e0b",
  D: "#f97316",
  F: "#ef4444",
};

export function ScoreGauge({ score, grade, size = 140 }: Props) {
  const r = (size - 16) / 2;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const color = GRADE_COLORS[grade] ?? "#6366f1";

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: size, height: size }}
      aria-label={`Match score ${score.toFixed(0)}%`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="currentColor"
          className="text-zinc-800"
          strokeWidth={8}
          fill="none"
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={8}
          strokeLinecap="round"
          fill="none"
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - fill }}
          transition={{ duration: 1, ease: "easeOut" }}
          strokeDasharray={circ}
        />
      </svg>

      <div className="absolute flex flex-col items-center">
        <motion.span
          className="text-3xl font-bold"
          style={{ color }}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          {score.toFixed(0)}
        </motion.span>
        <span className="text-xs text-zinc-400">Grade {grade}</span>
      </div>
    </div>
  );
}
