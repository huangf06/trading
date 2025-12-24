"""
Main execution script for BTC-Gold Correlation Analysis and Trading Strategy
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Import our modules
from btc_gold_correlation_analysis import BTCGoldCorrelationAnalyzer
from trading_strategy import CorrelationTradingStrategy, run_strategy_backtest


def print_summary_report(analyzer, strategy_simple, strategy_dynamic, metrics_simple, metrics_dynamic):
    """Print a comprehensive summary report."""
    print("\n" + "=" * 70)
    print("EXECUTIVE SUMMARY: BTC-GOLD CORRELATION TRADING ANALYSIS")
    print("=" * 70)

    # Analysis period
    data = analyzer.correlation_data
    print(f"\nAnalysis Period: {data.index[0].date()} to {data.index[-1].date()}")
    print(f"Total Days Analyzed: {len(data)}")

    # Correlation findings
    negative_periods = analyzer.identify_negative_periods()
    print(f"\n📊 CORRELATION ANALYSIS:")
    print(f"  • Negative correlation periods identified: {len(negative_periods)}")

    if len(negative_periods) > 0:
        avg_return_60d = negative_periods['BTC_Return_60d'].dropna().mean()
        print(f"  • Average BTC return 60 days after negative correlation: {avg_return_60d:.1f}%")

    # Statistical significance
    sig_test = analyzer.statistical_significance_test()
    if sig_test:
        print(f"\n📈 STATISTICAL SIGNIFICANCE:")
        print(f"  • P-value: {sig_test['p_value']:.4f}")
        print(f"  • Statistically significant: {'Yes ✓' if sig_test['statistically_significant'] else 'No ✗'}")
        print(f"  • Effect size: {sig_test['effect_size']:.2f}")

    # Trading strategy performance
    print(f"\n💰 TRADING STRATEGY PERFORMANCE:")

    print(f"\n  Simple Strategy (Fixed 60-day holding):")
    print(f"    • Total return: {metrics_simple.get('total_return_pct', 0):.1f}%")
    print(f"    • Win rate: {metrics_simple.get('win_rate', 0):.1f}%")
    print(f"    • Sharpe ratio: {metrics_simple.get('sharpe_ratio', 0):.2f}")
    print(f"    • Max drawdown: {metrics_simple.get('max_drawdown_pct', 0):.1f}%")
    print(f"    • Total trades: {metrics_simple.get('total_trades', 0)}")

    print(f"\n  Dynamic Strategy (Correlation-based exit):")
    print(f"    • Total return: {metrics_dynamic.get('total_return_pct', 0):.1f}%")
    print(f"    • Win rate: {metrics_dynamic.get('win_rate', 0):.1f}%")
    print(f"    • Sharpe ratio: {metrics_dynamic.get('sharpe_ratio', 0):.2f}")
    print(f"    • Max drawdown: {metrics_dynamic.get('max_drawdown_pct', 0):.1f}%")
    print(f"    • Total trades: {metrics_dynamic.get('total_trades', 0)}")

    # Verification of claims
    print(f"\n🔍 VERIFICATION OF HISTORICAL CLAIMS:")
    verification_df = analyzer.verify_historical_claims()
    for _, row in verification_df.iterrows():
        status = "✓" if row['correlation_negative'] else "✗"
        print(f"  • {row['period']}: Correlation negative: {status}")

    # Key insights
    print(f"\n💡 KEY INSIGHTS:")
    if sig_test and sig_test['statistically_significant']:
        print(f"  ✓ The negative correlation signal shows statistical significance")
        print(f"  ✓ Average excess return vs random periods: {sig_test['actual_mean_return_60d'] - sig_test['random_mean_return_60d']:.1f}%")
    else:
        print(f"  ⚠ The correlation signal does not show strong statistical significance")

    if metrics_simple.get('sharpe_ratio', 0) > 1.0 or metrics_dynamic.get('sharpe_ratio', 0) > 1.0:
        print(f"  ✓ Trading strategies show promising risk-adjusted returns (Sharpe > 1.0)")
    else:
        print(f"  ⚠ Trading strategies show moderate risk-adjusted returns")

    # Risk warnings
    print(f"\n⚠️  RISK CONSIDERATIONS:")
    print(f"  • Past performance does not guarantee future results")
    print(f"  • The analysis is based on limited historical data")
    print(f"  • Transaction costs and slippage may impact real-world performance")
    print(f"  • Market conditions and correlations can change over time")
    print(f"  • Consider position sizing and risk management carefully")

    print("\n" + "=" * 70)


def main():
    """Main execution function."""
    print("\n🚀 Starting BTC-Gold Correlation Analysis and Trading Strategy Development")
    print("=" * 70)

    try:
        # Step 1: Run correlation analysis
        print("\n📊 Step 1: Running correlation analysis...")
        analyzer = BTCGoldCorrelationAnalyzer(start_date='2020-01-01')

        # Fetch and process data
        analyzer.fetch_data()
        correlation_data = analyzer.calculate_rolling_correlation(window=40)

        # Identify negative periods
        negative_periods = analyzer.identify_negative_periods()
        print(f"✓ Found {len(negative_periods)} negative correlation periods")

        # Verify historical claims
        verification = analyzer.verify_historical_claims()
        print("\n📋 Historical Claims Verification:")
        print(verification.to_string())

        # Statistical analysis
        perf_stats = analyzer.analyze_performance_after_negative_correlation()
        if perf_stats is not None:
            print("\n📈 Performance Statistics After Negative Correlation:")
            print(perf_stats)

        # Statistical significance test
        sig_test = analyzer.statistical_significance_test()

        # Create visualizations
        print("\n📊 Creating correlation analysis visualizations...")
        analyzer.plot_analysis()

        # Step 2: Run trading strategy backtest
        print("\n💹 Step 2: Running trading strategy backtest...")

        # Simple strategy
        strategy_simple = CorrelationTradingStrategy(initial_capital=100000, fee_rate=0.001)
        data_simple = correlation_data.copy()
        data_simple = strategy_simple.backtest_simple_strategy(
            data_simple,
            entry_threshold=-0.1,
            holding_days=60,
            position_size=0.5,
            stop_loss=0.10,
            take_profit=0.30
        )
        metrics_simple = strategy_simple.calculate_performance_metrics(data_simple)

        # Dynamic strategy
        strategy_dynamic = CorrelationTradingStrategy(initial_capital=100000, fee_rate=0.001)
        data_dynamic = correlation_data.copy()
        data_dynamic = strategy_dynamic.backtest_dynamic_strategy(
            data_dynamic,
            entry_threshold=-0.15,
            exit_correlation=0.1,
            position_size=0.5,
            max_holding_days=90,
            use_trailing_stop=True,
            trailing_stop_pct=0.15
        )
        metrics_dynamic = strategy_dynamic.calculate_performance_metrics(data_dynamic)

        # Create backtest visualizations
        print("\n📊 Creating backtest visualizations...")
        strategy_simple.plot_backtest_results(data_simple)

        # Step 3: Generate summary report
        print_summary_report(analyzer, strategy_simple, strategy_dynamic, metrics_simple, metrics_dynamic)

        # Step 4: Save all results
        print("\n💾 Saving results to files...")

        # Save data
        correlation_data.to_csv('btc_gold_correlation_data.csv')
        print("✓ Saved: btc_gold_correlation_data.csv")

        if len(negative_periods) > 0:
            negative_periods.to_csv('negative_correlation_periods.csv')
            print("✓ Saved: negative_correlation_periods.csv")

        if len(strategy_simple.trades) > 0:
            strategy_simple.trades.to_csv('simple_strategy_trades.csv')
            print("✓ Saved: simple_strategy_trades.csv")

        if len(strategy_dynamic.trades) > 0:
            strategy_dynamic.trades.to_csv('dynamic_strategy_trades.csv')
            print("✓ Saved: dynamic_strategy_trades.csv")

        # Save metrics summary
        metrics_summary = pd.DataFrame({
            'Simple Strategy': metrics_simple,
            'Dynamic Strategy': metrics_dynamic
        }).T
        metrics_summary.to_csv('strategy_performance_metrics.csv')
        print("✓ Saved: strategy_performance_metrics.csv")

        print("\n✅ Analysis complete! All results have been saved.")
        print("\n📁 Output files:")
        print("  • btc_gold_correlation_data.csv - Full correlation dataset")
        print("  • negative_correlation_periods.csv - Periods when correlation turned negative")
        print("  • simple_strategy_trades.csv - Trade log for simple strategy")
        print("  • dynamic_strategy_trades.csv - Trade log for dynamic strategy")
        print("  • strategy_performance_metrics.csv - Performance metrics summary")
        print("  • btc_gold_correlation_analysis.png - Correlation analysis chart")
        print("  • backtest_results.png - Backtest performance chart")

        return analyzer, strategy_simple, strategy_dynamic

    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None, None


if __name__ == "__main__":
    # Run the complete analysis
    analyzer, strategy_simple, strategy_dynamic = main()

    # Additional prompt for user
    print("\n" + "=" * 70)
    print("📌 NEXT STEPS:")
    print("1. Review the generated charts and CSV files for detailed insights")
    print("2. Consider adjusting strategy parameters based on optimization results")
    print("3. Implement real-time monitoring if the pattern proves profitable")
    print("4. Always use proper risk management and position sizing")
    print("=" * 70)