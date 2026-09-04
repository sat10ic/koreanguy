// T10: de-developer helpers shared across DeskTab/DebateTab/PositionsTab —
// map raw model ids / source_cite paths to plain-English labels, and strip
// inline citation codes from user-facing prose while keeping the original
// text (with the codes) available via a title/hover affordance.

const MODEL_SEAT_LABELS = {
  "deepseek/deepseek-v4-pro": "DEEPSEEK",
  "z-ai/glm-5": "GLM",
  "moonshotai/kimi-k2-thinking": "KIMI",
  "qwen/qwen3.5-plus-02-15": "QWEN",
};

// Returns a plain seat label for a raw model id; falls back to the raw id
// (uppercased) when it isn't one of the known seats.
export function modelSeatLabel(modelId) {
  if (!modelId) return modelId;
  return MODEL_SEAT_LABELS[modelId] || modelId;
}

const SOURCE_CITE_RULES = [
  { match: "sizer.py", label: "Rule: sizer authority" },
  { match: "eod_detectors.py", label: "Rule: exit engine" },
  { match: "coach.py", label: "Rule: position coach" },
];

// Humanizes a source_cite value that looks like a file path (e.g.
// "manas_os/agents/sizer.py"). Non-path values are returned unchanged.
export function humanizeSourceCite(sourceCite) {
  if (!sourceCite || typeof sourceCite !== "string") return sourceCite;
  if (!sourceCite.endsWith(".py")) return sourceCite;
  const rule = SOURCE_CITE_RULES.find((r) => sourceCite.includes(r.match));
  return rule ? rule.label : "Rule: system logic";
}

const CITATION_CODE_RE = /\[(TTM|AR)-[^\]]*\]/g;

// Strips inline citation codes like "[TTM-...]" / "[AR-...]" from
// user-facing text, returning { clean, codes } where codes is the list of
// extracted codes (for a "sources" hover/expand affordance).
export function stripCitationCodes(text) {
  if (!text || typeof text !== "string") return { clean: text, codes: [] };
  const codes = text.match(CITATION_CODE_RE) || [];
  const clean = text.replace(CITATION_CODE_RE, "").replace(/\s{2,}/g, " ").trim();
  return { clean, codes };
}
