/**
 * Typed API client for the Sentinel AI backend.
 *
 * The backend speaks snake_case (Pydantic); the frontend is idiomatic
 * camelCase. Responses are deep-converted here so components consume one
 * consistent shape.
 */

import type { AgentReport, RepositoryMetadata } from "@/types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const API_PREFIX = "/api/v1";

// ── key-case conversion ──────────────────────────────────────────

function toCamel(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
}

function deepCamel<T>(value: unknown): T {
  if (Array.isArray(value)) {
    return value.map((v) => deepCamel(v)) as unknown as T;
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([k, v]) => [
        toCamel(k),
        deepCamel(v),
      ]),
    ) as T;
  }
  return value as T;
}

// ── error extraction (FastAPI returns { detail } — string or array) ──

function extractError(data: unknown, status: number): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : String(d)))
        .join(", ");
    }
  }
  return `Request failed (${status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${API_PREFIX}${path}`, init);
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    throw new Error(extractError(data, res.status));
  }
  return deepCamel<T>(data);
}

// ── endpoints ────────────────────────────────────────────────────

/** Ingest a ZIP upload. */
export function ingestUpload(file: File): Promise<RepositoryMetadata> {
  const form = new FormData();
  form.append("file", file);
  // Note: do not set Content-Type — the browser adds the multipart boundary.
  return request<RepositoryMetadata>("/repositories/upload", {
    method: "POST",
    body: form,
  });
}

// ── async job API (queue-backed scanning) ────────────────────────

export type JobStatus = "queued" | "running" | "done" | "failed";

export interface SubmitResponse {
  jobId: string;
  status: JobStatus;
  deduplicated: boolean;
}

export interface Job {
  id: string;
  status: JobStatus;
  result: AgentReport | null;
  error: string | null;
  cached: boolean;
}

/** Enqueue a scan of a public GitHub URL; returns immediately with a job id. */
export function submitGithubJob(repoUrl: string): Promise<SubmitResponse> {
  return request<SubmitResponse>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

/** Enqueue a scan of an already-ingested repository (e.g. a ZIP upload). */
export function submitRepositoryJob(repositoryId: string): Promise<SubmitResponse> {
  return request<SubmitResponse>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repository_id: repositoryId }),
  });
}

/** Fetch a job's current status/result. */
export function getJob(jobId: string): Promise<Job> {
  return request<Job>(`/jobs/${jobId}`);
}

/**
 * Poll a job until it reaches a terminal state, returning the review.
 * `onStatus` fires on each poll so the UI can reflect queued vs running.
 */
export async function waitForJob(
  jobId: string,
  onStatus?: (status: JobStatus) => void,
  opts: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<AgentReport> {
  const intervalMs = opts.intervalMs ?? 2000;
  const timeoutMs = opts.timeoutMs ?? 5 * 60 * 1000;
  const started = Date.now();

  for (;;) {
    const job = await getJob(jobId);
    onStatus?.(job.status);
    if (job.status === "done") {
      if (!job.result) throw new Error("Scan finished without a result.");
      return job.result;
    }
    if (job.status === "failed") {
      throw new Error(job.error ?? "Scan failed.");
    }
    if (Date.now() - started > timeoutMs) {
      throw new Error("Timed out waiting for the scan to finish.");
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
