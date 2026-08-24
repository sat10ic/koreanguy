// STYLE — dev-only reference sheet for the shared primitives (ui.jsx +
// charts.jsx), restyled to the SCOUTING × WIRE tokens (2026-08-24).
//
// Not one of the six product tabs. Renders every primitive against inline
// sample data — no API calls — so it always renders, even against an empty
// database, and so a future model has one place to copy correct usage from.
// Reachable only via ?tab=STYLE.
import React from "react";
import {
  Panel, Chip, Conf, Num, Pct, Bar, Empty, Segmented, SortableTh, Disclosure, Stat,
} from "../components/ui.jsx";
import {
  PositionBars, Dumbbell, StripPlot, BandLine, Ribbon, StackedStrip, SmallMultiples,
} from "../components/charts.jsx";

// ---- inline sample data -----------------------------------------------
const POSITION_ROWS = [
  {
    id: "dixon", label: "DIXON", sublabel: "@manas_arora",
    start: "2026-08-01", end: "2026-08-24", result: 9.9,
    events: [{ at: "2026-08-09", kind: "sl_up" }],
  },
  {
    id: "bel", label: "BEL", sublabel: "@swing_ka_sultan",
    start: "2026-07-22", end: "2026-08-19", result: 8.7,
    events: [{ at: "2026-08-02", kind: "add" }],
  },
  {
    id: "kpit", label: "KPITTECH", sublabel: "@swing_ka_sultan",
    start: "2026-08-06", end: null, result: null, warn: "no stop stated",
    events: [],
  },
];

const DUMBBELL_ROWS = [
  { label: "stop discipline", a: { value: 71, label: "stated" }, b: { value: 62, label: "honoured" } },
  { label: "sizing discipline", a: { value: 80, label: "stated" }, b: { value: 77, label: "honoured" } },
];

const HOLD_DAYS = [3, 5, 5, 6, 9, 11, 11, 14, 19, 21, 28];

const XP_POINTS = Array.from({ length: 24 }, (_, i) => {
  const base = 12 + 20 * Math.abs(Math.sin(i / 3.2));
  return { x: `d${i}`, y: Math.round(base * 10) / 10 };
});
const XP_BANDS = [
  { at: 15, label: "low" },
  { at: 40, label: "building" },
  { at: 100, label: "strong" },
];

const RIBBON_CELLS = Array.from({ length: 40 }, (_, i) => {
  const roll = (i * 37) % 10;
  const state = roll < 4 ? "GREEN" : roll < 7 ? "WHITE" : roll < 9 ? "RED" : "NONE";
  const d = new Date(2026, 6, 1 + i).toISOString().slice(0, 10);
  return { key: d, state, warn: state === "RED" && i % 6 === 0, title: `${d} · ${state}` };
});

const SECTOR_SEGMENTS = [
  { label: "CAPITAL GOODS", value: 24 },
  { label: "AUTO", value: 18 },
  { label: "PHARMA", value: 12 },
  { label: "OTHERS", value: 46 },
];

const PLAY_SEGMENTS = [
  { label: "breakout", value: 61 },
  { label: "pullback", value: 24 },
  { label: "ep", value: 15 },
];

const SMALL_MULTIPLES_ITEMS = [
  { label: "@swingdesk", values: [1, 2, 5, 7, 6, 3, 2, 1], caption: "+18% · 21 pos" },
  { label: "@baseandgo", values: [1, 1, 3, 4, 6, 7, 7, 5], caption: "+9% · 14 pos" },
  { label: "@tapewatcher", values: [2, 3, 2, 1, 1, 2, 3, 2], caption: "-2% · 9 pos" },
  { label: "@ipobase", values: [1, 1, 1, 2, 1, 1, 1, 1], caption: "— · 2 pos" },
];

function Swatch({ title, cite, children }) {
  return (
    <div className="swatch">
      <div className="swatch-title">{title}</div>
      {children}
      {cite && <div className="chart-caption">{cite}</div>}
    </div>
  );
}

function Pair({ label1 = "populated", label2 = "empty", children1, children2 }) {
  return (
    <div className="swatch-pair">
      <div>
        <div className="cell-label">{label1}</div>
        {children1}
      </div>
      <div>
        <div className="cell-label">{label2}</div>
        {children2}
      </div>
    </div>
  );
}

export default function Style() {
  const [segVal, setSegVal] = React.useState("20d");
  const [sortDir, setSortDir] = React.useState("desc");
  const [sortActive, setSortActive] = React.useState(true);
  const [open, setOpen] = React.useState(false);

  return (
    <div className="style-gallery">
      <p className="page-lede">
        Reference sheet for every shared chart and control — restyled to the scouting × wire
        tokens (dark ground, ink ladder, one accent). Inline sample data, no API calls: this
        screen renders even with an empty database. Not one of the six product tabs.
      </p>

      <Panel title="PositionBars" cite="§2.1 — shared time axis, one row per position">
        <Pair
          children1={
            <PositionBars from="2026-07-20" to="2026-08-24" rows={POSITION_ROWS} onRowClick={() => {}} />
          }
          children2={<PositionBars from="2026-07-20" to="2026-08-24" rows={[]} />}
        />
      </Panel>

      <Panel title="Dumbbell" cite="§2.2 — the gap is the finding">
        {/* n is passed here on purpose: this gallery is the reference sheet
            other models copy from, and §1 requires a denominator beside every
            percentage. A sample without it would teach the wrong pattern. */}
        <Pair
          children1={<Dumbbell rows={DUMBBELL_ROWS} max={100} gapWarn={10} suffix="%" n={183} />}
          children2={<Dumbbell rows={[]} max={100} gapWarn={10} suffix="%" />}
        />
      </Panel>

      <Panel title="StripPlot" cite="§2.3 — one tick per observation, median ruled">
        <Pair
          children1={<StripPlot values={HOLD_DAYS} median={11} suffix="d" />}
          children2={<StripPlot values={[]} suffix="d" />}
        />
      </Panel>

      <Panel title="BandLine" cite="§2.4 — line + flat threshold bands, generalises XP">
        <Pair
          children1={<BandLine points={XP_POINTS} bands={XP_BANDS} log />}
          children2={<BandLine points={[]} bands={XP_BANDS} log />}
        />
      </Panel>

      <Panel title="Ribbon" cite="§2.5 — one small rect per session, generalises MBI">
        <Pair
          children1={<Ribbon cells={RIBBON_CELLS} />}
          children2={<Ribbon cells={[]} />}
        />
      </Panel>

      <Panel title="StackedStrip" cite="§2.6 — proportional composition, labelled in place, never a pie">
        <Pair
          label1="sector tilt" label2="empty"
          children1={<StackedStrip segments={SECTOR_SEGMENTS} n={183} suffix="%" />}
          children2={<StackedStrip segments={[]} />}
        />
        <div style={{ marginTop: 14 }}>
          <div className="cell-label">play-type mix</div>
          <StackedStrip segments={PLAY_SEGMENTS} n={183} suffix="%" />
        </div>
      </Panel>

      <Panel title="SmallMultiples" cite="§2.7 — grid of miniatures on a SHARED scale">
        <Pair
          children1={<SmallMultiples items={SMALL_MULTIPLES_ITEMS} />}
          children2={<SmallMultiples items={[]} />}
        />
      </Panel>

      <Panel title="Segmented" cite="§3 — mutually exclusive views, ≤4 options">
        <div className="row-sample">
          <Segmented options={["5d", "20d", "90d"]} value={segVal} onChange={setSegVal} />
          <span className="unstated">value = {segVal}</span>
        </div>
      </Panel>

      <Panel title="SortableTh" cite="§3 — sortable column headers with a caret">
        <table className="sample-table" style={{ maxWidth: 360 }}>
          <thead>
            <tr>
              <SortableTh
                label="symbol"
                active={sortActive && true}
                dir={sortDir}
                onClick={() => {
                  setSortActive(true);
                  setSortDir(sortDir === "asc" ? "desc" : "asc");
                }}
              />
              <SortableTh label="net" className="num" active={false} dir="asc" onClick={() => {}} />
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>DIXON</td>
              <td className="num"><Pct value={9.9} /></td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel title="Disclosure" cite="§3 — a real caret, not a bare row click">
        <div className="row-sample">
          <Disclosure open={open} onToggle={() => setOpen((o) => !o)} />
          <span className="unstated">{open ? "open" : "closed"}</span>
        </div>
      </Panel>

      <Panel title="Stat" cite="§3/§10.1 — the explained-stat: a value with its meaning in plain English beneath">
        <div className="row-sample">
          <Stat
            value="7.3"
            meaning="Only a few stocks are pushing higher. Breakouts fail more often in a market like this."
            n={446}
          />
          <Stat value={null} meaning="this meaning is never shown — the dash speaks first" />
        </div>
      </Panel>

      <Panel title="Existing primitives, for reference" cite="ui.jsx — unchanged exports">
        <div className="row-sample">
          <Chip kind="CORE">CORE</Chip>
          <Chip kind="trade_event">TRADE EVENT</Chip>
          <Conf value={0.91} />
          <Num value={1847} prefix="₹" />
          <Pct value={-4.2} />
          <Bar pct={62} tone="amber" />
          <Empty>no data example</Empty>
        </div>
      </Panel>
    </div>
  );
}