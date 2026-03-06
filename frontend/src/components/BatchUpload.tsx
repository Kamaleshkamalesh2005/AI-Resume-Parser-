import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useBatchMatch } from "@/api/hooks";
import type { MatchResult } from "@/types/api";

const ACCEPTED_TYPES = [
  "text/plain",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const MAX_SIZE = 5 * 1024 * 1024; // 5 MB

export function BatchUpload() {
  const [resumeTexts, setResumeTexts] = useState<string[]>([]);
  const [resumeFilenames, setResumeFilenames] = useState<string[]>([]);
  const [jobDesc, setJobDesc] = useState("");
  const [results, setResults] = useState<MatchResult[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState({ current: 0, total: 0 });
  const batch = useBatchMatch();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const processFile = useCallback(
    async (file: File): Promise<string | null> => {
      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.endsWith(".txt")) {
        return null;
      }
      if (file.size > MAX_SIZE) {
        return null;
      }

      try {
        // For text files, read directly
        if (file.type === "text/plain" || file.name.endsWith(".txt")) {
          return await file.text();
        } else {
          // For PDF/DOCX, upload to backend for extraction
          const formData = new FormData();
          formData.append("file", file);

          const response = await fetch("/api/v1/extract", {
            method: "POST",
            body: formData,
          });

          const responseText = await response.text();
          if (!response.ok || !responseText) {
            return null;
          }

          try {
            const data = JSON.parse(responseText) as { data?: { text?: string } };
            return data.data?.text || null;
          } catch {
            return null;
          }
        }
      } catch {
        return null;
      }
    },
    [],
  );

  const handleFiles = useCallback(
    async (files: FileList) => {
      setIsLoading(true);
      const fileCount = files.length;
      setLoadingProgress({ current: 0, total: fileCount });
      
      // Process all files in parallel for faster extraction
      const filePromises = Array.from(files).map(async (file) => {
        try {
          const text = await processFile(file);
          // Update progress after each file completes
          setLoadingProgress((prev) => ({ 
            current: prev.current + 1, 
            total: fileCount 
          }));
          
          if (text && text.length >= 20) {
            return { text, filename: file.name };
          }
          return null;
        } catch {
          setLoadingProgress((prev) => ({ 
            current: prev.current + 1, 
            total: fileCount 
          }));
          return null;
        }
      });

      const results = await Promise.all(filePromises);
      const validResults = results.filter((r): r is { text: string; filename: string } => r !== null);
      
      if (validResults.length > 0) {
        setResumeTexts((prev) => [...prev, ...validResults.map(r => r.text)]);
        setResumeFilenames((prev) => [...prev, ...validResults.map(r => r.filename)]);
      }
      
      setIsLoading(false);
      setLoadingProgress({ current: 0, total: 0 });
    },
    [processFile],
  );

  const addResume = useCallback(() => {
    setResumeTexts((prev) => [...prev, ""]);
    setResumeFilenames((prev) => [...prev, ""]);
  }, []);

  const updateResume = useCallback((idx: number, val: string) => {
    setResumeTexts((prev) => prev.map((t, i) => (i === idx ? val : t)));
  }, []);

  const removeResume = useCallback((idx: number) => {
    setResumeTexts((prev) => prev.filter((_, i) => i !== idx));
    setResumeFilenames((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const submit = useCallback(async () => {
    const valid = resumeTexts.filter((t) => t.length >= 50);
    const validFilenames = resumeTexts
      .map((t, i) => (t.length >= 50 ? resumeFilenames[i] : null))
      .filter((f): f is string => f !== null);
    
    if (valid.length === 0 || jobDesc.length < 50) return;

    const res = await batch.mutateAsync({
      resumeTexts: valid,
      jobDescription: jobDesc,
      resumeFilenames: validFilenames.length === valid.length ? validFilenames : undefined,
    });
    setResults(res.data.results);
  }, [resumeTexts, resumeFilenames, jobDesc, batch]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      if (e.dataTransfer.files) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles],
  );

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-white">Batch Compare</h2>

      {/* Job Description */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-zinc-300">
          Job Description
        </label>
        <textarea
          value={jobDesc}
          onChange={(e) => setJobDesc(e.target.value)}
          placeholder="Job description (min 50 chars)…"
          rows={4}
          className="w-full rounded-xl border border-zinc-700 bg-surface-2 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-accent focus:ring-1 focus:ring-accent/40"
          aria-label="Batch job description"
        />
        <p className="text-right text-xs text-zinc-500">
          {jobDesc.length} chars
        </p>
      </div>

      {/* File Upload Zone */}
      <div className="space-y-3">
        <label className="text-sm font-medium text-zinc-300">
          Resumes
        </label>
        
        <motion.div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
            dragActive
              ? "border-accent bg-accent/10"
              : "border-zinc-700 hover:border-zinc-500"
          } ${isLoading ? "opacity-60 cursor-wait" : ""}`}
        >
          <p className="text-sm text-zinc-400">
            {isLoading ? (
              <span className="flex flex-col items-center justify-center gap-2">
                <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-zinc-500/30 border-t-zinc-400" />
                <span>Processing {loadingProgress.current} of {loadingProgress.total} files…</span>
              </span>
            ) : (
              <>
                Drag &amp; drop resume files here, or&nbsp;
                <span className="text-accent underline cursor-pointer">
                  browse files
                </span>
                &nbsp;/&nbsp;
                <span className="text-accent underline cursor-pointer">
                  folder
                </span>
              </>
            )}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".txt,.pdf,.docx"
            className="hidden"
            disabled={isLoading}
            onChange={(e) => {
              if (e.target.files) {
                handleFiles(e.target.files);
              }
            }}
            aria-label="Upload resume files"
          />
          <input
            ref={folderInputRef}
            type="file"
            multiple
            {...({ webkitdirectory: "" } as Record<string, string>)}
            accept=".txt,.pdf,.docx"
            className="hidden"
            disabled={isLoading}
            onChange={(e) => {
              if (e.target.files) {
                handleFiles(e.target.files);
              }
            }}
            aria-label="Upload resume folder"
          />
        </motion.div>

        <div className="flex gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="flex-1 rounded-lg border border-zinc-700 px-4 py-2 text-sm transition hover:border-accent hover:text-accent disabled:opacity-50"
          >
            📁 Browse Files
          </button>
          <button
            onClick={() => folderInputRef.current?.click()}
            disabled={isLoading}
            className="flex-1 rounded-lg border border-zinc-700 px-4 py-2 text-sm transition hover:border-accent hover:text-accent disabled:opacity-50"
          >
            📂 Upload Folder
          </button>
          <button
            onClick={addResume}
            disabled={isLoading}
            className="flex-1 rounded-lg border border-zinc-700 px-4 py-2 text-sm transition hover:border-accent hover:text-accent disabled:opacity-50"
          >
            ✏️ Paste Text
          </button>
        </div>
      </div>

      {/* Resume entries */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-sm text-zinc-400">
            {resumeTexts.length} resume{resumeTexts.length !== 1 ? "s" : ""}
          </p>
        </div>
        
        <AnimatePresence>
          {resumeTexts.map((text, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="relative"
            >
              <textarea
                value={text}
                onChange={(e) => updateResume(idx, e.target.value)}
                placeholder={`Resume #${idx + 1} (min 50 chars)…`}
                rows={3}
                className="w-full rounded-xl border border-zinc-700 bg-surface-2 px-4 py-3 pr-10 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-accent focus:ring-1 focus:ring-accent/40"
                aria-label={`Resume ${idx + 1}`}
              />
              <button
                onClick={() => removeResume(idx)}
                className="absolute right-2 top-2 rounded p-1 text-zinc-500 transition hover:text-danger"
                aria-label={`Remove resume ${idx + 1}`}
              >
                ✕
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Submit */}
      <button
        onClick={submit}
        disabled={batch.isPending || resumeTexts.filter((t) => t.length >= 50).length === 0}
        className="w-full rounded-xl bg-accent px-6 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {batch.isPending ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
            Matching…
          </span>
        ) : (
          `Run Batch Match (${resumeTexts.filter((t) => t.length >= 50).length} valid)`
        )}
      </button>

      {batch.isError && (
        <p className="text-sm text-danger" role="alert">
          {batch.error.message}
        </p>
      )}

      {/* Results table */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="overflow-x-auto"
        >
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                <th className="py-2 pr-4">Rank</th>
                <th className="py-2 pr-4">Candidate</th>
                <th className="py-2 pr-4">Score</th>
                <th className="py-2 pr-4">Grade</th>
                <th className="py-2 pr-4">Matched Skills</th>
                <th className="py-2">Missing Skills</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r, i) => (
                <tr key={i} className="border-b border-zinc-800/50">
                  <td className="py-3 pr-4 text-zinc-300">
                    {r.rank ?? i + 1}
                  </td>
                  <td className="py-3 pr-4 text-zinc-200">
                    {r.candidate_name || `Candidate ${i + 1}`}
                  </td>
                  <td className="py-3 pr-4">
                    <span className="text-2xl font-bold text-white">
                      {r.score.toFixed(1)}%
                    </span>
                  </td>
                  <td className="py-3 pr-4 font-semibold text-white">
                    {r.grade}
                  </td>
                  <td className="py-3 pr-4">
                    <div className="flex flex-wrap gap-1">
                      {r.matched_skills.slice(0, 5).map((skill, idx) => (
                        <span
                          key={idx}
                          className="inline-block rounded-full bg-green-500/20 px-2 py-1 text-xs text-green-400 border border-green-500/30"
                        >
                          {skill}
                        </span>
                      ))}
                      {r.matched_skills.length > 5 && (
                        <span className="inline-block rounded-full bg-zinc-700 px-2 py-1 text-xs text-zinc-400">
                          +{r.matched_skills.length - 5}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-3">
                    <div className="flex flex-wrap gap-1">
                      {r.missing_skills.slice(0, 5).map((skill, idx) => (
                        <span
                          key={idx}
                          className="inline-block rounded-full bg-red-500/20 px-2 py-1 text-xs text-red-400 border border-red-500/30"
                        >
                          {skill}
                        </span>
                      ))}
                      {r.missing_skills.length > 5 && (
                        <span className="inline-block rounded-full bg-zinc-700 px-2 py-1 text-xs text-zinc-400">
                          +{r.missing_skills.length - 5}
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </div>
  );
}
