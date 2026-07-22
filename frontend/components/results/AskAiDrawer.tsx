"use client";

import { useEffect } from "react";

import { CloseIcon, SparkIcon } from "@/components/ui/icons";
import type { AgentReport } from "@/types";

interface AskAiDrawerProps {
  report: AgentReport;
  open: boolean;
  onClose: () => void;
}

/**
 * A slide-over that surfaces the agent's guidance. Interactive Q&A needs a
 * backend chat endpoint (roadmap); for now it presents the developer summary,
 * per-issue remediations, and any caveats the agent raised.
 */
export function AskAiDrawer({ report, open, onClose }: AskAiDrawerProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <>
      {/* Overlay */}
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      {/* Panel */}
      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-900 shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-400">
              <SparkIcon className="h-4 w-4" />
            </span>
            <h2 className="text-sm font-semibold text-slate-100">AI Assistant</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            aria-label="Close"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <Section title="What to do first">
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">
              {report.developerSummary}
            </p>
          </Section>

          {report.prioritizedFindings.length > 0 && (
            <Section title="Fix guidance by issue">
              <ul className="space-y-3">
                {report.prioritizedFindings.slice(0, 8).map((f) => (
                  <li key={f.id} className="rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                    <p className="text-sm font-medium text-slate-200">
                      {f.priority}. {f.title}
                    </p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-400">{f.remediation}</p>
                  </li>
                ))}
              </ul>
            </Section>
          )}

          {report.notes && (
            <Section title="Caveats">
              <p className="text-sm leading-relaxed text-slate-400">{report.notes}</p>
            </Section>
          )}
        </div>

        {/* Composer (interactive chat is on the roadmap) */}
        <div className="border-t border-slate-800 p-4">
          <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/50 px-3 py-2">
            <input
              disabled
              placeholder="Ask a follow-up question (coming soon)…"
              className="flex-1 bg-transparent text-sm text-slate-300 placeholder:text-slate-600 focus:outline-none disabled:cursor-not-allowed"
            />
            <SparkIcon className="h-4 w-4 text-slate-600" />
          </div>
        </div>
      </aside>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {title}
      </h3>
      {children}
    </section>
  );
}
