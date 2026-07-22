import { Card } from "@/components/ui/Card";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { SEVERITY_META } from "@/lib/severity";
import { riskBand } from "@/lib/report";
import type { Severity } from "@/types";

interface RiskScoreProps {
  score: number; // 0–100, higher = more risk
  overallRisk: Severity;
}

const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

// Stroke color per band (static classes for Tailwind JIT).
const STROKE: Record<Severity, string> = {
  critical: "text-red-500",
  high: "text-orange-500",
  medium: "text-amber-400",
  low: "text-sky-500",
  info: "text-emerald-400",
};

export function RiskScore({ score, overallRisk }: RiskScoreProps) {
  const band = riskBand(score);
  const offset = CIRCUMFERENCE * (1 - score / 100);

  return (
    <Card className="flex flex-col items-center justify-center p-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        Risk Score
      </p>

      <div className="relative mt-4 h-40 w-40">
        <svg className="h-full w-full -rotate-90" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            fill="none"
            strokeWidth={10}
            className="stroke-slate-800"
          />
          <circle
            cx="60"
            cy="60"
            r={RADIUS}
            fill="none"
            strokeWidth={10}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            className={`${STROKE[band.severity]} transition-all duration-1000 ease-out`}
            stroke="currentColor"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-slate-50">{score}</span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
      </div>

      <p className={`mt-4 text-sm font-medium ${SEVERITY_META[band.severity].text}`}>
        {band.label}
      </p>
      <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
        <span>AI verdict:</span>
        <SeverityBadge severity={overallRisk} />
      </div>
    </Card>
  );
}
