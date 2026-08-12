"use client";

import { useState } from "react";

import { CheckIcon, CopyIcon } from "@/components/ui/icons";

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

/** Copies `text` to the clipboard and briefly shows a "Copied!" confirmation. */
export function CopyButton({ text, label = "Copy", className = "" }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — ignore */
    }
  }

  return (
    <button
      onClick={copy}
      className={`inline-flex items-center gap-1.5 rounded-md border border-black/10 bg-white px-2.5 py-1 text-xs font-medium text-ink/80 transition-colors hover:bg-pistachio-50 ${className}`}
    >
      {copied ? (
        <CheckIcon className="h-3.5 w-3.5 text-pistachio-600" />
      ) : (
        <CopyIcon className="h-3.5 w-3.5" />
      )}
      {copied ? "Copied!" : label}
    </button>
  );
}
