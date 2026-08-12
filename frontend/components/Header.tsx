import type { ReactNode } from "react";

import { ShieldIcon } from "@/components/ui/icons";

interface HeaderProps {
  action?: ReactNode;
}

/** Top navigation bar shown on every view. */
export function Header({ action }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-black/5 bg-pistachio-200/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-pistachio-600 shadow-soft">
            <ShieldIcon className="h-5 w-5" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-bold text-ink">
              Sentinel<span className="text-pistachio-600"> AI</span>
            </p>
            <p className="text-[11px] text-ink/50">Application Security Reviewer</p>
          </div>
        </div>
        {action}
      </div>
    </header>
  );
}
