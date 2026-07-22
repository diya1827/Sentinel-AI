"use client";

import { useEffect, useState } from "react";

import { CheckIcon, ShieldIcon, SpinnerIcon } from "@/components/ui/icons";
import type { AnalysisStatus } from "@/hooks/useAnalysis";

interface ScanningViewProps {
  status: Extract<AnalysisStatus, "ingesting" | "analyzing">;
}

const STEPS = [
  { key: "ingest", label: "Ingesting repository", detail: "Staging files in an isolated workspace" },
  { key: "semgrep", label: "Static analysis", detail: "Scanning code patterns with Semgrep" },
  { key: "gitleaks", label: "Secret scanning", detail: "Hunting for leaked credentials with Gitleaks" },
  { key: "ai", label: "AI security review", detail: "Correlating, prioritizing, and explaining findings" },
];

export function ScanningView({ status }: ScanningViewProps) {
  // Advance an internal cursor to animate progress while the request is in
  // flight. Ingesting pins step 0; analyzing walks steps 1→3 over time.
  const [cursor, setCursor] = useState(0);

  useEffect(() => {
    if (status === "ingesting") {
      setCursor(0);
      return;
    }
    // status === "analyzing"
    setCursor((c) => Math.max(c, 1));
    const timer = setInterval(() => {
      setCursor((c) => (c < STEPS.length - 1 ? c + 1 : c));
    }, 1400);
    return () => clearInterval(timer);
  }, [status]);

  const progress = ((cursor + 1) / STEPS.length) * 100;

  return (
    <div className="mx-auto flex min-h-[70vh] max-w-lg flex-col items-center justify-center px-4">
      <span className="animate-glow flex h-16 w-16 items-center justify-center rounded-2xl bg-indigo-500/15 text-indigo-400">
        <ShieldIcon className="h-9 w-9" />
      </span>
      <h1 className="mt-6 text-xl font-semibold text-slate-100">Analyzing your code…</h1>
      <p className="mt-1 text-sm text-slate-500">This usually takes a few moments.</p>

      {/* Progress bar */}
      <div className="mt-8 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-700 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <ol className="mt-8 w-full space-y-2.5">
        {STEPS.map((step, index) => {
          const state = index < cursor ? "done" : index === cursor ? "active" : "pending";
          return (
            <li
              key={step.key}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors ${
                state === "active"
                  ? "border-indigo-500/40 bg-indigo-500/5"
                  : "border-slate-800 bg-slate-900/40"
              }`}
            >
              <span
                className={`flex h-7 w-7 flex-none items-center justify-center rounded-full ${
                  state === "done"
                    ? "bg-emerald-500/15 text-emerald-400"
                    : state === "active"
                      ? "bg-indigo-500/15 text-indigo-400"
                      : "bg-slate-800 text-slate-600"
                }`}
              >
                {state === "done" ? (
                  <CheckIcon className="h-4 w-4" />
                ) : state === "active" ? (
                  <SpinnerIcon className="h-4 w-4 animate-spin" />
                ) : (
                  <span className="text-xs">{index + 1}</span>
                )}
              </span>
              <div className="min-w-0">
                <p
                  className={`text-sm font-medium ${
                    state === "pending" ? "text-slate-500" : "text-slate-200"
                  }`}
                >
                  {step.label}
                </p>
                <p className="truncate text-xs text-slate-500">{step.detail}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
