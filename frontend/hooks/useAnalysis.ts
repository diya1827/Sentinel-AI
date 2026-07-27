/**
 * useAnalysis — drives the ingest → enqueue → poll flow as a state machine.
 *
 * States: idle → ingesting → analyzing → done | error.
 * Scanning is async on the backend: we submit a job and poll it, so a slow
 * scan + LLM run never holds a request open. GitHub URLs are submitted straight
 * to the queue (the worker clones); ZIP uploads are ingested first, then queued.
 */

"use client";

import { useCallback, useState } from "react";

import {
  ingestUpload,
  submitGithubJob,
  submitRepositoryJob,
  waitForJob,
} from "@/lib/api";
import type { AgentReport } from "@/types";

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

  const fail = useCallback((err: unknown) => {
    setError(err instanceof Error ? err.message : "Something went wrong.");
    setStatus("error");
  }, []);

  const analyzeFromGithub = useCallback(
    async (url: string) => {
      setError(null);
      setReport(null);
      setStatus("analyzing");
      try {
        const { jobId } = await submitGithubJob(url);
        const result = await waitForJob(jobId);
        setReport(result);
        setStatus("done");
      } catch (err) {
        fail(err);
      }
    },
    [fail],
  );

  const analyzeFromFile = useCallback(
    async (file: File) => {
      setError(null);
      setReport(null);
      setStatus("ingesting");
      try {
        const meta = await ingestUpload(file);
        setStatus("analyzing");
        const { jobId } = await submitRepositoryJob(meta.repositoryId);
        const result = await waitForJob(jobId);
        setReport(result);
        setStatus("done");
      } catch (err) {
        fail(err);
      }
    },
    [fail],
  );

  const reset = useCallback(() => {
    setStatus("idle");
    setReport(null);
    setError(null);
  }, []);

  return { status, report, error, analyzeFromFile, analyzeFromGithub, reset };
}
