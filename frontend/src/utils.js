// Small utilities shared across components.

export function fmtNum(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  if (typeof n !== "number") return String(n);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function fmtPct(n, digits = 2) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

export function fmtInt(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return Math.round(n).toLocaleString("en-IN");
}

export function fmtCompact(n) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  const abs = Math.abs(n);
  if (abs >= 1e7) return `${(n / 1e7).toFixed(2)}Cr`;
  if (abs >= 1e5) return `${(n / 1e5).toFixed(2)}L`;
  if (abs >= 1e3) return `${(n / 1e3).toFixed(1)}k`;
  return String(Math.round(n));
}

export function gradeColor(g) {
  if (!g) return "text-textMuted";
  if (g.startsWith("A")) return "text-bull";
  if (g.startsWith("B")) return "text-emerald-300";
  if (g.startsWith("C")) return "text-warn";
  if (g.startsWith("D") || g.startsWith("E")) return "text-orange-400";
  return "text-bear";
}

export function gradeBorderColor(g) {
  if (!g) return "border-borderDefault";
  if (g.startsWith("A")) return "border-bull/60";
  if (g.startsWith("B")) return "border-emerald-300/40";
  if (g.startsWith("C")) return "border-warn/40";
  if (g.startsWith("D") || g.startsWith("E")) return "border-orange-400/30";
  return "border-bear/40";
}

export function pnlClass(p) {
  if (p === null || p === undefined || Number.isNaN(p)) return "text-textSecondary";
  if (p > 0) return "text-bull";
  if (p < 0) return "text-bear";
  return "text-textSecondary";
}

export function classNames(...xs) {
  return xs.filter(Boolean).join(" ");
}
