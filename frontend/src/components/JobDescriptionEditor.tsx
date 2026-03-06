import { useMatchStore } from "@/store/useMatchStore";

export function JobDescriptionEditor() {
  const jobDescription = useMatchStore((s) => s.jobDescription);
  const setJobDescription = useMatchStore((s) => s.setJobDescription);

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-zinc-300">
        Job Description
      </label>
      <textarea
        value={jobDescription}
        onChange={(e) => setJobDescription(e.target.value)}
        placeholder="Paste the job description here…"
        rows={8}
        className="w-full rounded-xl border border-zinc-700 bg-surface-2 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-accent focus:ring-1 focus:ring-accent/40"
        aria-label="Job description"
      />
      <p className="text-right text-xs text-zinc-500">
        {jobDescription.length} chars
      </p>
    </div>
  );
}
