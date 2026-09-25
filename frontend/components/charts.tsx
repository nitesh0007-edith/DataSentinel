"use client";

import { useRef, useState, type ReactNode } from "react";
import type { DatasetProfile, PipelineRun } from "@/types";
import { fmtInt } from "@/lib/format";
import { Empty, StatusIcon, toneFor } from "./ui";

/* ------------------------------------------------------------------ tooltip */

function useTooltip() {
  const ref = useRef<HTMLDivElement>(null);
  const [tip, setTip] = useState<{ x: number; y: number; body: ReactNode } | null>(null);
  const show = (e: React.MouseEvent | React.FocusEvent, body: ReactNode) => {
    const box = ref.current?.getBoundingClientRect();
    const target = (e.currentTarget as HTMLElement).getBoundingClientRect();
    if (!box) return;
    const x = "clientX" in e ? e.clientX - box.left : target.left - box.left + target.width / 2;
    const y = "clientY" in e ? e.clientY - box.top : target.top - box.top;
    setTip({ x, y, body });
  };
  const node = tip ? (
    <div
      role="tooltip"
      className="pointer-events-none absolute z-10 min-w-40 -translate-x-1/2 -translate-y-[calc(100%+12px)] rounded-lg border border-line bg-surface px-3 py-2 text-xs shadow-lg"
      style={{ left: tip.x, top: tip.y }}
    >
      {tip.body}
    </div>
  ) : null;
  return { ref, show, hide: () => setTip(null), node };
}

function TipRow({ swatch, label, value }: { swatch?: string; label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-0.5">
      <span className="flex items-center gap-1.5 text-ink-2">
        {swatch && <span className="h-2 w-2 rounded-sm" style={{ background: swatch }} />}
        {label}
      </span>
      <span className="tabular font-semibold text-ink">{value}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ category distribution */

export function CategoryComparison({
  baseline,
  current,
  column,
}: {
  baseline: DatasetProfile | null;
  current: DatasetProfile | null;
  column: string;
}) {
  const tt = useTooltip();
  const [showTable, setShowTable] = useState(false);
  const bCol = baseline?.columns[column];
  if (!baseline || !bCol?.frequencies) return <Empty>Run the healthy pipeline to capture a baseline.</Empty>;

  const cCol = current?.columns[column];
  const counts = (p: DatasetProfile | null | undefined, freq: Record<string, number> | null | undefined, nulls: number) =>
    (k: string) => (p && freq ? Math.round((freq[k] ?? 0) * (p.row_count - nulls)) : 0);
  const bCount = counts(baseline, bCol.frequencies, bCol.null_count);
  const cCount = counts(current, cCol?.frequencies, cCol?.null_count ?? 0);
  const keys = Array.from(new Set([...Object.keys(bCol.frequencies), ...Object.keys(cCol?.frequencies ?? {})]));
  keys.sort((a, b) => bCount(b) - bCount(a));
  const max = Math.max(1, ...keys.map((k) => Math.max(bCount(k), cCount(k))));
  const sameRun = current?.run_id === baseline.run_id;

  const series = [
    { name: `Baseline (${baseline.run_id})`, color: "var(--series-1)", get: bCount },
    ...(current && !sameRun ? [{ name: `Latest (${current.run_id})`, color: "var(--series-2)", get: cCount }] : []),
  ];

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <div className="flex flex-wrap gap-4 text-xs text-ink-2">
          {series.map((s) => (
            <span key={s.name} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
        <button onClick={() => setShowTable((v) => !v)} className="text-xs text-accent hover:underline">
          {showTable ? "Chart" : "Table"}
        </button>
      </div>

      {showTable ? (
        <table className="tabular w-full text-sm">
          <thead className="text-left text-xs text-ink-3">
            <tr>
              <th className="py-1 font-medium">{column}</th>
              {series.map((s) => (
                <th key={s.name} className="py-1 text-right font-medium">{s.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k} className="border-t border-line">
                <td className="py-1.5">{k}</td>
                {series.map((s) => (
                  <td key={s.name} className="py-1.5 text-right">{fmtInt(s.get(k))}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div ref={tt.ref} className="relative space-y-3" onMouseLeave={tt.hide}>
          {keys.map((k) => {
            const missing = series.length > 1 && bCount(k) > 0 && cCount(k) === 0;
            return (
              <div
                key={k}
                className="grid grid-cols-[72px_1fr] items-center gap-3 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-accent"
                tabIndex={0}
                onMouseMove={(e) =>
                  tt.show(
                    e,
                    <>
                      <div className="mb-1 font-semibold text-ink">{column} = {k}</div>
                      {series.map((s) => (
                        <TipRow key={s.name} swatch={s.color} label={s.name} value={fmtInt(s.get(k))} />
                      ))}
                    </>,
                  )
                }
                onFocus={(e) => tt.show(e, <div className="font-semibold">{k}: {series.map((s) => fmtInt(s.get(k))).join(" → ")}</div>)}
                onBlur={tt.hide}
              >
                <span className="text-sm font-medium text-ink">{k}</span>
                <div className="flex flex-col gap-[2px]">
                  {series.map((s, i) => {
                    const v = s.get(k);
                    return (
                      <div key={s.name} className="flex h-4 items-center gap-2">
                        {v > 0 ? (
                          <div
                            className="h-full rounded-r-[4px] transition-[width] duration-500"
                            style={{ width: `${(v / max) * 82}%`, background: s.color }}
                          />
                        ) : null}
                        {i === series.length - 1 && missing ? (
                          <span className="flex items-center gap-1 text-xs font-semibold text-critical-ink">
                            <StatusIcon tone="critical" /> 0 rows (missing)
                          </span>
                        ) : (
                          <span className="tabular text-xs text-ink-2">{fmtInt(v)}</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
          {tt.node}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ run timeline */

const HEALTH_FILL: Record<string, string> = {
  HEALTHY: "var(--good)",
  WARNING: "var(--warning)",
  CRITICAL: "var(--critical)",
  UNKNOWN: "var(--text-3)",
};

/** Round axis maximum and 3-5 evenly spaced ticks (1/2/2.5/5 x 10^n steps). */
function niceScale(value: number): { max: number; ticks: number[] } {
  const raw = value / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => value / s <= 5) ?? 10 * mag;
  const max = Math.ceil((value * 1.08) / step) * step;
  const ticks: number[] = [];
  for (let t = step; t <= max; t += step) ticks.push(t);
  return { max, ticks };
}

const INK: Record<string, string> = {
  good: "text-good-ink",
  warning: "text-warning-ink",
  critical: "text-critical-ink",
};

export function RunTimeline({ runs, baselineRows }: { runs: PipelineRun[]; baselineRows: number | null }) {
  const tt = useTooltip();
  if (!runs.length) return <Empty>No pipeline runs yet.</Empty>;
  const shown = runs.slice(-12);
  const { max, ticks } = niceScale(Math.max(1, ...shown.map((r) => r.rows_output), baselineRows ?? 0));
  const H = 150;

  return (
    <div ref={tt.ref} className="relative" onMouseLeave={tt.hide}>
      <div className="relative" style={{ height: H }}>
        {/* recessive gridlines */}
        {ticks.map((t) => (
          <div key={t} className="absolute inset-x-0 border-t border-[var(--grid)]" style={{ bottom: (t / max) * H }}>
            <span className="tabular absolute -top-2 right-0 bg-surface pl-1 text-[10px] text-ink-3">
              {t >= 1000 ? `${fmtInt(t / 1000)}k` : fmtInt(t)}
            </span>
          </div>
        ))}
        {baselineRows != null && (
          <div className="absolute inset-x-0 border-t-2 border-dashed border-[var(--series-1)]" style={{ bottom: (baselineRows / max) * H }}>
            <span className="absolute -top-5 left-0 bg-surface pr-1 text-[10px] font-medium text-ink-2">
              Baseline {fmtInt(baselineRows)}
            </span>
          </div>
        )}
        <div className="absolute inset-0 flex items-end gap-[2px] pr-12">
          {shown.map((r) => (
            <div
              key={r.run_id}
              tabIndex={0}
              className="group flex h-full flex-1 cursor-default items-end justify-center outline-none"
              onMouseMove={(e) =>
                tt.show(
                  e,
                  <>
                    <div className="mb-1 font-semibold text-ink">{r.run_id} · {r.purpose}</div>
                    <TipRow label="Pipeline status" value={r.status} />
                    <TipRow label="Data health" value={r.data_health === "UNKNOWN" ? "Not checked" : r.data_health} />
                    <TipRow label="Rows output" value={fmtInt(r.rows_output)} />
                    <TipRow label="Commit" value={<span className="font-mono">{r.git_commit?.slice(0, 7) ?? "—"}</span>} />
                  </>,
                )
              }
              onFocus={(e) => tt.show(e, <div className="font-semibold">{r.run_id}: {fmtInt(r.rows_output)} rows, {r.data_health}</div>)}
              onBlur={tt.hide}
            >
              <div
                className="w-full max-w-10 rounded-t-[4px] transition-all duration-500 group-hover:opacity-80"
                style={{ height: Math.max(2, (r.rows_output / max) * H), background: HEALTH_FILL[r.data_health] }}
              />
            </div>
          ))}
        </div>
      </div>
      <div className="mt-2 flex gap-[2px] pr-12">
        {shown.map((r) => (
          <div key={r.run_id} className="flex flex-1 flex-col items-center gap-0.5 text-[10px] text-ink-3">
            <span className="tabular">{r.run_id.replace("run-", "#")}</span>
            <span className={`flex items-center gap-0.5 font-medium ${INK[toneFor(r.data_health)] ?? "text-ink-3"}`}>
              <StatusIcon tone={toneFor(r.data_health)} className="h-3 w-3" />
            </span>
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-4 text-xs text-ink-2">
        {(["HEALTHY", "CRITICAL", "UNKNOWN"] as const).map((h) => (
          <span key={h} className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: HEALTH_FILL[h] }} />
            {h === "UNKNOWN" ? "Not checked" : h.toLowerCase().replace(/^\w/, (c) => c.toUpperCase())}
          </span>
        ))}
        <span className="text-ink-3">Bar height = Gold rows output</span>
      </div>
      {tt.node}
    </div>
  );
}

