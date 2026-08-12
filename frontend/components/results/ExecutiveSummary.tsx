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
          <div className="flex rounded-lg bg-pistachio-100 p-0.5 text-xs">
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
        <p className="whitespace-pre-line text-sm leading-relaxed text-ink/80">{text}</p>

        {report.correlations.length > 0 && (
          <div className="mt-4 border-t border-black/5 pt-4">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
              Correlations
            </p>
            <ul className="space-y-1.5">
              {report.correlations.map((c, i) => (
                <li key={i} className="flex gap-2 text-xs text-ink/60">
                  <span className="text-pistachio-600">•</span>
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1 border-t border-black/5 pt-4 text-xs text-ink/50">
          <span>
            {report.totalInputFindings} raw findings →{" "}
            <span className="text-ink">{report.prioritizedFindings.length}</span> prioritized
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
        active ? "bg-white text-ink shadow-sm" : "text-ink/50 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}
