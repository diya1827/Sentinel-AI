"use client";

import { useEffect } from "react";

import { CopyButton } from "@/components/ui/CopyButton";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { CloseIcon, LinkIcon, SparkIcon } from "@/components/ui/icons";
import type { AgentReport, PrioritizedFinding } from "@/types";

interface AskAiDrawerProps {
  report: AgentReport;
  open: boolean;
  onClose: () => void;
}

/**
 * The friendly, actionable side of the review: for each issue it explains the
 * risk in plain English, lists quick fix steps, links to trusted guides, and
 * hands over a copy-paste prompt for the user's own AI coding assistant.
 */
export function AskAiDrawer({ report, open, onClose }: AskAiDrawerProps) {
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const issues = [...report.prioritizedFindings]
    .sort((a, b) => a.priority - b.priority)
    .slice(0, 8);

  return (
    <>
      <div
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-ink/30 transition-opacity ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />

      <aside
        className={`fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col border-l border-black/5 bg-pistachio-50 shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
        aria-hidden={!open}
      >
        <div className="flex items-center justify-between border-b border-black/5 bg-white px-5 py-4">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-pistachio-100 text-pistachio-600">
              <SparkIcon className="h-4 w-4" />
            </span>
            <div className="leading-tight">
              <h2 className="text-sm font-semibold text-ink">Fix it with AI</h2>
              <p className="text-[11px] text-ink/50">Plain-English fixes you can act on</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-ink/50 hover:bg-pistachio-50 hover:text-ink"
            aria-label="Close"
          >
            <CloseIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4 sm:px-5">
          {/* The gist */}
          <div className="rounded-xl border border-black/5 bg-white p-4">
            <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
              The gist
            </h3>
            <p className="whitespace-pre-line text-sm leading-relaxed text-ink/80">
              {report.executiveSummary}
            </p>
          </div>

          {issues.length === 0 ? (
            <p className="px-1 py-6 text-center text-sm text-ink/50">
              Nothing urgent to fix. Nice. 🎉
            </p>
          ) : (
            issues.map((f) => <IssueCard key={f.id} finding={f} />)
          )}

          {report.notes && (
            <div className="rounded-xl border border-black/5 bg-white p-4">
              <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
                Caveats
              </h3>
              <p className="text-sm leading-relaxed text-ink/60">{report.notes}</p>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}

function IssueCard({ finding }: { finding: PrioritizedFinding }) {
  return (
    <div className="rounded-xl border border-black/5 bg-white p-4">
      {/* Title row */}
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-semibold text-ink">
          {finding.priority}. {finding.title}
        </p>
        <SeverityBadge severity={finding.severity} />
      </div>

      {/* Plain-English explanation */}
      <p className="mt-2 text-sm leading-relaxed text-ink/80">
        {finding.plainSummary || finding.whyItMatters}
      </p>

      {/* Quick fix steps */}
      {finding.fixSteps.length > 0 && (
        <div className="mt-3">
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
            How to fix
          </p>
          <ul className="space-y-1.5">
            {finding.fixSteps.map((step, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80">
                <span className="mt-0.5 flex h-4 w-4 flex-none items-center justify-center rounded-full bg-pistachio-100 text-[10px] font-semibold text-pistachio-700">
                  {i + 1}
                </span>
                {step}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Copy-paste prompt for their AI coding assistant */}
      {finding.fixPrompt && (
        <div className="mt-3 rounded-lg border border-pistachio-300 bg-pistachio-50 p-3">
          <div className="mb-1.5 flex items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-pistachio-700">
              Paste into your AI coding tool
            </p>
            <CopyButton text={finding.fixPrompt} label="Copy prompt" />
          </div>
          <p className="whitespace-pre-line font-mono text-xs leading-relaxed text-ink/70">
            {finding.fixPrompt}
          </p>
        </div>
      )}

      {/* Helpful links */}
      {finding.references.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {finding.references.map((ref) => (
            <a
              key={ref.url}
              href={ref.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-2.5 py-1 text-xs font-medium text-ink/70 transition-colors hover:border-pistachio-400 hover:bg-pistachio-50 hover:text-ink"
            >
              <LinkIcon className="h-3 w-3" />
              {ref.title}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
