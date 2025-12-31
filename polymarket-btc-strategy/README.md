# Polymarket BTC 15-min Crash Strategy

Research and replication project for the strategy described by @the_smart_ape.

## Strategy Overview
An automated bot targeting **Polymarket's BTC 15-minute UP/DOWN markets**. It exploits temporary liquidity crashes to enter a position cheaply and then hedges with the opposite side for a guaranteed profit (arbitrage).

## Key Components
1.  **Market:** Polymarket BTC Event Contracts (Expire every 15 mins).
2.  **Trigger (Leg 1):** Rapid price drop (e.g., -15% in 3s) on either 'UP' or 'DOWN' outcome.
3.  **Hedge (Leg 2):** Buy opposite side if `Entry_Price + Opposite_Ask <= 0.95` (or other target).

## Project Status
- [x] Initial Research & Documentation
- [ ] Data Source Investigation (Polymarket API)
- [ ] Data Collector Implementation
- [ ] Backtest/Simulation Engine
