// Plain label (beginner) ⇄ technical label (expert). One source of truth.
// From BEGINNER_EXPERT_SPEC §2 Axis A. Every density-aware component renders
// labelFor(key, expert) instead of a hardcoded technical string.
export const LABELS = {
  posture:      { plain: "Today's game plan",     tech: "Market posture" },
  xp:           { plain: "Market energy",          tech: "XP dial" },
  r4p5:         { plain: "Big-mover balance",      tech: "4.5R burst" },
  mbi:          { plain: "Day color",              tech: "MBI" },
  breadth20:    { plain: "How many stocks are healthy", tech: "Breadth 20d" },
  readiness:    { plain: "Match strength",         tech: "Readiness" },
  ep:           { plain: "Earnings surprise",      tech: "EP" },
  ants:         { plain: "Quiet accumulation",     tech: "ANTS" },
  avwap:        { plain: "Big-money average price", tech: "AVWAP" },
  rs:           { plain: "Leadership vs market",   tech: "RS line" },
  exit_state:   { plain: "Trade health",           tech: "Exit state" },
};

// Returns the plain label in beginner mode, the technical label in expert.
// Falls back to the key itself if unknown (defensive — never crashes render).
export const labelFor = (key, expert) => (LABELS[key]?.[expert ? "tech" : "plain"] ?? key);
