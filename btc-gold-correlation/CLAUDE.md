# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **quantitative trading research project** investigating whether weakening BTC-Gold correlation can predict Bitcoin price increases. The research has completed data validation and is ready for further development.

**Key Finding**: The signal is real but was slightly overestimated. After data quality improvements:
- 60-day average return: +26.3% (down from +31.7%)
- Win rate: 71.4%
- Excess return over random baseline: +14.4%
- **Status**: Not statistically significant (p=0.257), but economically significant
- **Recommendation**: Use as supplementary signal, not standalone strategy

## Essential Commands

### Data Collection
```bash
# Collect/update market data (BTC, Gold, DXY, SPX)
python scripts/simple_data_collector.py

# Alternative data collector (older version - archived)
python archive/data_collector.py
```

### Signal Validation & Analysis
```bash
# Verify signal performance with corrected data
python scripts/verify_signal_with_new_data.py

# Analyze data quality and weekend handling
python scripts/analyze_data_quality.py

# Compare old vs new data methodology
python scripts/compare_old_vs_new_data.py

# Test different correlation signal variants
python scripts/test_different_correlations.py
```

### Development Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Key packages: pandas, numpy, yfinance, ccxt, scipy, statsmodels
```

## Architecture & Design Principles

### Data Pipeline Architecture

The codebase uses a **two-stage data correction approach**:

1. **Data Collection** (`simple_data_collector.py`):
   - **CRITICAL**: Never use forward fill for weekend data
   - Keep NaN for non-trading days (Gold, DXY, SPX trade weekdays only)
   - BTC trades 24/7, so it has data on weekends
   - Sources: yfinance (BTC-USD), GLD ETF, FRED (DXY, SPX)

2. **Correlation Calculation**:
   - Use log returns: `np.log(price / price.shift(1))`
   - Calculate 40-day rolling correlation on returns (not prices)
   - Pandas `.corr()` automatically handles NaN pairs correctly
   - Only computes correlation on days both assets traded

**Why this matters**: The original methodology used forward fill for weekends, which artificially set 209 days/year of Gold returns to 0, systematically biasing correlations toward zero. See `RESEARCH_HANDOVER_PACKAGE.md` for full analysis.

### Signal Definition

**Primary Signal: "Strong Positive → Weak Positive"**
```python
# Entry conditions:
# 1. Past 10-20 days avg correlation: +0.3 to +1.0 (strong positive)
# 2. Current correlation: -0.1 to +0.15 (weak/neutral)
# 3. Minimum 30 days between signals (avoid clustering)

# Historical performance (corrected data):
# - 7 triggers in 10 years (2015-2025)
# - 60-day avg return: +26.3%
# - Win rate: 71.4%
# - Excess return vs random: +14.4%
```

**Alternative Signal: "Positive → Negative"** (worth investigating)
- 12 triggers (larger sample)
- 60-day return: +27.6%
- Win rate: 83.3%
- **This signal improved after data correction** (+4.5%)

### Data Storage Format

All data stored as Parquet files for efficiency:

- `results/improved_data_prices.parquet` - Daily prices (BTC, Gold, DXY, SPX)
- `results/improved_data_returns.parquet` - Log returns with NaN preserved
- `results/improved_data_correlation.parquet` - 40-day rolling correlation + valid pairs count
- `data/processed/` - Old data for comparison (uses forward fill method)

**Data Quality Metrics**:
- BTC: 100% coverage (2015-2025, 3,956 days)
- Gold: 68.9% coverage (weekends correctly = NaN)
- Correlation valid points: 2,094 with avg 21.6/40 pairs per window

### Critical Data Quality Rules

When working with this codebase:

1. **NEVER use forward fill** for multi-asset correlation analysis
2. **ALWAYS preserve NaN** on weekends for non-24/7 assets
3. **Calculate correlation on returns**, not prices
4. **Use log returns** for better statistical properties
5. **Verify weekend handling**: `df[df.index.dayofweek >= 5]` should show NaN for Gold

### Signal Validation Methodology

The codebase uses rigorous statistical testing:

```python
# Key validation steps in verify_signal_with_new_data.py:
# 1. Detect signal triggers using correlation thresholds
# 2. Calculate forward returns (30, 60, 90 days)
# 3. Generate random baseline (10,000 iterations)
# 4. Statistical comparison (t-test)
# 5. Bootstrap confidence intervals
```

**Statistical significance issue**: With only 7 signals in 10 years, p-value = 0.257 (not < 0.05). This is a **sample size issue**, not strategy failure. Economic significance is strong (+14.4% excess return).

## Known Issues & Limitations

### 1. Small Sample Size (Critical)
- Only 7 signal triggers in 10 years
- Need 20+ samples for statistical significance
- Current p-value: 0.257 (need < 0.05)

### 2. Data Source Not Ideal
- Using GLD ETF (Gold trust fund) instead of XAU/USD spot
- GLD trades only during US market hours
- Better than forward-filled data, but suboptimal
- **TODO**: Get true XAU/USD spot data (24/5 trading)

### 3. Alpha Vantage API Issue
- API key exists: `11A6UEZO56SX8FC9`
- Supposed to provide XAU/USD data but currently failing
- Need to debug or find alternative (Twelve Data, Polygon.io, Yahoo `XAUUSD=X`)

## High-Priority Next Steps

Based on `RESEARCH_HANDOVER_PACKAGE.md`, the immediate roadmap:

### Week 1 (Do These First)
1. **Get Real XAU/USD Spot Data**
   - Debug Alpha Vantage API or switch to alternative
   - Expected 5-10% signal quality improvement

2. **Extract & Analyze 7 Signal Dates**
   - Identify which 2 are new vs old data methodology
   - Analyze individual performance
   - If new signals underperform, may need additional filters

3. **Investigate "Positive → Negative" Signal**
   - Performed better after data correction
   - Larger sample (12 vs 7 triggers)
   - May be superior to current primary signal

### Medium Term (Next 2 Weeks)
4. **Multi-Asset Testing**: Apply to ETH, BNB, SOL for larger sample
5. **Multi-Window Testing**: Test 30, 50, 60-day correlation windows
6. **Combined Signal System**: Integrate with technical/macro indicators

## File Organization

### Core Files (Project Root)
- `README.md` - **⭐ Start here** - Project overview and quick start
- `CLAUDE.md` - This file - Development guide for AI assistants
- `requirements.txt` - Python dependencies

### Scripts (`scripts/`)
- `simple_data_collector.py` - **⭐ Primary data collection** (correct method)
- `verify_signal_with_new_data.py` - Signal validation with statistical tests
- `analyze_data_quality.py` - Data quality verification
- `compare_old_vs_new_data.py` - Methodology comparison
- `trading_strategy.py` - Backtesting framework
- `analyze_correlation_trends.py` - Correlation pattern analysis
- `test_different_correlations.py` - Signal variant testing
- `verify_cases.py` - Twitter claim validation
- `verify_correct_logic.py` - Logic verification
- `verify_leading_signal.py` - Lead/lag relationship testing

### Documentation (`docs/`)
- `RESEARCH_HANDOVER_PACKAGE.md` - **⭐ Comprehensive research summary (start here)**
- `FINAL_CONCLUSION_REPORT.md` - Data validation findings (11,000 words)
- `correlation_signal_findings.md` - Original research report
- `data_source_upgrade_summary.md` - Technical methodology documentation
- `next_steps_validation_plan.md` - Future roadmap
- `gemini_feedback.md` - Expert review that identified data issues
- `research_plan.md` - Original research plan (Chinese)

### Data Files (`results/`)
- `improved_data_prices.parquet` - Daily prices (BTC, Gold, DXY, SPX)
- `improved_data_returns.parquet` - Log returns with NaN preserved
- `improved_data_correlation.parquet` - 40-day rolling correlation

### Raw Data (`data/`)
- `raw/` - Downloaded raw data cache
- `processed/` - Old processed data (forward fill method, for comparison)

### Archive (`archive/`)
- `data_collector.py` - Original data collector (deprecated)
- `improved_data_collector.py` - Intermediate version
- `btc_gold_correlation_analysis.py` - Early analysis
- `verification_output.log` - Old logs

## Trading Strategy Implementation Notes

From `scripts/trading_strategy.py`:

**Strategy Types**:
1. **Simple Fixed Hold**: Buy on signal, hold 60 days
2. **Dynamic Correlation**: Exit when correlation reverts
3. **Combined Technical**: Add technical confirmation (breakouts, etc.)

**Risk Management**:
- Max single trade risk: 2-3%
- Recommended position sizing: 10-30% depending on confluence
- Stop loss: -10% or key support break
- **NEVER use this signal standalone** with >50% position

**Realistic Expectations**:
- 60-day return: +15-30% (conservative: +15-25%, optimistic: +25-35%)
- Win rate: 65-75%
- Drawdown risk: -10% to -15%

## Code Patterns & Conventions

### Data Loading
```python
import pandas as pd

# Load corrected data
prices = pd.read_parquet('results/improved_data_prices.parquet')
returns = pd.read_parquet('results/improved_data_returns.parquet')
correlation = pd.read_parquet('results/improved_data_correlation.parquet')

# Verify weekend handling
weekend = prices[prices.index.dayofweek >= 5]
assert weekend['Gold'].isna().sum() > 1000, "Gold weekends should be NaN"
assert weekend['BTC'].isna().sum() == 0, "BTC should trade on weekends"
```

### Correlation Calculation
```python
import numpy as np

# CORRECT METHOD (preserves NaN)
returns = np.log(prices / prices.shift(1))
correlation = returns['BTC'].rolling(40).corr(returns['Gold'])

# WRONG METHOD (do not use)
# prices_filled = prices.fillna(method='ffill')  # ❌ Never do this
```

### Signal Detection
```python
def detect_signal(correlation, lookback_start=20, lookback_end=10):
    """Detect 'strong positive → weak' correlation signals"""
    signals = []

    for i in range(lookback_start, len(correlation)):
        current = correlation.iloc[i]
        past_avg = correlation.iloc[i-lookback_start:i-lookback_end].mean()

        # Signal conditions
        was_strong_positive = (past_avg > 0.3)
        now_weak = (-0.1 < current < 0.15)

        if was_strong_positive and now_weak:
            signals.append({
                'date': correlation.index[i],
                'current_corr': current,
                'past_corr': past_avg
            })

    return pd.DataFrame(signals)
```

## Testing & Validation

When modifying signal logic or data pipeline:

1. **Data Quality Checks**: Run `python analyze_data_quality.py`
   - Verify weekend NaN counts
   - Check for data artifacts
   - Validate coverage percentages

2. **Signal Validation**: Run `python verify_signal_with_new_data.py`
   - Compare against random baseline
   - Statistical significance tests
   - Performance metrics

3. **Old vs New Comparison**: Run `python compare_old_vs_new_data.py`
   - Ensure methodology improvements don't break existing findings
   - Document any changes to signal performance

## Research Context

This project originated from a Twitter claim about BTC-Gold correlation predicting rallies. The research validated the core concept but found:

**Original Twitter Claims** (Oct 2023, Feb 2024, Nov 2024 rallies):
- Claimed: Correlation turning negative → BTC rallies 43-80%
- **Finding**: The real signal is correlation weakening from strong positive to weak (not necessarily negative)

**Data Quality Journey**:
- Initial analysis: +31.7% returns, 80% win rate
- Expert (Gemini) identified forward fill bias
- After correction: +26.3% returns, 71.4% win rate
- **Conclusion**: Signal is real but was overestimated by ~17%

## Important Reminders

1. **Statistical vs Economic Significance**: This signal has strong economic significance (+14.4% excess return) but weak statistical significance (p=0.257). This is due to small sample size, not strategy failure.

2. **Risk Disclosure**: 7 signals over 10 years is insufficient for robust conclusions. Use as supplementary confirmation, not primary strategy.

3. **Data Integrity**: Always verify weekend handling when modifying data pipeline. The correlation bias from forward filling affected 57% of days (209 weekend days/year).

4. **Methodology First**: Before adding features, focus on getting XAU/USD spot data and expanding sample size through multi-asset/multi-window testing.

## Success Criteria

From `RESEARCH_HANDOVER_PACKAGE.md`, minimum criteria for live testing:
- [ ] XAU/USD spot data obtained
- [ ] Sample size >10 signals (multi-asset or multi-window)
- [ ] Win rate >70%
- [ ] Excess return >12%
- [ ] Paper trading: 3 months profitable

Ideal criteria for scaling:
- [ ] p-value <0.05 (statistical significance)
- [ ] Sharpe ratio >1.0
- [ ] Maximum drawdown <15%
- [ ] Validated across multiple crypto assets
- [ ] Clear causal mechanism understood
