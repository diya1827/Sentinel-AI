"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { DownloadIcon, SparkIcon } from "@/components/ui/icons";
import { AskAiDrawer } from "@/components/results/AskAiDrawer";
import { ExecutiveSummary } from "@/components/results/ExecutiveSummary";
import { FindingsTable } from "@/components/results/FindingsTable";
import { RiskScore } from "@/components/results/RiskScore";
import { SeverityCards } from "@/components/results/SeverityCards";
import { computeRiskScore, downloadReport } from "@/lib/report";
import { countBySeverity } from "@/lib/severity";
import type { AgentReport } from "@/types";

interface ResultsViewProps {
  report: AgentReport;
}

export function ResultsView({ report }: ResultsViewProps) {
  const [askOpen, setAskOpen] = useState(false);
  const score = computeRiskScore(report);
  const counts = countBySeverity(report.prioritizedFindings);

  return (
    <div className="animate-fade-in mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {/* Title + actions */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-ink">Security Review</h1>
          <p className="mt-0.5 font-mono text-xs text-ink/40">
            repo {report.repositoryId.slice(0, 12)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setAskOpen(true)}>
            <SparkIcon className="h-4 w-4" />
            Fix with AI
          </Button>
          <Button variant="secondary" onClick={() => downloadReport(report)}>
            <DownloadIcon className="h-4 w-4" />
            Download Report
          </Button>
        </div>
      </div>

      {/* Top row: risk score + severity cards */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <RiskScore score={score} overallRisk={report.overallRisk} />
        </div>
        <div className="lg:col-span-2 lg:self-stretch">
          <SeverityCards counts={counts} />
        </div>
      </div>

      {/* Executive summary */}
      <div className="mt-4">
        <ExecutiveSummary report={report} />
      </div>

      {/* Findings table */}
      <div className="mt-4">
        <FindingsTable findings={report.prioritizedFindings} />
      </div>

      <AskAiDrawer report={report} open={askOpen} onClose={() => setAskOpen(false)} />
    </div>
  );
}
