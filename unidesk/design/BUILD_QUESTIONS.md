# BUILD_QUESTIONS — open questions for the owner

**Newest batch at the top. Append-only. Answered questions move to the bottom
with the answer recorded — never deleted.**
**Channel note:** this file is the durable channel; the chat response is
transient. An unanswered question must never become a silent assumption in
code — each carries a default and its reversibility, or the node stays BLOCKED.

---

## BATCH 1 — 2026-09-04, 7 open (E8 blocks the entire Risk Desk wave)

### Q1 · E8 — Approve the X-03 charter amendment?
BLOCKS      N-42, N-43, N-44, N-45, N-46, N-47, N-48, N-49 (the whole Risk Desk wave past the draft)
QUESTION    May the Risk Desk compute position sizes by deterministic arithmetic
            over YOUR inputs (risk fraction, equity, stop), while the rule
            "no model output may author risk" stays in force?
OPTIONS     (a) Approve the amendment as drafted (X03_AMENDMENT_DRAFT.md)
            (b) Approve with changes (mark up the draft)
            (c) Reject — the Playbook stays no-numbers, Risk Desk stays descriptive-only
RECOMMEND   Approve as drafted: the amendment narrows the rule to the regime→playbook
            mapping only, keeps every charter guard (§22.1, no automatic Governor),
            and the acceptance test (remove the risk-fraction input → every size
            output disappears) makes the calculator honest by construction.
IF UNANSWERED  N-42.. stay BLOCKED. I will not build past the draft.

### Q2 · E9 — Default risk fraction and maximum position size
BLOCKS      N-43 (Trade Planner), N-44, N-45 (and therefore N-46..N-49)
QUESTION    What risk per trade and maximum position size should the planner use as
            the SOURCE_PRESET defaults?
OPTIONS     (a) 0.5% risk per trade / 40% max position (source-spec range midpoint)
            (b) 0.3% risk per trade / 25% max position (conservative end)
            (c) your own numbers (state them; they ship as SOURCE_PRESET with your label)
RECOMMEND   Do not recommend — this is your capital and your risk appetite. The spec
            stores whichever you pick as a named, editable SOURCE_PRESET, never a
            silent default.
IF UNANSWERED  N-43 stays BLOCKED: the planner ships schema-only, planner fields
            render "— (no risk fraction approved)". Reversible: defaults plug in
            the moment you answer.

### Q3 · E9 — Open-risk ceiling (portfolio heat cap)
BLOCKS      N-44 (Portfolio Heat), N-47 (Governor)
QUESTION    What is the maximum total open risk (sum of planned risk across open
            positions) as a percent of capital?
OPTIONS     (a) 2% of capital   (b) 5%   (c) 10%   (d) your own number
RECOMMEND   Do not recommend — same reason as Q2.
IF UNANSWERED  N-44 renders the heat metre with the ceiling field empty and a
            named gap; the Governor has no threshold to propose against.

### Q4 · E10 — Risk Governor: propose-and-confirm forever?
BLOCKS      N-47 (Governor design)
QUESTION    Should the Risk Governor ever ACT automatically (move stops, cut size),
            or is it propose-and-confirm only, permanently?
OPTIONS     (a) Propose-and-confirm permanently (v1 as specified)
            (b) Propose-and-confirm now; revisit automation after 3 months of use
            (c) Allow automatic stops only (never size changes), owner-toggled
RECOMMEND   (a) — the Governor acting on your behalf without a confirmation is the
            one thing the charter was written to prevent.
IF UNANSWERED  N-47 builds propose-and-confirm (the safe reading). Reversible only
            by an owner toggle, so the default is conservative.

### Q5 · E1 — Flip `ipo_base` trust from BLOCKED?
BLOCKS      N-23 escalation; unlocks ipo_base candidates for ranking
QUESTION    The listing calendar now verifies listing age (the reason for the
            BLOCKED verdict is resolved). Flip `ipo_base` to rankable?
OPTIONS     (a) Flip to rankable (listing-age reason is resolved; other caveats remain)
            (b) Keep BLOCKED one more cycle — validate the listing feed first
RECOMMEND   (a) — the documented reason for the BLOCK is now satisfied by real
            data (2,570 listings, ISIN-carried), and the detector itself was
            already VERIFIED on its other rules.
IF UNANSWERED  ipo_base stays BLOCKED — no code change, no risk, just fewer candidates.

### Q6 · E2 — Run the ~2,300-session never-attached backfill?
BLOCKS      Research/History totals change scope; delayed-EP and EP validation
            population grows
QUESTION    Run the archive pass that creates event partitions for ~2,300 sessions
            that never had one (2010-2016 era, before detectors existed)?
OPTIONS     (a) Run it now (B2-3 worker is idle after the 149 finish — extends the run)
            (b) Skip permanently — the pre-detector era adds little to edge validation
            (c) Defer to a weekend run
RECOMMEND   (b) Skip — sessions before the detector suite existed produce events
            from a different regime than anything the desk will trade; their
            validation value is low and their distortion of totals is real.
IF UNANSWERED  I skip it (reversible — the resume driver picks it up any time).

### Q7 · Account equity and MTF
BLOCKS      N-43 (planner outputs are rupee-quantities only with equity set)
QUESTION    What is the trading capital the planner should size against, and is MTF
            (margin) in use at all?
OPTIONS     (a) Equity: ₹[amount] · MTF: no
            (b) Equity: ₹[amount] · MTF: yes (then MTF haircuts and rates are also needed)
            (c) Prefer not to say — planner renders % and R figures only, never rupee qty
RECOMMEND   (c) if you prefer not to store equity in the tool: percent-based sizing
            works without it; rupee outputs stay "—" with the gap named.
IF UNANSWERED  Planner renders percent figures only; rupee quantity stays "—" with
            the gap named. Fully reversible when you answer.

---

## ANSWERED (oldest last)

*(none yet)*
