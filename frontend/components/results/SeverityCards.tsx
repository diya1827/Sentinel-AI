import { Card } from "@/components/ui/Card";
import { SEVERITY_META } from "@/lib/severity";
import type { Severity } from "@/types";

interface SeverityCardsProps {
  counts: Record<Severity, number>;
}

// The four severities the dashboard surfaces as headline cards.
const CARD_SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

export function SeverityCards({ counts }: SeverityCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      {CARD_SEVERITIES.map((severity) => {
        const meta = SEVERITY_META[severity];
        return (
          <Card key={severity} className={`p-4 ${meta.border}`}>
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
                {meta.label}
              </p>
            </div>
            <p className={`mt-3 text-3xl font-bold ${meta.text}`}>{counts[severity]}</p>
            <p className="mt-0.5 text-xs text-slate-600">
              {counts[severity] === 1 ? "issue" : "issues"}
            </p>
          </Card>
        );
      })}
    </div>
  );
}
