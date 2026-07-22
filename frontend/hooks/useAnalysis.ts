/**
 * useAnalysis — drives the ingest → analyze flow as a small state machine.
 *
 * States: idle → ingesting → analyzing → done | error.
 * Exposes the current status plus the resulting `AgentReport` and any error,
 * so the UI can swap between the Upload, Scanning, and Results views.
 */

"use client";

import { useCallback, useState } from "react";

import { analyzeRepository, ingestGithub, ingestUpload } from "@/lib/api";
import type { AgentReport, RepositoryMetadata } from "@/types";

export type AnalysisStatus = "idle" | "ingesting" | "analyzing" | "done" | "error";

export interface UseAnalysis {
  status: AnalysisStatus;
  report: AgentReport | null;
  error: string | null;
  analyzeFromFile: (file: File) => Promise<void>;
  analyzeFromGithub: (url: string) => Promise<void>;
  reset: () => void;
}

export function useAnalysis(): UseAnalysis {
  const [status, setStatus] = useState<AnalysisStatus>("idle");
  const [report, setReport] = useState<AgentReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(
    async (ingest: () => Promise<RepositoryMetadata>) => {
      setError(null);
      setReport(null);
      setStatus("ingesting");
      try {
        const meta = await ingest();
        setStatus("analyzing");
        const result = await analyzeRepository(meta.repositoryId);
        setReport(result);
        setStatus("done");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong.");
        setStatus("error");
      }
    },
    [],
  );

  const analyzeFromFile = useCallback((file: File) => run(() => ingestUpload(file)), [run]);
  const analyzeFromGithub = useCallback((url: string) => run(() => ingestGithub(url)), [run]);

  const reset = useCallback(() => {
    setStatus("idle");
    setReport(null);
    setError(null);
  }, []);

  return { status, report, error, analyzeFromFile, analyzeFromGithub, reset };
}
