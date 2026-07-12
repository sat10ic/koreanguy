import React, { useEffect, useMemo, useState } from "react";
import { fetchAlphaLeaders, fetchDebate, fetchWatchlist } from "../../api.js";

// ── #13b: Alpha ↔ Debate ↔ Shortlist relationship legend + cross-badges ──
// The three lists show DIFFERENT stocks BY DESIGN (confirmed #1 beginner
// confusion, UX_AUDIT_FULL / GUIDED_SYSTEM_DESIGN §5):
//   ALPHA     = shadow cross-sectional rank over the whole universe (research,
//               never a tradeable call — ALPHA_LEARNING_CONSTRAINTS).
//   DEBATE    = council verdicts on GATE-PASSED candidates only.
//   SHORTLIST = the user's own curated watch.
// Legend renders the live funnel (from /api/desk/debate `funnel` — never
// hardcoded; three snapshots have already diverged across docs) and one role
// line per list. Cross-badges tag a symbol's membership in the sibling lists;
// icon+text (WCAG 1.4.1 — never color-only).

// Membership across the three lists for one date. One fetch set per mount.
export function useListMembership(date) {
  const [state, setState] = useState({ loading: true, alphaRank: new Map(), debated: new Set(), watch: new Set(), funnel: null });
  useEffect(() => {
    let dead = false;
    setState((s) => ({ ...s, loading: true }));
    Promise.allSettled([fetchAlphaLeaders(date, 50), fetchDebate(date), fetchWatchlist(date)])
      .then(([alpha, debate, watch]) => {
        if (dead) return;
        const alphaRank = new Map();
        if (alpha.status === "fulfilled") {
          (alpha.value?.rows || []).forEach((r, i) => alphaRank.set(r.symbol, i + 1));
        }
        const debated = new Set(
          debate.status === "fulfilled" ? (debate.value?.symbols || []).map((s) => s.symbol) : [],
        );
        const watchSet = new Set(
          watch.status === "fulfilled" ? (watch.value?.rows || []).map((r) => r.symbol) : [],
        );
        const funnel = debate.status === "fulfilled" ? debate.value?.funnel || null : null;
        setState({ loading: false, alphaRank, debated, watch: watchSet, funnel });
      });
    return () => { dead = true; };
  }, [date]);
  return state;
}

const ROLES = [
  { key: "ALPHA", label: "ALPHA", role: "shadow rank of the whole universe — research, not a call" },
  { key: "DEBATE", label: "DEBATE", role: "council verdicts on gate-passed candidates only" },
  { key: "SHORTLIST", label: "SHORTLIST", role: "your own curated watch" },
];

// Compact strip: live funnel + the three list roles, active one marked.
// Different symbols across tabs is the FUNNEL working, not a bug — say so.
export default function ListRelationshipLegend({ active, membership, onNavigate }) {
  const f = membership?.funnel;
  const stages = useMemo(() => {
    if (!f) return [];
    return [
      { label: "universe", n: f.universe },
      { label: "screeners", n: f.screeners },
      { label: "gates", n: f.gates },
      { label: "debated", n: f.debated },
    ].filter((s) => s.n != null);
  }, [f]);
  return (
    <div className="lrl" role="note" aria-label="How ALPHA, DEBATE and SHORTLIST relate">
      <div className="lrl-funnel">
        {stages.length
          ? stages.map((s, i) => (
              <span key={s.label} className="lrl-stage">
                {i > 0 && <span className="lrl-arrow" aria-hidden="true">→</span>}
                <span className="lrl-n">{Number(s.n).toLocaleString("en-IN")}</span>
                <span className="lrl-stage-label">{s.label}</span>
              </span>
            ))
          : <span className="lrl-stage-label">funnel unavailable for this date</span>}
        <span className="lrl-note">same pipeline — each list is a different cut, so different stocks is by design</span>
      </div>
      <div className="lrl-roles">
        {ROLES.map((r) => (
          <button
            key={r.key}
            type="button"
            className={"lrl-role" + (active === r.key ? " lrl-role--active" : "")}
            onClick={() => active !== r.key && onNavigate?.(r.key)}
            title={active === r.key ? "you are here" : `open ${r.label}`}
          >
            <span className="lrl-role-name">{r.label}</span>
            <span className="lrl-role-desc">{r.role}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

// Inline membership chips for one symbol. Icon+text, link to sibling tab.
export function CrossBadges({ symbol, membership, active, onNavigate }) {
  if (!membership || membership.loading) return null;
  const chips = [];
  const rank = membership.alphaRank.get(symbol);
  if (active !== "ALPHA" && rank != null) {
    chips.push({ key: "alpha", icon: "◈", text: `shadow #${rank}`, tab: "ALPHA", title: "Ranked in ALPHA's shadow universe rank (research only)" });
  }
  if (active !== "DEBATE" && membership.debated.has(symbol)) {
    chips.push({ key: "debate", icon: "⚖", text: "debated", tab: "DEBATE", title: "The council debated this symbol tonight" });
  }
  if (active !== "SHORTLIST" && membership.watch.has(symbol)) {
    chips.push({ key: "watch", icon: "★", text: "on watch", tab: "SHORTLIST", title: "On your shortlist" });
  }
  if (!chips.length) return null;
  return (
    <span className="lrl-badges">
      {chips.map((c) => (
        <button key={c.key} type="button" className="lrl-badge" title={c.title} onClick={() => onNavigate?.(c.tab)}>
          <span aria-hidden="true">{c.icon}</span> {c.text}
        </button>
      ))}
    </span>
  );
}
