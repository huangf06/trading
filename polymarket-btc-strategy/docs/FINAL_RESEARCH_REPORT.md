# Research Report: Polymarket BTC 15-min Crash Strategy

**Date:** 2025-12-31
**Subject:** Feasibility Analysis of "The Smart Ape" Automated Arbitrage Bot
**Target Market:** Polymarket BTC 15-Minute Event Contracts

---

## 1. Executive Summary
This report analyzes a high-frequency "legged arbitrage" strategy designed to exploit temporary liquidity crashes in short-term prediction markets. While the strategy demonstrates high theoretical ROI (86%) in snapshot-based backtests, **it is assessed as highly risky and likely unprofitable in real-world execution** due to latency, slippage, and market microstructure dynamics.

## 2. Strategy Logic
The strategy operates on a **Non-Atomic Arbitrage** model:
1.  **Leg 1 (The Snipe):** Monitors the order book for "Flash Crashes" (e.g., price drops >15% in <3 seconds) caused by liquidity voids.
2.  **Leg 2 (The Hedge):** Upon filling Leg 1, immediately attempts to buy the opposite outcome if the total cost is below a risk-free threshold (e.g., `Price_A + Price_B <= 0.95`).
3.  **Profit Mechanism:** Because the contract payout is fixed at $1.00, securing both sides for <$1.00 guarantees a profit equal to the spread.

## 3. Key Parameters & Sensitivities
*   **`windowMin` (Hunting Window):** Time at the start of the 15-min round to look for trades. *Risk:* Too long = no time to hedge.
*   **`movePct` (Crash Threshold):** % drop required to trigger Leg 1. *Risk:* Too low = triggered by noise; Too high = never triggers.
*   **`sumTarget` (Hedge Limit):** Max combined cost. *Risk:* Setting this too aggressively (e.g., 0.60) makes Leg 2 impossible to fill, leaving the bot with a naked gambling position.

## 4. Critical Flaws (Why it Fails)
Our deep-dive analysis identifies three fatal weaknesses in the methodology:

### A. The "Legged" Risk (Execution Risk)
True arbitrage is atomic (happens simultaneously). This strategy is sequential.
*   **Scenario:** Leg 1 fills at $0.40 (YES).
*   **Reality:** Bots react instantly. The price of NO spikes to $0.65 before Leg 2 can execute.
*   **Result:** The bot cannot hedge (`0.40 + 0.65 > 0.95`). It is now holding a naked long position on YES. If the market settles NO, capital is lost.

### B. Liquidity Illusion
Backtests cited in the source material relied on `Best Ask` snapshots.
*   **Depth:** The "crash" price might only have $10 of liquidity.
*   **Slippage:** A market order for $100 will eat through the book, raising the average entry price significantly, destroying the arbitrage math.

### C. Adversarial Environment
Polymarket is populated by sophisticated Market Makers (MMs).
*   **Quote Stuffing:** MMs may flash fake liquidity to bait bots.
*   **Latency:** Retail API access (Python scripts) cannot compete with collocated HFT algorithms in a race for <1 second opportunities.

## 5. Verdict & Recommendation

| Dimension | Rating | Comment |
| :--- | :--- | :--- |
| **Theoretical Logic** | ⭐⭐⭐⭐ | Conceptually sound (Vol arb). |
| **Backtest Reliability** | ⭐ | Snapshot backtests ignore slippage/latency. |
| **Real-World Viability** | ⭐ | High probability of "Leg 1 Death" (Naked exposure). |
| **Educational Value** | ⭐⭐⭐⭐⭐ | Excellent case study for API & market structure. |

### Conclusion
**Do not deploy this strategy with real capital expecting risk-free arbitrage.**
The market efficiency of Polymarket, combined with blockchain/relayer latency, makes "picking up pennies in front of a steamroller" a fitting analogy.

### Pivot Suggestions (For Research Only)
To make this viable, the logic must shift from **Taking** to **Making**:
1.  **Maker Strategy:** Place deep limit orders (e.g., Buy at $0.05) to catch fat-finger crashes passively.
2.  **Mean Reversion:** Abandon the full hedge. Buy the crash and sell on the rebound (Scalping), accepting directional risk.

---
*End of Report*
