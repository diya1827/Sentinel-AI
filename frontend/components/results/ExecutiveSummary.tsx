"use client";

import { useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { SparkIcon } from "@/components/ui/icons";
import type { AgentReport } from "@/types";

interface ExecutiveSummaryProps {
  report: AgentReport;
}

type View = "executive" | "developer";

export function ExecutiveSummary({ report }: ExecutiveSummaryProps) {
  const [view, setView] = useState<View>("executive");
  const text = view === "executive" ? report.executiveSummary : report.developerSummary;

  return (
    <Card>
      <CardHeader
        title="AI Security Summary"
        icon={<SparkIcon className="h-4 w-4" />}
        action={
          <div className="flex rounded-lg bg-slate-800 p-0.5 text-xs">
            <ToggleButton active={view === "executive"} onClick={() => setView("executive")}>
              Executive
            </ToggleButton>
            <ToggleButton active={view === "developer"} onClick={() => setView("developer")}>
              Developer
            </ToggleButton>
          </div>
        }
      />
      <div className="px-5 py-4">
        <p className="whitespace-pre-line text-sm leading-relaxed text-slate-300">{text}</p>

        {report.correlations.length > 0 && (
          <div className="mt-4 border-t border-slate-800 pt-4">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
              Correlations
            </p>
            <ul className="space-y-1.5">
              {report.correlations.map((c, i) => (
                <li key={i} className="flex gap-2 text-xs text-slate-400">
                  <span className="text-indigo-400">•</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-slate-800 pt-4 text-xs text-slate-500">
          <span>
            {report.totalInputFindings} raw findings →{" "}
            <span className="text-slate-300">{report.prioritizedFindings.length}</span> prioritized
          </span>
          <span>{report.duplicatesRemoved} duplicates removed</span>
          {report.modelUsed && <span>Model: {report.modelUsed}</span>}
        </div>
      </div>
    </Card>
  );
}

function ToggleButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md px-2.5 py-1 font-medium transition-colors ${
        active ? "bg-slate-700 text-slate-100" : "text-slate-400 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}
