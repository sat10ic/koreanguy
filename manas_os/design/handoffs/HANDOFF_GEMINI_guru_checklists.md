# HANDOFF 6 — Configurable mentor/guru checklists, Arora first (Gemini)

Repo `C:\Users\satta\Downloads\koreanguy`, branch `emergent`. Standing rules: HANDOFF_INDEX.md.
Long-standing task #17: the user's OWN mentors (Manas Arora / TradeTM / StocksGeeks), not US gurus.

## Sources (ground every checklist item in the corpus — source-fidelity is binding)
- `manas_os/design/knowledge/ARORA_SHARDS_NUANCES.md`, `TRADETM_NUANCES*.md`,
  `STOCKGEEKS_NUANCES.md`, `PLAYBOOK_TO_TOOL_MAP.md`, `INDIA_PLAYBOOK.md`
- `manas_os/design/study/Manas Arora/Course Notes/` (cleaned chapters)
Every checklist item carries a `source_cite` (doc + section). NO invented items.

## Scope
1. **Data model**: `guru_checklists` table (additive): checklist id, mentor, name, ordered items
   (text, source_cite, kind: hard/soft), scope (entry/manage/exit/market). Seed with ONE
   shipped checklist: Manas Arora entry discipline (extract 8-15 concrete checks from the course
   notes — e.g. market breadth supportive, RS, stop distance sane, position-size rule, no
   averaging down, journal-before-entry — each cited).
2. **Evaluation, honest split**: for each item mark it AUTO (the tool can evaluate from existing
   data — map to the real field, e.g. breadth from regime snapshot, stop % from the plan) or
   MANUAL (user self-checks). AUTO items render checked/unchecked from live payload values via
   ONE server endpoint (`/api/checklists/{id}/evaluate?symbol&date`) — no client derivation;
   MANUAL items are user-tickable (persist ticks per symbol+date in a small table).
3. **UI**: a compact checklist panel on TRADE PLAN (primary) + optional DEBATE deep-dive
   disclosure, v5 idiom: each row = check state + item text + source cite chip; AUTO rows show
   the actual value ("stop 4.1% <= 5% cap"). Overall read = "N of M — and which HARD items fail";
   a failing HARD item renders amber warning text, but this is ADVISORY — it never blocks or
   alters the deterministic plan/gates.
4. **Configurability**: user can duplicate a checklist and toggle items on/off (no free-text item
   creation this wave — keeps source-fidelity). CRUD endpoints additive.
5. **Tests**: seed + evaluate on a real-shaped fixture (AUTO mappings correct), manual-tick
   persistence, a HARD-fail renders advisory only.

## Do NOT
Let checklist state feed gates/sizing/verdicts. No US-guru content. No uncited items.

## Output
`HANDOFF_GEMINI_guru_checklists_COMPLETED.md`: the seeded Arora checklist with citations, the
AUTO-mapping table (item -> payload field), endpoints, test results, wiring notes.
