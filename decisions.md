# SwingEdge Lite Phase 1 Decisions

1. **Regime pillars**: *Are NF500EW / Nifty RSI / breadth / Nifty-vs-21EMA the right four for NSE?* 
   **Decision**: Yes, provisional default. We'll stick to these four for Phase 1 as they provide a solid mix of trend, momentum, breadth, and volatility/mean-reversion. India VIX is a nice-to-have but deferred to Phase 2.

2. **Purple Dot volume thresholds**: *The 10/5/3 lakh scaling is a first pass. Refine after backfill?* 
   **Decision**: 10/5/3 lakh is our provisional default. Manas loves "low float + sudden volume bursts" so keeping the threshold relatively low for smallcaps (3 lakh) makes sense to catch early demand.

3. **SMA20 reclaim**: *Strictly today-crosses-above, or allow 2-day tolerance?* 
   **Decision**: Allow 2-day tolerance. Indian markets frequently gap up; strict same-day cross might miss strong start (S in SVRO) gap-ups.

4. **Walk-forward window**: *12 months of 2025 includes which regimes?* 
   **Decision**: We'll use the last 12 months. Even if mostly RISK_ON, we will manually review drawdowns to ensure risk control ("perfect setups fail... job is risk control").

5. **Initial watchlist**: *Start with 30 names picked by Sunit or let secondary build it?* 
   **Decision**: Let the secondary signal list build the watchlist over the first two weeks to avoid manual bias and align with "maintains dynamic list of 30-40 high-potential stocks".

6. **Layer A thresholds**: *Are US-market thresholds (3 days A-or-better, avg RS ≥ 85) appropriate?* 
   **Decision**: Loosen to a 2-day window with an average RS of 75. India has 20-40% typical swings, so we want to catch them a bit earlier before they become super-extended.

7. **Fyers daily rate limits**: *Confirm the Nifty 500 daily fetch fits inside quota.* 
   **Decision**: Yes, provisional default is to use a 200ms batch delay which fits within Fyers historical API limits.

8. **Weekly rebalance day**: *Should primary signals be gated by 'stock was in Nifty 500 at signal date'?* 
   **Decision**: Keep it simple for Phase 1. Use the current static universe without historical gating (accepting minor survivorship bias for now).
