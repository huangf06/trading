"""
Bitcoin-Gold Correlation Analysis and Trading Strategy
Based on the hypothesis that negative 40-day correlation between BTC and Gold
precedes explosive BTC price movements.
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class BTCGoldCorrelationAnalyzer:
    """Analyze the correlation between Bitcoin and Gold prices."""

    def __init__(self, start_date='2020-01-01', end_date=None):
        self.start_date = start_date
        self.end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        self.btc_data = None
        self.gold_data = None
        self.merged_data = None
        self.correlation_data = None

    def fetch_data(self):
        """Fetch historical price data for Bitcoin and Gold."""
        print(f"Fetching data from {self.start_date} to {self.end_date}...")

        # Fetch Bitcoin data (using BTC-USD ticker)
        btc = yf.Ticker("BTC-USD")
        self.btc_data = btc.history(start=self.start_date, end=self.end_date)

        # Fetch Gold data (using GLD ETF as proxy)
        gold = yf.Ticker("GLD")
        self.gold_data = gold.history(start=self.start_date, end=self.end_date)

        # Alternative: Use GC=F for Gold Futures
        # gold_futures = yf.Ticker("GC=F")
        # self.gold_data = gold_futures.history(start=self.start_date, end=self.end_date)

        print(f"BTC data points: {len(self.btc_data)}")
        print(f"Gold data points: {len(self.gold_data)}")

        return self.btc_data, self.gold_data

    def calculate_returns(self):
        """Calculate daily returns for both assets."""
        # Merge data on common dates
        self.merged_data = pd.DataFrame({
            'BTC_Close': self.btc_data['Close'],
            'Gold_Close': self.gold_data['Close']
        }).dropna()

        # Calculate returns
        self.merged_data['BTC_Return'] = self.merged_data['BTC_Close'].pct_change()
        self.merged_data['Gold_Return'] = self.merged_data['Gold_Close'].pct_change()

        return self.merged_data

    def calculate_rolling_correlation(self, window=40):
        """Calculate rolling correlation between BTC and Gold returns."""
        if self.merged_data is None:
            self.calculate_returns()

        # Calculate rolling correlation
        self.correlation_data = self.merged_data.copy()
        self.correlation_data[f'{window}d_correlation'] = (
            self.merged_data['BTC_Return']
            .rolling(window=window)
            .corr(self.merged_data['Gold_Return'])
        )

        # Identify when correlation turns negative
        self.correlation_data['correlation_negative'] = (
            self.correlation_data[f'{window}d_correlation'] < 0
        )

        # Identify transition points (positive to negative)
        self.correlation_data['turns_negative'] = (
            (~self.correlation_data['correlation_negative'].shift(1)) &
            (self.correlation_data['correlation_negative'])
        )

        return self.correlation_data

    def identify_negative_periods(self):
        """Identify specific dates when correlation turned negative."""
        negative_turns = self.correlation_data[
            self.correlation_data['turns_negative']
        ].copy()

        # Add future price information for verification
        for days in [30, 60, 90, 120]:
            negative_turns[f'BTC_Return_{days}d'] = (
                self.correlation_data['BTC_Close'].shift(-days) /
                self.correlation_data['BTC_Close'] - 1
            ) * 100

        return negative_turns

    def verify_historical_claims(self):
        """Verify the specific historical claims mentioned in the message."""
        claims = [
            {'date': '2023-10-31', 'from_price': 25000, 'to_price': 45000, 'period': 'Late Oct 2023'},
            {'date': '2024-02-01', 'from_price': 40000, 'to_price': 70000, 'period': 'Early Feb 2024'},
            {'date': '2024-11-01', 'from_price': 70000, 'to_price': 100000, 'period': 'Early Nov 2024'},
        ]

        verification_results = []

        for claim in claims:
            # Find the nearest date in our data
            claim_date = pd.to_datetime(claim['date'])

            # Check correlation around this date
            if claim_date in self.correlation_data.index:
                row = self.correlation_data.loc[claim_date]

                # Get actual price and correlation
                actual_price = row['BTC_Close']
                correlation_40d = row['40d_correlation']

                # Get price 60 days later
                future_date = claim_date + timedelta(days=60)
                if future_date in self.correlation_data.index:
                    future_price = self.correlation_data.loc[future_date, 'BTC_Close']
                    actual_return = (future_price / actual_price - 1) * 100
                else:
                    future_price = None
                    actual_return = None

                verification_results.append({
                    'period': claim['period'],
                    'claim_date': claim['date'],
                    'claimed_start_price': claim['from_price'],
                    'actual_start_price': round(actual_price, 2),
                    'claimed_end_price': claim['to_price'],
                    'actual_end_price': round(future_price, 2) if future_price else 'N/A',
                    '40d_correlation': round(correlation_40d, 3),
                    'correlation_negative': correlation_40d < 0,
                    'actual_60d_return': f"{actual_return:.1f}%" if actual_return else 'N/A'
                })

        return pd.DataFrame(verification_results)

    def analyze_performance_after_negative_correlation(self):
        """Analyze BTC performance following negative correlation periods."""
        # Get all periods where correlation turned negative
        negative_periods = self.identify_negative_periods()

        if len(negative_periods) == 0:
            print("No negative correlation periods found!")
            return None

        # Calculate statistics for returns following negative correlation
        stats_results = {}

        for days in [30, 60, 90, 120]:
            returns_col = f'BTC_Return_{days}d'
            if returns_col in negative_periods.columns:
                returns = negative_periods[returns_col].dropna()

                if len(returns) > 0:
                    stats_results[f'{days}d_returns'] = {
                        'count': len(returns),
                        'mean': returns.mean(),
                        'median': returns.median(),
                        'std': returns.std(),
                        'min': returns.min(),
                        'max': returns.max(),
                        'positive_rate': (returns > 0).mean() * 100
                    }

        return pd.DataFrame(stats_results).T

    def plot_analysis(self):
        """Create comprehensive visualization of the analysis."""
        fig, axes = plt.subplots(4, 1, figsize=(15, 12), sharex=True)

        # Plot 1: BTC Price
        axes[0].plot(self.correlation_data.index, self.correlation_data['BTC_Close'],
                     color='orange', linewidth=1)
        axes[0].set_ylabel('BTC Price (USD)', fontsize=10)
        axes[0].set_title('BTC-Gold Correlation Analysis', fontsize=14, fontweight='bold')
        axes[0].grid(True, alpha=0.3)
        axes[0].set_yscale('log')

        # Mark negative correlation periods
        negative_turns = self.correlation_data[self.correlation_data['turns_negative']]
        for date in negative_turns.index:
            axes[0].axvline(x=date, color='red', linestyle='--', alpha=0.5)
            axes[0].annotate('Neg Corr', xy=(date, self.correlation_data.loc[date, 'BTC_Close']),
                           xytext=(10, 20), textcoords='offset points',
                           fontsize=8, color='red', alpha=0.7)

        # Plot 2: Gold Price
        axes[1].plot(self.correlation_data.index, self.correlation_data['Gold_Close'],
                     color='gold', linewidth=1)
        axes[1].set_ylabel('Gold Price (USD)', fontsize=10)
        axes[1].grid(True, alpha=0.3)

        # Plot 3: 40-day Correlation
        axes[2].plot(self.correlation_data.index, self.correlation_data['40d_correlation'],
                     color='blue', linewidth=1)
        axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[2].fill_between(self.correlation_data.index,
                            self.correlation_data['40d_correlation'],
                            0, where=(self.correlation_data['40d_correlation'] < 0),
                            color='red', alpha=0.3)
        axes[2].set_ylabel('40-day Correlation', fontsize=10)
        axes[2].set_ylim(-1, 1)
        axes[2].grid(True, alpha=0.3)

        # Plot 4: BTC Returns
        axes[3].plot(self.correlation_data.index,
                     self.correlation_data['BTC_Return'].rolling(30).mean() * 100,
                     color='green', linewidth=1, label='30d MA Return')
        axes[3].set_ylabel('BTC Return (%)', fontsize=10)
        axes[3].set_xlabel('Date', fontsize=10)
        axes[3].grid(True, alpha=0.3)
        axes[3].legend()

        plt.tight_layout()
        plt.savefig('btc_gold_correlation_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()

        return fig

    def statistical_significance_test(self):
        """Test statistical significance of returns following negative correlation."""
        # Get returns following negative correlation periods
        negative_periods = self.identify_negative_periods()

        if len(negative_periods) == 0:
            return None

        # Compare with random periods
        all_dates = self.correlation_data.index[40:]  # Skip initial period
        random_samples = []

        # Generate random samples for comparison
        np.random.seed(42)
        for _ in range(1000):
            random_dates = np.random.choice(all_dates, size=len(negative_periods), replace=False)
            random_returns = []

            for date in random_dates:
                if date in self.correlation_data.index:
                    idx = self.correlation_data.index.get_loc(date)
                    if idx + 60 < len(self.correlation_data):
                        future_price = self.correlation_data.iloc[idx + 60]['BTC_Close']
                        current_price = self.correlation_data.iloc[idx]['BTC_Close']
                        ret = (future_price / current_price - 1) * 100
                        random_returns.append(ret)

            if random_returns:
                random_samples.append(np.mean(random_returns))

        # Calculate actual mean return after negative correlation
        actual_returns = negative_periods['BTC_Return_60d'].dropna()
        actual_mean = actual_returns.mean()

        # Perform statistical test
        if random_samples:
            p_value = (np.array(random_samples) >= actual_mean).mean()

            return {
                'actual_mean_return_60d': actual_mean,
                'random_mean_return_60d': np.mean(random_samples),
                'p_value': p_value,
                'statistically_significant': p_value < 0.05,
                'effect_size': (actual_mean - np.mean(random_samples)) / np.std(random_samples)
            }

        return None


def main():
    """Run the complete analysis."""
    print("=" * 60)
    print("BTC-Gold Correlation Analysis")
    print("=" * 60)

    # Initialize analyzer
    analyzer = BTCGoldCorrelationAnalyzer(start_date='2020-01-01')

    # Fetch data
    print("\n1. Fetching historical data...")
    analyzer.fetch_data()

    # Calculate correlations
    print("\n2. Calculating 40-day rolling correlation...")
    correlation_data = analyzer.calculate_rolling_correlation(window=40)
    print(f"Data range: {correlation_data.index[0]} to {correlation_data.index[-1]}")

    # Identify negative correlation periods
    print("\n3. Identifying negative correlation periods...")
    negative_periods = analyzer.identify_negative_periods()
    print(f"Found {len(negative_periods)} periods where correlation turned negative")

    if len(negative_periods) > 0:
        print("\nNegative Correlation Periods:")
        print(negative_periods[['BTC_Close', '40d_correlation', 'BTC_Return_30d',
                                'BTC_Return_60d', 'BTC_Return_90d']])

    # Verify historical claims
    print("\n4. Verifying historical claims...")
    verification = analyzer.verify_historical_claims()
    print(verification)

    # Analyze performance statistics
    print("\n5. Performance statistics after negative correlation:")
    perf_stats = analyzer.analyze_performance_after_negative_correlation()
    if perf_stats is not None:
        print(perf_stats)

    # Statistical significance test
    print("\n6. Statistical significance test:")
    sig_test = analyzer.statistical_significance_test()
    if sig_test:
        for key, value in sig_test.items():
            print(f"  {key}: {value}")

    # Create visualizations
    print("\n7. Creating visualizations...")
    analyzer.plot_analysis()

    # Save results
    print("\n8. Saving results...")
    correlation_data.to_csv('btc_gold_correlation_data.csv')
    if len(negative_periods) > 0:
        negative_periods.to_csv('negative_correlation_periods.csv')

    print("\n✓ Analysis complete!")

    return analyzer


if __name__ == "__main__":
    analyzer = main()