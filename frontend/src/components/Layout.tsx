import type { ReactNode } from "react";
import { useHealth } from "@/api/hooks";

export function Layout({ children }: { children: ReactNode }) {
  const health = useHealth();
  const status = health.data?.data?.status;

  return (
    <div className="flex min-h-screen flex-col">
      {/* ── Header ───────────────────────────────────────────── */}
      <header className="sticky top-0 z-30 border-b border-zinc-800 bg-surface-1/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-white">
              AI Resume Matcher
            </span>
          </div>

          <div className="flex items-center gap-3 text-sm text-zinc-400">
            {status && (
              <span className="flex items-center gap-1.5">
                <span
                  className={`inline-block h-2 w-2 rounded-full ${
                    status === "healthy" ? "bg-success" : "bg-warning"
                  }`}
                  aria-label={`API status: ${status}`}
                />
                {status}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* ── Main ─────────────────────────────────────────────── */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        {children}
      </main>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="border-t border-zinc-800 py-4 text-center text-xs text-zinc-500">
        &copy; {new Date().getFullYear()} AI Resume Matcher &mdash; Built with
        React + Flask
      </footer>
    </div>
  );
}
