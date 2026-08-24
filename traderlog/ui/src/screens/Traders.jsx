// TRADERS — REDESIGN_SCOUTING_WIRE §4.3
//
// One question at a time, ranked, with the sample size visible. Not a card
// grid, not four hero stats side by side. The question is a plain-English
// sentence above the ranking; a Segmented control switches the question; bars
// dim to --ink-4 below the §6 confidence threshold and the value becomes an em
// dash + "too few" — never a percentage, never a guess. trader_style is empty
// today (W6 not built), so every row honestly shows the dash/"too few" state;
// the mechanism is fully built and does not fake data.
//
// Thresholds (§6): a trader's rate needs 10 closed positions; a preach score
// needs 10 linked trades. The n is always visible. The roster table stays
// beneath the ranking (sortable, keyboard-reachable Disclosure rows), and
// selecting a trader opens the detail profile (fetchTrader), restyled.
import React from "react";
import { fetchFeed, fetchTrader, fetchTraders } from "../api.js";
import {
  Chip, Disclosure, ErrorBox, Loading, Panel, Segmented, SortableTh, useApi,
} from "../components/ui.jsx";
import { Dumbbell, StripPlot } from "../components/charts.jsx";
import * as chartNS from "../components/charts.jsx";
import "../styles/traders.css";

// S4 remaps charts.jsx internals in parallel; StackedArea and CalendarGrid are
// the two NEW exports of this wave (prop contracts frozen in the handoff).
// They may not exist in this checkout yet — read them off the namespace so
// this screen builds either way and renders the labelled empty state until
// they land. The existing exports (Dumbbell, StripPlot) are imported named.
const StackedArea = chartNS.StackedArea;
const CalendarGrid = chartNS.CalendarGrid;

// §6 — where the tool refuses to speak. A trader's rate needs 10 closed
// positions; a preach score needs 10 linked trades.
const MIN_CLOSED = 10;
const MIN_LINKED = 10;

// Every percentage shows its n; unstated renders "—"; adaptive precision is a
// correctness rule upstream. fnum normalises the payload's null/undefined/NaN
// into a single null so the threshold logic never has to guess.
function fnum(v) {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function pct(v) {
  return Math.round(v * 100);
}

function median(vals) {
  if (!vals.length) return null;
  const s = [...vals].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// The five questions. Each is: its short Segmented label, the plain-English
// sentence stated above the ranking (Rule 1 — a sentence, never a bare
// number), the value from the /api/traders summary, the sample n, the §6
// minimum, and how to format a trustworthy value.
const QUESTIONS = [
  {
    key: "stop",
    label: "stop-kept",
    sentence:
      "Does what he says he'll do — how often a trader who names an exit price actually uses it.",
    // stop_honored_pct is additive from S9 (parallel); undefined today.
    value: (t) => fnum(t.stop_honored_pct),
    n: (t) => fnum(t.closed_positions),
    min: MIN_CLOSED,
    unit: "closed",
    fmt: (v) => `${pct(v)}%`,
  },
  {
    key: "win",
    label: "win rate",
    sentence:
      "Stated win rate — of every closed trade he put a result on, how many did he say won.",
    value: (t) => fnum(t.stated_win_rate),
    n: (t) => fnum(t.closed_positions),
    min: MIN_CLOSED,
    unit: "closed",
    fmt: (v) => `${pct(v)}%`,
  },
  {
    key: "avgR",
    label: "avg R",
    sentence:
      "Average R — how a typical closed result measures against what he risked.",
    value: (t) => fnum(t.avg_r),
    n: (t) => fnum(t.closed_positions),
    min: MIN_CLOSED,
    unit: "closed",
    fmt: (v) => `${v.toFixed(1)}R`,
  },
  {
    key: "hold",
    label: "hold",
    sentence:
      "Median hold — the middle length of a closed trade, from entry to stated exit.",
    value: (t) => fnum(t.median_hold_days),
    n: (t) => fnum(t.closed_positions),
    min: MIN_CLOSED,
    unit: "closed",
    fmt: (v) => `${Math.round(v)}d`,
  },
  {
    key: "preach",
    label: "preach",
    sentence:
      "Practise vs preach — when a trade links to a principle he named, how often he followed it.",
    value: (t) => fnum(t.preach_score),
    // The summary payload does not carry the linked-trade count today. A
    // missing n is below the §6 minimum by construction, so the row shows the
    // honest dash/"too few" until the API exposes it — never a guessed n.
    n: () => null,
    min: MIN_LINKED,
    unit: "linked",
    fmt: (v) => `${pct(v)}%`,
  },
];

// The threshold state of one value. Below the minimum the bar dims and the
// value is an em dash + "too few"; a value that exists with enough history is
// rendered by the question's fmt; a value that is simply unstated (enough
// history, no statement) is a plain em dash.
function rateState(value, n, min) {
  const enough = n !== null && n >= min;
  if (value === null && !enough) return { enough: false, text: "— too few" };
  if (value === null) return { enough: true, text: "—" };
  if (!enough) return { enough: false, text: "— too few" };
  return { enough: true, text: null };
}

// The one-ranked-question view. One row per trader, bar width proportional to
// the value within the max, value + n always visible.
function QuestionRank({ traders, question }) {
  const rows = traders
    .map((t) => {
      const value = question.value(t);
      const n = question.n(t);
      const st = rateState(value, n, question.min);
      return { handle: t.handle, value, n, st };
    })
    // Ranked by the selected metric, biggest first; a null value sinks.
    .sort((a, b) => {
      const av = a.value === null ? -Infinity : a.value;
      const bv = b.value === null ? -Infinity : b.value;
      return bv - av;
    });
  const max = Math.max(1, ...rows.map((r) => r.value ?? 0));

  if (rows.length === 0) {
    return <p className="empty">No traders configured yet. Add tracked handles to start pulling in their posts.</p>;
  }

  return (
    <>
      <ol
        className="traders-rank"
        aria-label={`Ranked by: ${question.sentence}`}
      >
        {rows.map((r) => {
          const w = r.value === null ? 0 : Math.max(0, Math.min(100, (r.value / max) * 100));
          const valueText = r.st.text || question.fmt(r.value);
          const finding = r.st.text
            ? `@${r.handle}: ${r.st.text} (${r.n === null ? "n not stated" : `n=${r.n}`})`
            : `@${r.handle}: ${question.fmt(r.value)}, n=${r.n}`;
          return (
            <li
              key={r.handle}
              className={`q-row${r.st.text ? " below" : ""}`}
              aria-label={finding}
            >
              <span className="q-handle mono">@{r.handle}</span>
              <span className="q-track" aria-hidden="true">
                <span
                  className={`q-fill${r.st.text ? " dim" : ""}`}
                  style={{ width: `${w}%` }}
                />
              </span>
              <span className="q-value mono">{valueText}</span>
              <span className="q-n mono">{r.n === null ? "n=—" : `n=${r.n}`}</span>
            </li>
          );
        })}
      </ol>
      {/* Protected copy — handoff, below-threshold gloss. Verbatim. */}
      <p className="footnote">
        A dim bar means too little history to lean on. A dash means we won't guess.
      </p>
    </>
  );
}

// Roster sort — nulls sink to the bottom, strings by locale, everything else
// numeric. Same pattern the Ledger table sets (F7/F9).
function sortTraders(rows, key, dir) {
  if (!key) return rows;
  const mul = dir === "asc" ? 1 : -1;
  const get = {
    handle: (t) => t.handle || "",
    tier: (t) => t.tier || "",
    posts: (t) => t.posts,
    open: (t) => t.open_positions,
    closed: (t) => t.closed_positions,
    hold: (t) => t.median_hold_days,
    win: (t) => t.stated_win_rate,
    preach: (t) => t.preach_score,
  }[key];
  return [...rows].sort((a, b) => {
    const av = get(a);
    const bv = get(b);
    if (av === null || av === undefined) return bv === null || bv === undefined ? 0 : 1;
    if (bv === null || bv === undefined) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * mul;
    return (av - bv) * mul;
  });
}

// Roster cell for a rate (win / preach). §6 applies to every percentage: below
// 10 closed positions a trader has no rate, so the cell reads "— too few" —
// never a bare percentage, never an invented read.
function rosterRate(t, field) {
  const v = fnum(t[field]);
  const n = fnum(t.closed_positions);
  const enough = n !== null && n >= MIN_CLOSED;
  if (v === null) return enough ? "—" : "— too few";
  if (!enough) return "— too few";
  return `${pct(v)}%`;
}

// ---------------------------------------------------------------------------
// Detail profile — fetched on selection (existing behaviour, restyled).
// ---------------------------------------------------------------------------

// Posting cadence for the CalendarGrid: everything /api/feed has for this
// handle, paged. Reply roots the API pulls back for thread completeness may
// belong to other handles, so the cadence counts only matching rows — an
// honest per-trader count.
async function fetchCadence(handle) {
  let offset = 0;
  const mine = [];
  for (;;) {
    const page = await fetchFeed({ handle, limit: 100, offset });
    const rows = page?.posts || [];
    mine.push(...rows.filter((p) => p?.handle === handle));
    const next = page?.pagination?.next_offset;
    if (next === null || next === undefined) break;
    offset = next;
  }
  return mine;
}

function cadenceCells(posts) {
  const byDay = new Map();
  for (const p of posts) {
    const day = (p.ts_ist || "").slice(0, 10);
    if (day) byDay.set(day, (byDay.get(day) || 0) + 1);
  }
  const days = [...byDay.keys()].sort();
  return {
    cells: days.map((date) => ({ date, count: byDay.get(date) })),
    from: days[0] || null,
    to: days[days.length - 1] || null,
  };
}

// Play-type mix for the StackedArea. post_class.play_type exists in the DB but
// /api/feed does not select it, so nothing can be bucketed client-side today.
// The derivation is written against the payload field so the chart lights up
// the moment the API exposes it; until then the labelled empty state is the
// truth — never a chart of proxy labels.
function playMixRows(posts) {
  const byDay = new Map(); // day -> Map(label -> count)
  for (const p of posts || []) {
    const play = p?.play_type;
    if (!play) continue;
    const day = (p.ts_ist || "").slice(0, 10);
    if (!day) continue;
    let seg = byDay.get(day);
    if (!seg) {
      seg = new Map();
      byDay.set(day, seg);
    }
    seg.set(play, (seg.get(play) || 0) + 1);
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
    .map(([x, seg]) => ({
      x,
      segments: [...seg.entries()]
        .sort(([a], [b]) => (a < b ? -1 : 1))
        .map(([label, value]) => ({ label, value })),
    }));
}

function PlayMix({ posts, loading }) {
  const rows = playMixRows(posts || []);
  if (loading) return null;
  if (!rows.length || !StackedArea) {
    return (
      <div className="chart-empty" role="img" aria-label="Play-type mix can't be drawn yet">
        Play-type labels are not in the feed payload yet — the mix over time can't be drawn.
      </div>
    );
  }
  const total = rows.reduce(
    (sum, r) => sum + r.segments.reduce((a, b) => a + b.value, 0),
    0
  );
  return <StackedArea rows={rows} n={total} suffix="" />;
}

function Cadence({ posts, error, loading }) {
  if (loading) return null;
  if (error) {
    return (
      <div className="chart-empty" role="img" aria-label="Posting cadence feed unavailable">
        Posting cadence — the feed is unavailable right now.
      </div>
    );
  }
  const { cells, from, to } = cadenceCells(posts || []);
  if (!cells.length || !CalendarGrid) {
    return (
      <div className="chart-empty" role="img" aria-label="No posting days to chart">
        Posting cadence — no timestamped posts to chart yet.
      </div>
    );
  }
  return <CalendarGrid from={from} to={to} cells={cells} caption="posts per day" />;
}

function gatedEvidence(v, n, min, fmt) {
  if (v === null) return "—";
  if (n === null || n < min) return "—";
  return fmt(v);
}

function Profile({ handle, onNavigate }) {
  const { data, error } = useApi(() => fetchTrader(handle), [handle]);
  const cadence = useApi(() => fetchCadence(handle), [handle]);

  if (error) return <ErrorBox error={error} />;
  if (!data || !data.trader) return <Loading />;

  const t = data.trader;
  const s = data.style;
  const openN = (data.open || []).length;
  const closedN = (data.closed || []).length;

  // Lead figure: the stated win rate is the ONE dominant number, honest about
  // its denominator and §6 threshold.
  const win = fnum(s?.stated_win_rate);
  const winN = closedN;
  const winSt = rateState(win, winN, MIN_CLOSED);

  const avgR = gatedEvidence(fnum(s?.avg_r), winN, MIN_CLOSED, (v) => `${v.toFixed(1)}R`);
  const holdEv = gatedEvidence(fnum(s?.median_hold_days), winN, MIN_CLOSED, (v) => `${Math.round(v)}d`);
  const preach = gatedEvidence(fnum(s?.preach_score), null, MIN_LINKED, (v) => `${pct(v)}%`);

  // Hold-time StripPlot from the positions payload (available without the
  // style pass); the median falls back to the style figure when stated.
  const holdDays = (data.closed || [])
    .map((p) => fnum(p.holding_days))
    .filter((v) => v !== null);
  const holdMedian = median(holdDays) ?? fnum(s?.median_hold_days);

  // Stop-discipline Dumbbell: stated vs honoured, 0-100 scale.
  const stated = fnum(s?.stop_stated_pct);
  const honored = fnum(s?.stop_honored_pct);
  const dumbbellRows =
    stated !== null && honored !== null
      ? [{
          label: "stop discipline",
          a: { value: pct(stated), label: "stated" },
          b: { value: pct(honored), label: "honoured" },
        }]
      : [];

  return (
    <Panel title={`@${t.handle}`} right={<Chip kind={t.tier}>{String(t.tier || "").toLowerCase()}</Chip>}>
      {s ? (
        <div className="traders-lead">
          <div className={`traders-lead-num${winSt.enough ? "" : " dim"}`}>
            {winSt.text || `${pct(win)}%`}
          </div>
          <div className="traders-lead-gloss">
            stated win rate — of {winN} closed
            {winSt.enough ? "" : ", too few to lean on"}
          </div>
          <div className="traders-evidence">
            avg result {avgR} · median hold {holdEv} · practises what he preaches {preach}
          </div>
        </div>
      ) : (
        <p className="traders-future">
          No style profile yet — the style pass over closed positions (W6) hasn't
          landed. Every scored figure on this screen shows the honest "too few"
          state until it does; nothing here is guessed.
        </p>
      )}

      <div className="traders-chartlabel">Stop discipline</div>
      {dumbbellRows.length > 0 ? (
        <Dumbbell rows={dumbbellRows} max={100} gapWarn={10} suffix="%" n={fnum(s?.n_positions)} />
      ) : (
        <div className="chart-empty" role="img" aria-label="Stop discipline data unavailable">
          Stop discipline — no stated-vs-honoured pair yet. It arrives with the style pass.
        </div>
      )}

      <div className="traders-chartlabel">Hold days</div>
      <StripPlot
        values={holdDays}
        median={holdMedian !== null ? Math.round(holdMedian) : undefined}
        suffix="d"
      />

      <div className="traders-chartlabel">Play-type mix</div>
      <PlayMix
        posts={cadence.data || []}
        loading={cadence.data === null && !cadence.error}
      />

      <div className="traders-chartlabel">Posting cadence</div>
      <Cadence
        posts={cadence.data || []}
        error={cadence.error}
        loading={cadence.data === null && !cadence.error}
      />

      <div className="traders-chartlabel">Open now · {openN}</div>
      {openN === 0 && <p className="empty">Nothing open.</p>}
      {openN > 0 && (
        <table className="traders-open">
          <tbody>
            {data.open.map((p) => (
              <tr key={p.position_id}>
                <td>
                  {/* The --risk marker means money is risked right now. The
                      button is the existing symbol jump to LEDGER. */}
                  <span className="risk-dot" aria-hidden="true" />
                  <button
                    type="button"
                    className="traders-symlink"
                    onClick={() => onNavigate?.("LEDGER", { symbol: p.symbol })}
                  >
                    <strong>{p.symbol}</strong>
                  </button>
                </td>
                <td>{p.status}</td>
                <td className="num">
                  {p.holding_days != null ? `${p.holding_days}d` : "—"}
                </td>
                <td>
                  {p.unresolved?.length > 0 && (
                    <span className="row-note">⚠ {p.unresolved.join(" · ")}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

export default function Traders({ presetHandle, onNavigate }) {
  const { data, error } = useApi(fetchTraders, []);
  const [questionKey, setQuestionKey] = React.useState("stop");
  const [selected, setSelected] = React.useState(presetHandle || null);
  const [sortKey, setSortKey] = React.useState(null);
  const [sortDir, setSortDir] = React.useState("asc");

  // Deep link: ?tab=TRADERS&handle=X opens that trader. Only follows the prop
  // when it actually changes, so an in-session selection is never overridden.
  React.useEffect(() => {
    if (presetHandle) setSelected(presetHandle);
  }, [presetHandle]);

  React.useEffect(() => {
    if (!selected && data?.traders?.length) setSelected(data.traders[0].handle);
  }, [data, selected]);

  function onSort(key) {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  const question = QUESTIONS.find((q) => q.key === questionKey) || QUESTIONS[0];
  const traders = sortTraders(data?.traders || [], sortKey, sortDir);

  return (
    <div className="traders">
      <ErrorBox error={error} />

      <Panel>
        <p className="kicker">The question</p>
        <p className="traders-question">{question.sentence}</p>
        <Segmented
          options={QUESTIONS.map((q) => q.label)}
          value={question.label}
          onChange={(label) => {
            const q = QUESTIONS.find((x) => x.label === label);
            if (q) setQuestionKey(q.key);
          }}
        />
        {!data && !error && <Loading />}
        {data && (
          <QuestionRank traders={data.traders || []} question={question} />
        )}
      </Panel>

      {data?.traders?.length > 0 && (
        <Panel title="Roster">
          <table className="traders-roster">
            <thead>
              <tr>
                <th aria-hidden="true" />
                <SortableTh label="handle" active={sortKey === "handle"} dir={sortDir} onClick={() => onSort("handle")} />
                <SortableTh label="tier" active={sortKey === "tier"} dir={sortDir} onClick={() => onSort("tier")} />
                <SortableTh label="posts" className="num" active={sortKey === "posts"} dir={sortDir} onClick={() => onSort("posts")} />
                <SortableTh label="open" className="num" active={sortKey === "open"} dir={sortDir} onClick={() => onSort("open")} />
                <SortableTh label="closed" className="num" active={sortKey === "closed"} dir={sortDir} onClick={() => onSort("closed")} />
                <SortableTh label="hold" className="num" active={sortKey === "hold"} dir={sortDir} onClick={() => onSort("hold")} />
                <SortableTh label="win" className="num" active={sortKey === "win"} dir={sortDir} onClick={() => onSort("win")} />
                <SortableTh label="preach" className="num" active={sortKey === "preach"} dir={sortDir} onClick={() => onSort("preach")} />
              </tr>
            </thead>
            <tbody>
              {traders.map((t) => (
                <tr key={t.handle}>
                  <td>
                    {/* Keyboard-reachable — a real disclosure button, never a
                        bare row click. One trader open at a time. */}
                    <Disclosure
                      open={selected === t.handle}
                      onToggle={() => setSelected(t.handle)}
                    />
                  </td>
                  <td><strong>@{t.handle}</strong></td>
                  <td><Chip kind={t.tier}>{String(t.tier || "").toLowerCase()}</Chip></td>
                  <td className="num mono">{t.posts}</td>
                  <td className="num mono">{t.open_positions}</td>
                  <td className="num mono">{t.closed_positions}</td>
                  <td className="num mono">
                    {fnum(t.median_hold_days) === null
                      ? "—"
                      : `${Math.round(t.median_hold_days)}d`}
                  </td>
                  <td className="num mono">{rosterRate(t, "stated_win_rate")}</td>
                  <td className="num mono">{rosterRate(t, "preach_score")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      )}

      {selected && <Profile handle={selected} onNavigate={onNavigate} />}
    </div>
  );
}