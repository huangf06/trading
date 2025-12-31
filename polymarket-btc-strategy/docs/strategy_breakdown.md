# Strategy Breakdown: "The Smart Ape" Polymarket Bot

Based on the analysis of the tweet and subsequent discussions.

## Core Logic

The bot operates in 15-minute cycles corresponding to Polymarket's specific BTC markets.

### Parameters
*   `windowMin`: Time in minutes to monitor for crashes at the start of a round (e.g., first 2 mins).
*   `movePct`: Percentage drop required to trigger a buy (e.g., 0.15 or 15%).
*   `timeWindow`: Time duration to measure the drop (e.g., 3 seconds).
*   `sumTarget`: Max combined price for Leg 1 + Leg 2 to ensure profit (e.g., 0.95).
    *   *Note: Payout is 1.00 (USDC). Buying both for < 1.00 is risk-free profit if held to expiry.*

### Execution Flow

1.  **Wait for Round Start:** Initialize monitoring when a new 15-min market opens.
2.  **Monitor (Leg 1):** 
    *   Track Best Ask prices for 'YES' and 'NO' tokens.
    *   Calculate Rolling Change: `(Current_Ask - Ask_T_minus_3s) / Ask_T_minus_3s`.
    *   **Trigger:** If `Rolling_Change <= -movePct`:
        *   **Action:** BUY that side immediately (Market Buy or Aggressive Limit).
        *   **State:** Move to Leg 2.
3.  **Hedge (Leg 2):**
    *   Monitor Best Ask of the *opposite* side.
    *   **Trigger:** If `Leg1_Entry_Price + Opposite_Best_Ask <= sumTarget`:
        *   **Action:** BUY opposite side.
        *   **State:** Cycle Complete (Profit Locked).
    *   *Timeout Risk:* If the hedge target is never met before expiry, the bot holds a directional bet.

## Risks & Limitations

1.  **Execution Risk:** "Crashes" are often due to low liquidity. Filling size might be difficult without significant slippage.
2.  **Hedge Failure:** Prices might rebound too quickly (V-shape) or the other side might spike, making the hedge (`sum <= 0.95`) impossible.
3.  **API Latency:** Polymarket (Polygon/EVM) transactions might be too slow compared to CEXs, though Polymarket uses a relayer/proxy for faster matching.
4.  **Data Quality:** The original author noted that backtests were based on snapshots, missing micro-fluctuations.

## Data Requirements
To simulate this, we need:
- **Order Book Snapshots:** Best Ask for YES and NO tokens.
- **Frequency:** High frequency (at least 1s, ideally 100ms).
- **History:** Polymarket Clob API or Gamma API archives.
