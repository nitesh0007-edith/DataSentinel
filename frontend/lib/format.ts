export const fmtInt = (n: number | null | undefined) => (n == null ? "—" : n.toLocaleString("en-GB"));

export const fmtPct = (n: number | null | undefined, digits = 1, signed = false) => {
  if (n == null || Number.isNaN(n)) return "—";
  const s = `${(n * 100).toFixed(digits)}%`;
  return signed && n > 0 ? `+${s}` : s;
};

export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export const titleCase = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
