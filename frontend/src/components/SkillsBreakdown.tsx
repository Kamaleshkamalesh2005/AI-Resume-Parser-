import { motion } from "framer-motion";

interface Props {
  matched: string[];
  missing: string[];
}

const chip =
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium";

export function SkillsBreakdown({ matched, missing }: Props) {
  if (matched.length === 0 && missing.length === 0) return null;

  return (
    <div className="space-y-4">
      {matched.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-zinc-300">
            Matched Skills
          </h4>
          <div className="flex flex-wrap gap-1.5" role="list" aria-label="Matched skills">
            {matched.map((s, i) => (
              <motion.span
                key={s}
                className={`${chip} border border-success/30 bg-success/10 text-success`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
                role="listitem"
              >
                {s}
              </motion.span>
            ))}
          </div>
        </div>
      )}

      {missing.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-zinc-300">
            Missing Skills
          </h4>
          <div className="flex flex-wrap gap-1.5" role="list" aria-label="Missing skills">
            {missing.map((s, i) => (
              <motion.span
                key={s}
                className={`${chip} border border-danger/30 bg-danger/10 text-danger`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.03 }}
                role="listitem"
              >
                {s}
              </motion.span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
