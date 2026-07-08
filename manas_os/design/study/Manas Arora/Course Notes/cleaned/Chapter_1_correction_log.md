# Chapter 1 Correction Log — Fear Management

Source: `Manas Arora/Course Notes/CH1 Fear Management.md`

Cleaned: `Manas Arora/Course Notes/cleaned/Chapter_1.md`

## High-confidence fixes applied inline

| Raw ASR | Cleaned | Reason |
|---|---|---|
| `write it / writing` in trade-holding context | `ride it / riding` | Spoken trading context: holding a winner, ride-management chapters. |
| `30 to 50 breaks` | `30 to 50 trades` | Context is first learning trades; “breaks” is ASR slip. |
| `stock level` | `stop level` | Context is cutting losses. |
| `stocked out` | `stopped out` | Trading exit context. |
| `increases back to 2%` | `retraces back to 2%` | Context: stock goes up 5%, profit falls to 2%. |
| `20-hour trade` | Flagged as likely `20R trade` | Strong guess, but “20R” is a number/risk unit, so flagged instead of silently fixed. |

## Open flags added to `TRANSCRIPT_QUERIES.md`

- 1-a — “lost on 5%” wording.
- 1-b — “20-hour trade” likely 20R.
- 1-c — “GBMA” ticker/name.
- 1-d — “first one person lower” phrase in the 3% profit comment.
