import type { ReactNode } from "react";
import type { DataHealth, Severity } from "@/types";

export function Card({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-5 ${className}`}>
      {(title || action) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold tracking-tight text-ink">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-ink-3">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

type Tone = "good" | "warning" | "critical" | "neutral" | "info";

const TONE: Record<Tone, string> = {
  good: "bg-good-soft text-good-ink",
  warning: "bg-warning-soft text-warning-ink",
  critical: "bg-critical-soft text-critical-ink",
  neutral: "bg-surface-2 text-ink-2",
  info: "bg-surface-2 text-accent",
};

export function toneFor(value: DataHealth | Severity | string | null | undefined): Tone {
  switch (value) {
    case "HEALTHY":
    case "SUCCESS":
    case "RESOLVED":
    case "APPLIED":
      return "good";
    case "WARNING":
    case "FIX_PROPOSED":
    case "FIX_APPLIED":
    case "PROPOSED":
      return "warning";
    case "CRITICAL":
    case "FAILED":
    case "DETECTED":
    case "VALIDATION_FAILED":
    case "REJECTED":
      return "critical";
    case "INFO":
    case "ROOT_CAUSE_IDENTIFIED":
      return "info";
    default:
      return "neutral";
  }
}

export function StatusIcon({ tone, className = "h-3.5 w-3.5" }: { tone: Tone; className?: string }) {
  if (tone === "good")
    return (
      <svg viewBox="0 0 16 16" className={className} aria-hidden>
        <circle cx="8" cy="8" r="7" fill="currentColor" opacity="0.18" />
        <path d="M4.5 8.2l2.2 2.2 4.8-4.8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (tone === "critical")
    return (
      <svg viewBox="0 0 16 16" className={className} aria-hidden>
        <path d="M8 1.5l7 12.5H1z" fill="currentColor" opacity="0.18" />
        <path d="M8 6v3.5M8 11.6v.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  if (tone === "warning")
    return (
      <svg viewBox="0 0 16 16" className={className} aria-hidden>
        <circle cx="8" cy="8" r="7" fill="currentColor" opacity="0.18" />
        <path d="M8 4.5v4M8 11v.1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden>
      <circle cx="8" cy="8" r="3" fill="currentColor" />
    </svg>
  );
}

export function Pill({ value, label, tone }: { value?: string | null; label?: string; tone?: Tone }) {
  const t = tone ?? toneFor(value);
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONE[t]}`}>
      <StatusIcon tone={t} />
      {label ?? (value ?? "UNKNOWN").replace(/_/g, " ")}
    </span>
  );
}

export function Spinner({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={`animate-spin ${className}`} aria-hidden>
      <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
      <path d="M14 8a6 6 0 00-6-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="rounded-lg border border-dashed border-line px-4 py-6 text-center text-sm text-ink-3">{children}</p>;
}
