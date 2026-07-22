import type { ReactNode } from "react";

import { ShieldIcon } from "@/components/ui/icons";

interface HeaderProps {
  action?: ReactNode;
}

/** Top navigation bar shown on every view. */
export function Header({ action }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/70 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/15 text-indigo-400">
            <ShieldIcon className="h-5 w-5" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold text-slate-100">Sentinel AI</p>
            <p className="text-[11px] text-slate-500">Application Security Reviewer</p>
          </div>
        </div>
        {action}
      </div>
    </header>
  );
}
