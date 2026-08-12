"""Centralized, typed application settings.

All environment access flows through here so the rest of the codebase never
reads `os.environ` directly. Backed by pydantic-settings for validation.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default OpenAI-compatible base URLs per provider. `openai` uses the SDK
# default (None). `anthropic` is handled by a separate client.
_PROVIDER_BASE_URLS: dict[str, str | None] = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None,
}


class Settings(BaseSettings):
    """Typed view over the backend `.env`. See `.env.example` for docs."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"
    # Optional regex for origins (e.g. Vercel preview URLs):
    # r"https://.*\.vercel\.app". Blank = disabled.
    cors_origin_regex: str = ""

    # ── LLM (provider-agnostic; defaults to free Google Gemini) ──
    # gemini | groq | ollama | openrouter | openai all speak the OpenAI API,
    # so they share one client — switching is just a base_url + key change.
    # `anthropic` uses its own SDK.
    llm_provider: Literal[
        "gemini", "openai", "groq", "ollama", "openrouter", "anthropic"
    ] = "gemini"
    llm_model: str = "gemini-2.0-flash"
    llm_api_key: str | None = None
    llm_base_url: str | None = None  # override; otherwise derived from provider
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096
    llm_timeout: int = 60
    # Retries when the model returns text that doesn't parse/validate as JSON.
    llm_json_retries: int = 1
    # Anthropic uses its own SDK/key when llm_provider="anthropic".
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # ── Security scanners ────────────────────────────────────────
    semgrep_config: str = "auto"
    semgrep_timeout: int = 300
    gitleaks_timeout: int = 120
    # Cap Semgrep memory (MB) and parallelism to fit small hosts (e.g. Render's
    # 512MB free tier). 0 = let Semgrep decide (unbounded / all cores).
    semgrep_max_memory: int = 0
    semgrep_jobs: int = 0
    # SCA (osv-scanner) — dependency vulnerabilities → OWASP A06.
    osv_timeout: int = 180
    # IaC misconfiguration (checkov) → OWASP A05.
    checkov_timeout: int = 180
    # Custom XSS ruleset run by the dedicated XssScanner. Defaults to the
    # bundled backend/rules/xss.yml, resolved absolutely so it works regardless
    # of the process's working directory.
    xss_rules_path: str = Field(
        default_factory=lambda: str(
            Path(__file__).resolve().parents[2] / "rules" / "xss.yml"
        )
    )

    # ── Workspace ────────────────────────────────────────────────
    scan_workspace_dir: str = Field(default="/tmp/sentinel-scans")

    # ── Job queue (Redis) ────────────────────────────────────────
    # Connection URL, e.g. redis://... or rediss://... (Upstash in prod).
    # Blank → an in-process fakeredis is used (local dev / tests), so the app
    # runs without a Redis install; production sets REDIS_URL to real Redis.
    redis_url: str = ""
    # Number of in-process worker coroutines pulling jobs off the queue.
    worker_concurrency: int = 3
    # TTLs (seconds): finished job records, cached results, submit idempotency.
    job_ttl: int = 86_400
    result_cache_ttl: int = 86_400
    idempotency_ttl: int = 3_600

    # ── Database (users / auth) ──────────────────────────────────
    # SQLite by default → zero external setup. Point at Postgres in prod.
    database_url: str = "sqlite:///./sentinel.db"

    # ── Auth / JWT ───────────────────────────────────────────────
    # MUST be overridden in production (set JWT_SECRET to a long random value).
    jwt_secret: str = "dev-insecure-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    reset_token_expire_minutes: int = 30
    # Login abuse protection (backed by Redis).
    login_max_attempts: int = 10
    login_lockout_seconds: int = 300
    # Used to build password-reset links in emails.
    frontend_base_url: str = "http://localhost:3000"

    # ── Repository ingestion ─────────────────────────────────────
    # Hosts a GitHub URL is allowed to resolve to (comma-separated).
    allowed_git_hosts: str = "github.com"
    git_clone_depth: int = 1
    git_clone_timeout: int = 120
    # Upload / archive safety limits.
    max_upload_size_mb: int = 100
    max_archive_files: int = 20000
    max_archive_total_size_mb: int = 500
    # Cap on nodes walked when building the repository tree.
    max_tree_files: int = 20000

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins parsed from the comma-separated env value."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_git_hosts_list(self) -> list[str]:
        """Allowed git hostnames parsed from the comma-separated env value."""
        return [h.strip().lower() for h in self.allowed_git_hosts.split(",") if h.strip()]

    @property
    def resolved_llm_base_url(self) -> str | None:
        """OpenAI-compatible base URL for the selected provider (or override)."""
        if self.llm_base_url:
            return self.llm_base_url
        return _PROVIDER_BASE_URLS.get(self.llm_provider)


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — import this everywhere config is needed."""
    return Settings()
