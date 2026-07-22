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

/** Ingest a public GitHub repository by URL. */
export function ingestGithub(repoUrl: string): Promise<RepositoryMetadata> {
  return request<RepositoryMetadata>("/repositories/github", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

/** Run scanners + the AI agent, returning the full review. */
export function analyzeRepository(repositoryId: string): Promise<AgentReport> {
  return request<AgentReport>(`/repositories/${repositoryId}/analyze`, {
    method: "POST",
  });
}
