/**
 * Shared TypeScript types — the unified schema the frontend consumes.
 * Mirror the backend Pydantic models; keep in sync with `backend/app/models`.
 */

export type Severity = "info" | "low" | "medium" | "high" | "critical";

/** The single finding shape, regardless of which scanner produced it. */
export interface Finding {
  scanner: string;
  severity: Severity;
  file: string;
  line?: number | null;
  title: string;
  description?: string | null;
  remediation?: string | null;
  ruleId?: string | null;
}

export type ScanStatus = "success" | "failed";

/** Outcome of one scanner's run. */
export interface ScannerResult {
  scanner: string;
  status: ScanStatus;
  findings: Finding[];
  error?: string | null;
  durationSeconds?: number | null;
}

/** Aggregated result of scanning a repository. */
export interface ScanReport {
  repositoryId: string;
  results: ScannerResult[];
  findings: Finding[];
  totalFindings: number;
  severityCounts: Record<Severity, number>;
}

export type Confidence = "low" | "medium" | "high";

/** One correlated, deduplicated, ranked issue produced by the AI agent. */
export interface PrioritizedFinding {
  id: string;
  title: string;
  severity: Severity;
  priority: number;
  category: string;
  affectedFiles: string[];
  sourceFindingIds: string[];
  scanners: string[];
  whyItMatters: string;
  exploitability?: string | null;
  remediation: string;
  confidence: Confidence;
  duplicateOf?: string | null;
}

/** The AI AppSec-engineer agent's full review — rendered directly by the UI. */
export interface AgentReport {
  repositoryId: string;
  modelUsed?: string | null;
  totalInputFindings: number;
  overallRisk: Severity;
  executiveSummary: string;
  developerSummary: string;
  prioritizedFindings: PrioritizedFinding[];
  correlations: string[];
  duplicatesRemoved: number;
  notes?: string | null;
}

// ── Repository ingestion (only what the UI needs from the response) ──

export type NodeType = "file" | "directory";

export interface TreeNode {
  name: string;
  path: string;
  type: NodeType;
  size?: number | null;
  children?: TreeNode[] | null;
}

export interface LanguageStat {
  language: string;
  fileCount: number;
  percentage: number;
}

/** Returned by the ingestion endpoints; we mainly need `repositoryId`. */
export interface RepositoryMetadata {
  repositoryId: string;
  source: "upload" | "github";
  primaryLanguage?: string | null;
  languages: LanguageStat[];
  packageManagers: string[];
  fileCount: number;
  totalSizeBytes: number;
  truncated: boolean;
  tree: TreeNode;
}
