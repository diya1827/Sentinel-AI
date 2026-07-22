import type { Severity } from "@/types";
import { SEVERITY_META } from "@/lib/severity";

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

/** Small pill showing a severity with its dot + color. */
export function SeverityBadge({ severity, className = "" }: SeverityBadgeProps) {
  const meta = SEVERITY_META[severity];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${meta.bg} ${meta.border} ${meta.text} ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}
