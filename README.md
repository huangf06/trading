# Trading Research Projects

This directory contains various quantitative trading research projects.

## Projects

### 🎛️ [ikbr settings](./ikbr%20settings/)
**Status**: ✅ Completed (Dec 2025)
**Topic**: Interactive Brokers TWS configuration for macro observation
**Purpose**: Professional market monitoring setup

**Configuration Includes**:
- 12-asset macro watchlist (rates, risk assets, commodities, sentiment)
- Advanced Chart templates with SMA 20/200
- Window grouping for synchronized analysis
- Complete setup guide and quick reference

**Assets Covered**: ZN, DX, ZT, ES, NQ, HSI, GC, CL, HG, MBT, VIX, HYG

[📖 View Setup Guide](./ikbr%20settings/市场观察框架与TWS设置指南.md) | [📋 Quick Reference](./ikbr%20settings/品种速查表.md)

---

### 📊 [btc-gold-correlation](./btc-gold-correlation/)
**Status**: ✅ Completed (Oct 2025)
**Topic**: BTC-Gold correlation as a trading signal
**Signal Quality**: 6.0/10
**Key Finding**: Correlation weakening predicts BTC gains (+26.3% avg 60-day return)
**Use Case**: Supplementary confirmation signal only

**Quick Summary**:
- Validated signal with 7 historical triggers (2015-2025)
- Win rate: 71.4%, Excess return: +14.4% vs random
- Not statistically significant (p=0.257, small sample size)
- Fixed critical data quality issue (forward fill bias)
- Ready for: Sample expansion, data improvement, multi-asset testing
- NOT ready for: Standalone live trading

[📖 Read Full Report](./btc-gold-correlation/README.md)

---

## Future Projects

Additional research projects will be added here as they are developed.

### Potential Research Areas
- Other crypto correlation signals (BTC-SPX, BTC-DXY)
- On-chain metrics trading signals
- Multi-asset momentum strategies
- Volatility-based entries
- Macro indicator combinations

---

## Project Structure Convention

Each project should follow this structure:
```
project-name/
├── README.md              # Project overview and findings
├── CLAUDE.md              # Development guide for AI assistance
├── requirements.txt       # Python dependencies
├── scripts/               # Analysis and validation code
├── docs/                  # Research documentation
├── results/               # Processed data and outputs
├── data/                  # Raw data (optional, may be shared)
└── archive/               # Deprecated files
```

---

## Getting Started with a Project

1. Navigate to the project folder: `cd btc-gold-correlation/`
2. Read the README: `cat README.md`
3. Install dependencies: `pip install -r requirements.txt`
4. Follow project-specific instructions

---

**Last Updated**: December 24, 2025
**Active Projects**: 2
**Completed Projects**: 2
