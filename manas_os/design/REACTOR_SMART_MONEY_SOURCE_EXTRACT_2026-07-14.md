# Reactor / Smart Money Source Extract

**Frozen:** 2026-07-14  
**Source:** `C:\Users\satta\Downloads\NoteGPT_Transcript_How To Track Smart Money Footprint In Indian Stock Market  Proper Step By Step Video.txt`  
**Encoding:** UTF-8  
**Size:** 138,017 bytes  
**Lines:** 209  
**SHA-256:** `818DC042FDF51D77B4B3E7B801C2105F6A508FD23DD137C9EE6E54FC31A94DFA`

This file is the frozen, source-fidelity extraction layer for the Reactor Scale
reverse-engineering work. It paraphrases the supplied transcript rather than
silently converting the speaker's interpretation into proven market fact.

## Traceable source claims

| Transcript lines | Source claim, faithfully paraphrased | Product consequence |
|---|---|---|
| 13-15 | The presenter introduces a free tool as a way to use the sheet without a paid Volume Footprint indicator. | The substitute tool is part of interpretation and execution; it is not evidence that the sheet itself is a Volume Profile calculation. |
| 31-43 | The stated mechanism is unusually large order quantity relative to a stock's normal activity. The presenter illustrates normal order count and average quantity, then says a large participant must place larger quantity and the system catches that activity. | Test `volume / number_of_trades` and its causal rolling baseline before generic relative volume or delivery-only hypotheses. |
| 43-55 | Larger scores represent larger abnormal activity. The speaker treats below 3.5 as normal and above 3.5 as abnormal, then filters for at least three consecutive sessions; the threshold or run length can be tightened. | Preserve the supplied `>3.5` convention as benchmark semantics, plus separate persistence and isolated-spike states. It is not yet a validated alpha threshold. |
| 51-55 | A large participant may spread activity over several days; the activity can be accumulation or distribution. | A multi-day trail is essential, and the signal remains direction-neutral. |
| 59-61 | A high activity score alone does not identify accumulation or distribution; the chart supplies direction. | The Reactor cannot emit BUY/SELL by itself. |
| 61-65, 103-105 | Splits and related quantity changes can create distorted readings that the presenter says to ignore. | Corporate-action quarantine is mandatory before scoring and before learning from outcomes. |
| 67-75 | The presenter checks the broader trend and a larger timeframe before considering an entry. | Regime and higher-timeframe structure precede execution. |
| 79-93 | A Fixed Range Volume Profile is drawn over a selected prior swing/activity range. Important levels are taken from that profile, and an entry is considered only after price breaks the relevant range with supportive volume/close behaviour. | Store the exact profile anchor range and bar resolution; POC/VAH/VAL are range-dependent execution context. |
| 93-101 | The stop is derived from structure and position size is considered before entry. | Use sat10ic's existing deterministic risk engine. The speaker's illustrative risk percentage is not a sat10ic sizing rule. |
| 107-109 | The presenter interprets an isolated very high reading as capable of preceding a sharp move and repeated readings as capable of preceding a longer move. | Display spike and persistence separately, then validate both against future path outcomes. |
| 113-119 | The POC is used as an important reference and a stock can be rejected despite a high activity reading if the required structural break is absent. | Profile/structure confirmation can veto an activity candidate for the selected execution lens. |
| 121-127 | High activity can represent selling/distribution; the presenter avoids an equity long when structure points down. | Direction must be resolved after activity detection. |
| 141-147 | Continuous activity plus upside price direction is interpreted by the presenter as buying pressure that can support a longer hold. | The LLM must reason over the activity sequence and price response together, not recite the score. |
| 151-163 | The presenter favours structure-aware trailing over a rigid target. | Outcome and journal records need trailing/exit-path fields, not only fixed-horizon returns. |
| 164-167 | The transcript explicitly states that the data reports activity, not direction; buying and selling are both possible. Volume Profile and price behaviour are used to infer direction. | This is the canonical Reactor semantic contract. |
| 187-189 | The sheet is described as covering roughly 1,600-1,700 liquid stocks and carrying sector/industry filters. | Universe provenance and liquidity eligibility must be shown rather than implied. |
| 191-193 | The speaker distinguishes Volume Footprint from the free Volume Profile: the former is tied to candle activity/volatility, while the latter is used to judge where a trade may be taken. | Do not use the terms interchangeably in code, UI, or debate prompts. |
| 195-199 | Higher values are described as more abnormal activity, and the speaker presents the tool as best suited to swing trading when combined with price action/technical analysis. | Treat the score as a ranking input for swing candidates, not a self-contained signal. |
| 203-205 | VAH, VAL and POC must be enabled in the profile. The formula owner declines to reveal how the score is calculated and calls it proprietary. | Exact formula fidelity remains unproven even when an EOD mimic fits the supplied labels closely. |

## POC, VAH and VAL interpretation used by sat10ic

The user-supplied quick guide is useful as a beginner mnemonic, with three
necessary safeguards:

- **POC** is the highest-volume price within the explicitly selected profile
  range. Price near POC shows acceptance/balance around that price; it does not,
  by itself, prove accumulation.
- **VAL reaction** is a candidate support/rejection event. A long thesis still
  requires a reclaim or bullish response, compatible trend/context and a defined
  invalidation.
- **VAH break** is a candidate continuation event. A long thesis still requires
  acceptance above value (for example, a close/hold or breakout-retest), volume
  context and a defined invalidation.

The transcript does not specify the value-area percentage or a universal anchoring
algorithm. Those settings must be explicit and versioned; they must not be invented
and presented as source doctrine.

## Claims not promoted to facts

- The speaker's use of “smart money” and “institution” is an interpretation of
  abnormal activity, not proof of participant identity.
- Promotional return examples and testimonials are not alpha validation.
- The proprietary score formula is not disclosed in the source.
- Aggregate bhavcopy fields cannot reveal the maximum individual order, bid/ask
  aggressor, footprint delta or participant identity.

## Frozen implementation contract

```text
EOD abnormal-activity detection (direction-neutral)
-> persistence/spike classification
-> corporate-action and data-quality guard
-> regime + higher-timeframe structure
-> Fixed Range Volume Profile (POC/VAH/VAL with anchor provenance)
-> price/volume response and execution-lens interpretation
-> deterministic risk and position sizing
```

The Reactor score never becomes directional merely because a profile level is
available. The chart interpretation is a separate, traceable stage.
