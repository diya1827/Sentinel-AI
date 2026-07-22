/**
 * Severity presentation helpers.
 *
 * Tailwind classes are written as full static strings (not composed at
 * runtime) so the JIT compiler can see and emit them.
 */

import type { Severity } from "@/types";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export interface SeverityMeta {
  label: string;
  text: string;
  bg: string;
  border: string;
  dot: string;
  bar: string;
}

export const SEVERITY_META: Record<Severity, SeverityMeta> = {
  critical: {
    label: "Critical",
    text: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    dot: "bg-red-500",
    bar: "bg-red-500",
  },
  high: {
    label: "High",
    text: "text-orange-400",
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    dot: "bg-orange-500",
    bar: "bg-orange-500",
  },
  medium: {
    label: "Medium",
    text: "text-amber-300",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    dot: "bg-amber-400",
    bar: "bg-amber-400",
  },
  low: {
    label: "Low",
    text: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/30",
    dot: "bg-sky-500",
    bar: "bg-sky-500",
  },
  info: {
    label: "Info",
    text: "text-slate-400",
    bg: "bg-slate-500/10",
    border: "border-slate-500/30",
    dot: "bg-slate-500",
    bar: "bg-slate-500",
  },
};

/** Count findings by severity, always returning all keys. */
export function countBySeverity(
  findings: { severity: Severity }[],
): Record<Severity, number> {
  const counts: Record<Severity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  };
  for (const f of findings) counts[f.severity] += 1;
  return counts;
}
