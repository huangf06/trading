"""
Trading Strategy Implementation based on BTC-Gold Negative Correlation Signal
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class CorrelationTradingStrategy:
    """Implement and backtest trading strategies based on BTC-Gold correlation signals."""

    def __init__(self, initial_capital=100000, fee_rate=0.001):
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate
        self.positions = []
        self.trades = []
        self.portfolio_value = []

    def backtest_simple_strategy(self, data, correlation_col='40d_correlation',
                                entry_threshold=-0.1, holding_days=60,
                                position_size=1.0, stop_loss=None, take_profit=None):
        """
        Simple strategy: Buy when correlation goes below threshold, hold for fixed period.

        Parameters:
        - data: DataFrame with price and correlation data
        - correlation_col: Column name for correlation values
        - entry_threshold: Correlation threshold for entry signal (default -0.1)
        - holding_days: Number of days to hold position
        - position_size: Fraction of capital to use (0-1)
        - stop_loss: Optional stop loss percentage (e.g., 0.05 for 5%)
        - take_profit: Optional take profit percentage (e.g., 0.20 for 20%)
        """
        capital = self.initial_capital
        position = None
        trades = []

        # Add signal column
        data['signal'] = 0
        data['position'] = 0
        data['portfolio_value'] = capital

        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data.iloc[i]['BTC_Close']
            current_corr = data.iloc[i][correlation_col]

            # Check for entry signal
            if position is None and not pd.isna(current_corr):
                # Entry condition: correlation below threshold and turning negative
                if i > 0:
                    prev_corr = data.iloc[i-1][correlation_col]
                    if current_corr < entry_threshold and prev_corr >= entry_threshold:
                        # Enter position
                        position_value = capital * position_size
                        btc_amount = (position_value * (1 - self.fee_rate)) / current_price
                        remaining_capital = capital - position_value

                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'btc_amount': btc_amount,
                            'position_value': position_value,
                            'entry_correlation': current_corr,
                            'target_exit_date': current_date + timedelta(days=holding_days)
                        }

                        data.loc[current_date, 'signal'] = 1

            # Check for exit conditions
            if position is not None:
                data.loc[current_date, 'position'] = 1

                # Calculate current P&L
                current_value = position['btc_amount'] * current_price
                pnl_pct = (current_value - position['position_value']) / position['position_value']

                # Exit conditions
                exit_trade = False
                exit_reason = ""

                # 1. Time-based exit
                if current_date >= position['target_exit_date']:
                    exit_trade = True
                    exit_reason = "Time exit"

                # 2. Stop loss
                if stop_loss and pnl_pct <= -stop_loss:
                    exit_trade = True
                    exit_reason = "Stop loss"

                # 3. Take profit
                if take_profit and pnl_pct >= take_profit:
                    exit_trade = True
                    exit_reason = "Take profit"

                if exit_trade:
                    # Exit position
                    exit_value = position['btc_amount'] * current_price * (1 - self.fee_rate)
                    trade_pnl = exit_value - position['position_value']
                    trade_pnl_pct = trade_pnl / position['position_value'] * 100

                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'entry_correlation': position['entry_correlation'],
                        'holding_days': (current_date - position['entry_date']).days,
                        'pnl': trade_pnl,
                        'pnl_pct': trade_pnl_pct,
                        'exit_reason': exit_reason
                    })

                    # Update capital
                    capital = remaining_capital + exit_value
                    position = None
                    data.loc[current_date, 'signal'] = -1

            # Track portfolio value
            if position is not None:
                current_btc_value = position['btc_amount'] * current_price
                data.loc[current_date, 'portfolio_value'] = remaining_capital + current_btc_value
            else:
                data.loc[current_date, 'portfolio_value'] = capital

        self.trades = pd.DataFrame(trades)
        return data

    def backtest_dynamic_strategy(self, data, correlation_col='40d_correlation',
                                 entry_threshold=-0.1, exit_correlation=0.2,
                                 position_size=1.0, max_holding_days=120,
                                 use_trailing_stop=False, trailing_stop_pct=0.15):
        """
        Dynamic strategy: Enter on negative correlation, exit on correlation reversal.

        Parameters:
        - entry_threshold: Correlation threshold for entry
        - exit_correlation: Correlation level to exit position
        - use_trailing_stop: Whether to use trailing stop loss
        - trailing_stop_pct: Trailing stop percentage
        """
        capital = self.initial_capital
        position = None
        trades = []
        highest_value = 0

        # Add signal columns
        data['signal'] = 0
        data['position'] = 0
        data['portfolio_value'] = capital

        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data.iloc[i]['BTC_Close']
            current_corr = data.iloc[i][correlation_col]

            # Entry signal
            if position is None and not pd.isna(current_corr):
                if i > 0:
                    prev_corr = data.iloc[i-1][correlation_col]
                    # Strong negative correlation signal
                    if current_corr < entry_threshold and prev_corr >= entry_threshold:
                        position_value = capital * position_size
                        btc_amount = (position_value * (1 - self.fee_rate)) / current_price
                        remaining_capital = capital - position_value

                        position = {
                            'entry_date': current_date,
                            'entry_price': current_price,
                            'btc_amount': btc_amount,
                            'position_value': position_value,
                            'entry_correlation': current_corr,
                            'highest_value': position_value,
                            'max_date': current_date + timedelta(days=max_holding_days)
                        }

                        data.loc[current_date, 'signal'] = 1
                        highest_value = position_value

            # Exit conditions
            if position is not None:
                data.loc[current_date, 'position'] = 1
                current_value = position['btc_amount'] * current_price

                # Update highest value for trailing stop
                if use_trailing_stop and current_value > highest_value:
                    highest_value = current_value

                exit_trade = False
                exit_reason = ""

                # 1. Correlation reversal exit
                if not pd.isna(current_corr) and current_corr >= exit_correlation:
                    exit_trade = True
                    exit_reason = "Correlation reversal"

                # 2. Maximum holding period
                if current_date >= position['max_date']:
                    exit_trade = True
                    exit_reason = "Max holding period"

                # 3. Trailing stop loss
                if use_trailing_stop:
                    if current_value < highest_value * (1 - trailing_stop_pct):
                        exit_trade = True
                        exit_reason = "Trailing stop"

                if exit_trade:
                    exit_value = position['btc_amount'] * current_price * (1 - self.fee_rate)
                    trade_pnl = exit_value - position['position_value']
                    trade_pnl_pct = trade_pnl / position['position_value'] * 100

                    trades.append({
                        'entry_date': position['entry_date'],
                        'exit_date': current_date,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'entry_correlation': position['entry_correlation'],
                        'exit_correlation': current_corr,
                        'holding_days': (current_date - position['entry_date']).days,
                        'pnl': trade_pnl,
                        'pnl_pct': trade_pnl_pct,
                        'exit_reason': exit_reason
                    })

                    capital = remaining_capital + exit_value
                    position = None
                    data.loc[current_date, 'signal'] = -1

                # Update portfolio value
                if position is not None:
                    data.loc[current_date, 'portfolio_value'] = remaining_capital + current_value
            else:
                data.loc[current_date, 'portfolio_value'] = capital

        self.trades = pd.DataFrame(trades)
        return data

    def calculate_performance_metrics(self, data, trades_df=None):
        """Calculate comprehensive performance metrics."""
        if trades_df is None:
            trades_df = self.trades

        if len(trades_df) == 0:
            return {"error": "No trades to analyze"}

        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        # PnL metrics
        total_pnl = trades_df['pnl'].sum()
        avg_pnl = trades_df['pnl'].mean()
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0

        # Return metrics
        total_return = (data['portfolio_value'].iloc[-1] / self.initial_capital - 1) * 100
        avg_return_per_trade = trades_df['pnl_pct'].mean()

        # Risk metrics
        returns = data['portfolio_value'].pct_change().dropna()
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        max_drawdown = self._calculate_max_drawdown(data['portfolio_value'])

        # Calculate profit factor
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum() if winning_trades > 0 else 0
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf

        metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate * 100,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return_pct': total_return,
            'avg_return_per_trade': avg_return_per_trade,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_pct': max_drawdown * 100,
            'avg_holding_days': trades_df['holding_days'].mean()
        }

        return metrics

    def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
        """Calculate Sharpe ratio."""
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        if len(excess_returns) > 0 and excess_returns.std() > 0:
            return np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        return 0

    def _calculate_max_drawdown(self, portfolio_values):
        """Calculate maximum drawdown."""
        cummax = portfolio_values.cummax()
        drawdown = (portfolio_values - cummax) / cummax
        return drawdown.min()

    def plot_backtest_results(self, data, trades_df=None):
        """Create comprehensive visualization of backtest results."""
        if trades_df is None:
            trades_df = self.trades

        fig, axes = plt.subplots(4, 1, figsize=(15, 12))

        # Plot 1: Portfolio value over time
        axes[0].plot(data.index, data['portfolio_value'], label='Portfolio Value', linewidth=2)
        axes[0].axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5)
        axes[0].set_ylabel('Portfolio Value ($)')
        axes[0].set_title('Backtest Results: BTC-Gold Correlation Trading Strategy', fontweight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Mark entry and exit points
        entries = data[data['signal'] == 1]
        exits = data[data['signal'] == -1]

        # Plot 2: BTC price with trade signals
        axes[1].plot(data.index, data['BTC_Close'], label='BTC Price', color='orange', linewidth=1)
        axes[1].scatter(entries.index, entries['BTC_Close'], color='green', marker='^', s=100, label='Buy')
        axes[1].scatter(exits.index, exits['BTC_Close'], color='red', marker='v', s=100, label='Sell')
        axes[1].set_ylabel('BTC Price ($)')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        axes[1].set_yscale('log')

        # Plot 3: 40-day correlation
        axes[2].plot(data.index, data['40d_correlation'], label='40-day Correlation', linewidth=1)
        axes[2].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        axes[2].axhline(y=-0.1, color='red', linestyle='--', alpha=0.5, label='Entry Threshold')
        axes[2].fill_between(data.index, data['40d_correlation'], 0,
                            where=(data['40d_correlation'] < 0), color='red', alpha=0.2)
        axes[2].set_ylabel('Correlation')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)

        # Plot 4: Cumulative PnL of trades
        if len(trades_df) > 0:
            trades_df = trades_df.sort_values('exit_date')
            cumulative_pnl = trades_df['pnl'].cumsum()
            axes[3].bar(range(len(trades_df)), trades_df['pnl'],
                       color=['green' if x > 0 else 'red' for x in trades_df['pnl']])
            axes[3].plot(range(len(trades_df)), cumulative_pnl, 'b-', linewidth=2, label='Cumulative PnL')
            axes[3].axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            axes[3].set_xlabel('Trade Number')
            axes[3].set_ylabel('PnL ($)')
            axes[3].legend()
            axes[3].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
        plt.show()

        return fig

    def optimize_parameters(self, data, param_grid):
        """
        Optimize strategy parameters using grid search.

        Parameters:
        - data: Historical price and correlation data
        - param_grid: Dictionary of parameters to test
        """
        results = []

        for entry_threshold in param_grid.get('entry_threshold', [-0.1]):
            for holding_days in param_grid.get('holding_days', [60]):
                for stop_loss in param_grid.get('stop_loss', [None]):
                    for take_profit in param_grid.get('take_profit', [None]):
                        # Reset strategy
                        self.__init__(self.initial_capital, self.fee_rate)

                        # Run backtest
                        test_data = data.copy()
                        self.backtest_simple_strategy(
                            test_data,
                            entry_threshold=entry_threshold,
                            holding_days=holding_days,
                            stop_loss=stop_loss,
                            take_profit=take_profit
                        )

                        # Calculate metrics
                        if len(self.trades) > 0:
                            metrics = self.calculate_performance_metrics(test_data)
                            metrics.update({
                                'entry_threshold': entry_threshold,
                                'holding_days': holding_days,
                                'stop_loss': stop_loss,
                                'take_profit': take_profit
                            })
                            results.append(metrics)

        return pd.DataFrame(results).sort_values('sharpe_ratio', ascending=False)


def run_strategy_backtest(correlation_data):
    """Run comprehensive strategy backtest."""
    print("\n" + "=" * 60)
    print("Trading Strategy Backtest")
    print("=" * 60)

    # Initialize strategy
    strategy = CorrelationTradingStrategy(initial_capital=100000, fee_rate=0.001)

    # Test 1: Simple fixed holding period strategy
    print("\n1. Testing Simple Strategy (60-day holding period)...")
    data_simple = correlation_data.copy()
    data_simple = strategy.backtest_simple_strategy(
        data_simple,
        entry_threshold=-0.1,
        holding_days=60,
        position_size=0.5,  # Use 50% of capital per trade
        stop_loss=0.10,      # 10% stop loss
        take_profit=0.30     # 30% take profit
    )

    metrics_simple = strategy.calculate_performance_metrics(data_simple)
    print("\nSimple Strategy Performance:")
    for key, value in metrics_simple.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # Save trade log
    if len(strategy.trades) > 0:
        strategy.trades.to_csv('simple_strategy_trades.csv')
        print(f"\nExecuted {len(strategy.trades)} trades")

    # Test 2: Dynamic correlation-based strategy
    print("\n2. Testing Dynamic Strategy (correlation-based exit)...")
    strategy2 = CorrelationTradingStrategy(initial_capital=100000, fee_rate=0.001)
    data_dynamic = correlation_data.copy()
    data_dynamic = strategy2.backtest_dynamic_strategy(
        data_dynamic,
        entry_threshold=-0.15,
        exit_correlation=0.1,
        position_size=0.5,
        max_holding_days=90,
        use_trailing_stop=True,
        trailing_stop_pct=0.15
    )

    metrics_dynamic = strategy2.calculate_performance_metrics(data_dynamic)
    print("\nDynamic Strategy Performance:")
    for key, value in metrics_dynamic.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    if len(strategy2.trades) > 0:
        strategy2.trades.to_csv('dynamic_strategy_trades.csv')

    # Test 3: Parameter optimization
    print("\n3. Running parameter optimization...")
    strategy3 = CorrelationTradingStrategy(initial_capital=100000, fee_rate=0.001)

    param_grid = {
        'entry_threshold': [-0.05, -0.10, -0.15, -0.20],
        'holding_days': [30, 45, 60, 90],
        'stop_loss': [None, 0.05, 0.10],
        'take_profit': [None, 0.20, 0.30, 0.50]
    }

    optimization_results = strategy3.optimize_parameters(correlation_data, param_grid)

    if len(optimization_results) > 0:
        print("\nTop 5 Parameter Combinations (by Sharpe Ratio):")
        print(optimization_results.head()[['entry_threshold', 'holding_days', 'stop_loss',
                                           'take_profit', 'total_return_pct', 'sharpe_ratio', 'win_rate']])
        optimization_results.to_csv('parameter_optimization_results.csv')

    # Create visualizations
    print("\n4. Creating visualizations...")
    strategy.plot_backtest_results(data_simple)

    return strategy, strategy2, data_simple, data_dynamic


if __name__ == "__main__":
    # This would be run after the correlation analysis
    print("Run btc_gold_correlation_analysis.py first to generate correlation data.")
    print("Then load the data and run this backtest.")