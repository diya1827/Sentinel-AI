import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

/** Base surface used across the dashboard. */
export function Card({ children, className = "" }: CardProps) {
  return (
    <div
      className={`rounded-2xl border border-black/5 bg-white shadow-soft ${className}`}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps {
  title: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function CardHeader({ title, icon, action }: CardHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-black/5 px-5 py-4">
      <div className="flex items-center gap-2.5">
        {icon && <span className="text-pistachio-600">{icon}</span>}
        <h2 className="text-sm font-semibold tracking-wide text-ink">{title}</h2>
      </div>
      {action}
    </div>
  );
}
