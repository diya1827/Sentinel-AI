"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { GithubIcon, ShieldIcon, UploadIcon } from "@/components/ui/icons";

interface UploadViewProps {
  onUploadFile: (file: File) => void;
  onSubmitUrl: (url: string) => void;
  error: string | null;
}

type Tab = "github" | "upload";

// One-click demo targets (deliberately vulnerable public repos).
const EXAMPLES: { label: string; url: string }[] = [
  { label: "leaky-repo", url: "https://github.com/Plazmaz/leaky-repo" },
  { label: "nodejs-goof", url: "https://github.com/snyk-labs/nodejs-goof" },
  { label: "NodeGoat", url: "https://github.com/OWASP/NodeGoat" },
];

export function UploadView({ onUploadFile, onSubmitUrl, error }: UploadViewProps) {
  const [tab, setTab] = useState<Tab>("github");

  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 py-16 sm:py-24">
      {/* Wordmark */}
      <div className="animate-fade-in flex flex-col items-center text-center">
        <span className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-white text-pistachio-600 shadow-soft">
          <ShieldIcon className="h-8 w-8" />
        </span>
        <h1 className="text-5xl font-extrabold tracking-tight text-ink sm:text-6xl">
          Sentinel<span className="text-pistachio-600"> AI</span>
        </h1>
        <p className="mt-2 text-sm font-medium text-pistachio-700">
          Paranoia, as a service.
        </p>
        <p className="mt-5 text-lg font-medium text-ink/70">
          Point us at a repo — we&apos;ll find the skeletons.
        </p>
      </div>

      <Card className="animate-fade-in mt-10 w-full p-1.5">
        {/* Tabs (GitHub first / default) */}
        <div className="grid grid-cols-2 gap-1.5">
          <TabButton active={tab === "github"} onClick={() => setTab("github")} icon={<GithubIcon className="h-4 w-4" />}>
            GitHub URL
          </TabButton>
          <TabButton active={tab === "upload"} onClick={() => setTab("upload")} icon={<UploadIcon className="h-4 w-4" />}>
            Upload ZIP
          </TabButton>
        </div>

        <div className="p-4 sm:p-5">
          {tab === "github" ? (
            <GithubForm onSubmit={onSubmitUrl} />
          ) : (
            <ZipDropzone onFile={onUploadFile} />
          )}
        </div>
      </Card>

      {/* One-click examples */}
      {tab === "github" && (
        <div className="animate-fade-in mt-4 flex flex-wrap items-center justify-center gap-2 text-sm">
          <span className="text-ink/50">Or try one:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex.url}
              onClick={() => onSubmitUrl(ex.url)}
              className="rounded-full border border-black/10 bg-white px-3 py-1 font-medium text-ink/80 transition-colors hover:border-pistachio-400 hover:bg-pistachio-50 hover:text-ink"
            >
              {ex.label}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="animate-fade-in mt-4 w-full rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <p className="mt-8 text-center text-xs text-ink/40">
        Scanned in an isolated workspace and removed after review.
      </p>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors ${
        active
          ? "bg-pistachio-100 text-ink"
          : "text-ink/50 hover:bg-pistachio-50 hover:text-ink"
      }`}
    >
      {icon}
      {children}
    </button>
  );
}

function ZipDropzone({ onFile }: { onFile: (file: File) => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [invalid, setInvalid] = useState(false);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setInvalid(true);
      setFileName(null);
      return;
    }
    setInvalid(false);
    setFileName(file.name);
    onFile(file);
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
          dragging
            ? "border-pistachio-500 bg-pistachio-50"
            : "border-pistachio-300 hover:border-pistachio-400 hover:bg-pistachio-50/60"
        }`}
      >
        <UploadIcon className="h-8 w-8 text-pistachio-500" />
        <p className="mt-3 text-sm font-medium text-ink">
          Drop a <span className="text-pistachio-700">.zip</span> here, or click to browse
        </p>
        <p className="mt-1 text-xs text-ink/40">Max 100 MB</p>
        {fileName && (
          <p className="mt-3 rounded-md bg-pistachio-100 px-3 py-1 text-xs text-ink">
            {fileName}
          </p>
        )}
        <input
          ref={inputRef}
          type="file"
          accept=".zip,application/zip"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {invalid && (
        <p className="mt-2 text-xs text-red-600">Please choose a .zip file.</p>
      )}
    </div>
  );
}

function GithubForm({ onSubmit }: { onSubmit: (url: string) => void }) {
  const [url, setUrl] = useState("");
  const [invalid, setInvalid] = useState(false);

  function submit() {
    const value = url.trim();
    if (!/^https:\/\/github\.com\/[^/]+\/[^/]+/.test(value)) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    onSubmit(value);
  }

  return (
    <div>
      <label htmlFor="repo-url" className="mb-1.5 block text-sm font-medium text-ink/80">
        Public GitHub repository
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id="repo-url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit()}
          placeholder="https://github.com/owner/repo"
          className={`h-10 flex-1 rounded-lg border bg-white px-3 text-sm text-ink placeholder:text-ink/30 focus:outline-none focus:ring-2 ${
            invalid
              ? "border-red-300 focus:ring-red-400/40"
              : "border-black/10 focus:border-pistachio-400 focus:ring-pistachio-400/40"
          }`}
        />
        <Button onClick={submit}>Analyze</Button>
      </div>
      {invalid && (
        <p className="mt-2 text-xs text-red-600">
          Enter a valid public GitHub URL, e.g. https://github.com/psf/requests
        </p>
      )}
    </div>
  );
}
