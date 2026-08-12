"use client";

import { useState } from "react";

import { Card, CardHeader } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { ChevronIcon, ShieldIcon } from "@/components/ui/icons";
import type { PrioritizedFinding } from "@/types";

interface FindingsTableProps {
  findings: PrioritizedFinding[];
}

export function FindingsTable({ findings }: FindingsTableProps) {
  const [expanded, setExpanded] = useState<string | null>(null);
  const sorted = [...findings].sort((a, b) => a.priority - b.priority);

  return (
    <Card>
      <CardHeader
        title="Security Findings"
        icon={<ShieldIcon className="h-4 w-4" />}
        action={
          <span className="text-xs text-ink/40">{findings.length} prioritized</span>
        }
      />

      {sorted.length === 0 ? (
        <p className="px-5 py-10 text-center text-sm text-ink/40">
          No prioritized findings. 🎉
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead>
              <tr className="border-b border-black/5 text-xs uppercase tracking-wide text-ink/40">
                <th className="w-12 px-5 py-3 font-medium">#</th>
                <th className="px-3 py-3 font-medium">Severity</th>
                <th className="px-3 py-3 font-medium">Issue</th>
                <th className="px-3 py-3 font-medium">Category</th>
                <th className="px-3 py-3 font-medium">Location</th>
                <th className="px-3 py-3 font-medium">Detected by</th>
                <th className="w-10 px-3 py-3" />
              </tr>
            </thead>
            <tbody>
              {sorted.map((finding) => {
                const isOpen = expanded === finding.id;
                return (
                  <FindingRow
                    key={finding.id}
                    finding={finding}
                    isOpen={isOpen}
                    onToggle={() => setExpanded(isOpen ? null : finding.id)}
                  />
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function FindingRow({
  finding,
  isOpen,
  onToggle,
}: {
  finding: PrioritizedFinding;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const primaryFile = finding.affectedFiles[0];
  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer border-b border-black/5 transition-colors hover:bg-pistachio-50"
      >
        <td className="px-5 py-3 text-ink/40">{finding.priority}</td>
        <td className="px-3 py-3">
          <SeverityBadge severity={finding.severity} />
        </td>
        <td className="px-3 py-3 font-medium text-ink">{finding.title}</td>
        <td className="px-3 py-3 text-ink/60">{finding.category}</td>
        <td className="max-w-[220px] truncate px-3 py-3 font-mono text-xs text-ink/60">
          {primaryFile ?? "—"}
          {finding.affectedFiles.length > 1 && (
            <span className="text-ink/30"> +{finding.affectedFiles.length - 1}</span>
          )}
        </td>
        <td className="px-3 py-3 text-xs text-ink/60">
          {finding.scanners.join(", ") || "—"}
        </td>
        <td className="px-3 py-3 text-ink/40">
          <ChevronIcon className={`h-4 w-4 transition-transform ${isOpen ? "rotate-90" : ""}`} />
        </td>
      </tr>
      {isOpen && (
        <tr className="bg-pistachio-50/60">
          <td colSpan={7} className="px-5 py-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <DetailBlock label="Why it matters">{finding.whyItMatters}</DetailBlock>
              {finding.exploitability && (
                <DetailBlock label="Exploitability">{finding.exploitability}</DetailBlock>
              )}
              <DetailBlock label="Remediation" accent>
                {finding.remediation}
              </DetailBlock>
              <div className="flex flex-wrap items-start gap-4 text-xs text-ink/50">
                <span>
                  Confidence: <span className="text-ink">{finding.confidence}</span>
                </span>
                {finding.affectedFiles.length > 0 && (
                  <span className="min-w-0">
                    Files:{" "}
                    <span className="font-mono text-ink/80">
                      {finding.affectedFiles.join(", ")}
                    </span>
                  </span>
                )}
                {finding.sourceFindingIds.length > 0 && (
                  <span>Source: {finding.sourceFindingIds.join(", ")}</span>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function DetailBlock({
  label,
  children,
  accent = false,
}: {
  label: string;
  children: React.ReactNode;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-lg border p-3 ${
        accent ? "border-pistachio-300 bg-pistachio-50" : "border-black/5 bg-white"
      }`}
    >
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-ink/50">
        {label}
      </p>
      <p className="text-sm leading-relaxed text-ink/80">{children}</p>
    </div>
  );
}
