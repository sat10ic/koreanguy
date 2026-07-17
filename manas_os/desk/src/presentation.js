export function formatDisplayFloat(value, { digits = 1, unit = "", prefix = "", scale = 1 } = {}) {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value) * scale;
  if (!Number.isFinite(number)) return "—";
  const places = digits === 2 ? 2 : 1;
  return `${prefix}${number.toLocaleString("en-IN", {
    minimumFractionDigits: places,
    maximumFractionDigits: places,
  })}${unit}`;
}

export function humanizeShortlistReason(reason) {
  const text = String(reason || "").trim();
  if (!text) return "No reason recorded."
  if (/\(allowed:\s*\[/i.test(text)) {
    return "Held for the current market posture.";
  }
  return text;
}

export function newHighsLowsCopy(value, source) {
  const formatted = formatDisplayFloat(value, { digits: 1 });
  if (/up_4pct-down_4pct|NH\/NL not ingested/i.test(String(source || ""))) {
    const compact = formatted.endsWith(".0") ? formatted.slice(0, -2) : formatted;
    return `New highs vs lows: ${compact} (proxy from 4% moves)`;
  }
  return `New highs vs lows: ${formatted}`;
}
