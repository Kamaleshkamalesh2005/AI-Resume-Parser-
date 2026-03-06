import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useMatchStore } from "@/store/useMatchStore";

const ACCEPTED_TYPES = [
  "text/plain",
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const MAX_SIZE = 5 * 1024 * 1024; // 5 MB

export function UploadZone() {
  const setResumeText = useMatchStore((s) => s.setResumeText);
  const resumeText = useMatchStore((s) => s.resumeText);
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setIsLoading(true);

      if (!ACCEPTED_TYPES.includes(file.type) && !file.name.endsWith(".txt")) {
        setError("Unsupported file type. Please use .txt, .pdf, or .docx");
        setIsLoading(false);
        return;
      }
      if (file.size > MAX_SIZE) {
        setError("File too large (max 5 MB)");
        setIsLoading(false);
        return;
      }

      try {
        // For text files, read directly
        if (file.type === "text/plain" || file.name.endsWith(".txt")) {
          const text = await file.text();
          setResumeText(text);
          setFileName(file.name);
        } else {
          // For PDF/DOCX, upload to backend for extraction
          const formData = new FormData();
          formData.append("file", file);

          const response = await fetch("/api/v1/extract", {
            method: "POST",
            body: formData,
          });

          const responseText = await response.text();
          let data: {
            success?: boolean;
            errors?: string[];
            data?: { text?: string };
          } | null = null;

          if (responseText) {
            try {
              data = JSON.parse(responseText) as {
                success?: boolean;
                errors?: string[];
                data?: { text?: string };
              };
            } catch {
              throw new Error("Server returned an invalid response");
            }
          }

          if (!response.ok) {
            throw new Error(
              data?.errors?.[0] ||
                `Failed to extract text from file (HTTP ${response.status})`
            );
          }

          if (!data) {
            throw new Error("Server returned an empty response");
          }

          if (!data.success && data.errors) {
            throw new Error(data.errors[0]);
          }

          if (!data.data?.text) {
            throw new Error("No extracted text returned from server");
          }

          setResumeText(data.data.text);
          setFileName(file.name);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to process file");
      } finally {
        setIsLoading(false);
      }
    },
    [setResumeText],
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragActive(false);
      const file = e.dataTransfer.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <div className="space-y-3">
      <label className="text-sm font-medium text-zinc-300">
        Resume Text
      </label>

      {/* Drop zone */}
      <motion.div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={onDrop}
        onClick={() => !isLoading && inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-6 text-center transition-colors ${
          dragActive
            ? "border-accent bg-accent/10"
            : "border-zinc-700 hover:border-zinc-500"
        } ${isLoading ? "opacity-60 cursor-wait" : ""}`}
        whileHover={!isLoading ? { scale: 1.005 } : {}}
        role="button"
        aria-label="Upload resume file or click to browse"
        tabIndex={0}
      >
        <p className="text-sm text-zinc-400">
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-zinc-500/30 border-t-zinc-400" />
              Extracting text…
            </span>
          ) : (
            <>
              Drag &amp; drop a <strong>.txt, .pdf, or .docx</strong> file
              here,
              or&nbsp;
              <span className="text-accent underline">browse</span>
            </>
          )}
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.pdf,.docx"
          className="hidden"
          disabled={isLoading}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
      </motion.div>

      <AnimatePresence>
        {fileName && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-xs text-success"
          >
            Loaded: {fileName}
          </motion.p>
        )}
        {error && (
          <motion.p
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="text-xs text-danger"
            role="alert"
          >
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {/* Text area fallback */}
      <textarea
        value={resumeText}
        onChange={(e) => {
          setResumeText(e.target.value);
          setFileName(null);
        }}
        placeholder="Or paste the resume text here…"
        rows={8}
        className="w-full rounded-xl border border-zinc-700 bg-surface-2 px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none transition focus:border-accent focus:ring-1 focus:ring-accent/40"
        aria-label="Resume text"
      />
      <p className="text-right text-xs text-zinc-500">
        {resumeText.length} chars
      </p>
    </div>
  );
}
