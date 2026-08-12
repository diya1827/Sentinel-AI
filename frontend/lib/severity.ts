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
    text: "text-red-600",
    bg: "bg-red-50",
    border: "border-red-200",
    dot: "bg-red-500",
    bar: "bg-red-500",
  },
  high: {
    label: "High",
    text: "text-orange-600",
    bg: "bg-orange-50",
    border: "border-orange-200",
    dot: "bg-orange-500",
    bar: "bg-orange-500",
  },
  medium: {
    label: "Medium",
    text: "text-amber-600",
    bg: "bg-amber-50",
    border: "border-amber-200",
    dot: "bg-amber-500",
    bar: "bg-amber-500",
  },
  low: {
    label: "Low",
    text: "text-sky-600",
    bg: "bg-sky-50",
    border: "border-sky-200",
    dot: "bg-sky-500",
    bar: "bg-sky-500",
  },
  info: {
    label: "Info",
    text: "text-neutral-500",
    bg: "bg-neutral-100",
    border: "border-neutral-200",
    dot: "bg-neutral-400",
    bar: "bg-neutral-400",
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
