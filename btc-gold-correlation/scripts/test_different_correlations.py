"""
测试不同资产组合的相关性
可能的组合：
1. BTC vs 黄金现货
2. BTC vs 黄金ETF (GLD)
3. BTC vs 黄金矿业股 (GDX)
4. BTC vs 实际利率
5. BTC vs 美元指数
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def test_alternative_correlations():
    """测试可能的替代相关性组合"""

    print("="*80)
    print("测试不同资产组合的相关性（寻找Twitter可能提到的真实指标）")
    print("="*80)

    # 加载已有数据
    returns = pd.read_parquet('data/processed/log_returns.parquet')

    # 测试其他可能的黄金相关资产
    test_tickers = {
        'GLD': 'GLD',           # 黄金ETF
        'GDX': 'GDX',           # 黄金矿业股ETF
        'GDXJ': 'GDXJ',         # 初级黄金矿业股ETF
        'TLT': 'TLT',           # 20年期国债ETF（可能与实际利率相关）
    }

    print("\n下载额外测试数据...")
    extra_data = {}
    for name, ticker in test_tickers.items():
        try:
            data = yf.download(ticker, start='2015-01-01', progress=False, auto_adjust=True)
            if not data.empty and 'Close' in data.columns:
                extra_data[name] = data['Close']
                print(f"✓ {name}: {len(data)} 数据点")
        except Exception as e:
            print(f"✗ {name}: {e}")

    # 合并到returns
    for name, prices in extra_data.items():
        prices_aligned = prices.reindex(returns.index)
        returns[name] = np.log(prices_aligned / prices_aligned.shift(1))

    # 测试案例
    test_cases = [
        ('2023-10-20', '2023年10月案例'),
        ('2024-02-01', '2024年2月案例'),
        ('2024-11-01', '2024年11月案例'),
    ]

    print("\n" + "="*80)
    print("测试不同资产组合在关键日期的相关性")
    print("="*80)

    asset_pairs = [
        ('BTC', 'GOLD', 'BTC vs 黄金期货(GC=F)'),
        ('BTC', 'GLD', 'BTC vs 黄金ETF(GLD)'),
        ('BTC', 'GDX', 'BTC vs 黄金矿业股(GDX)'),
        ('BTC', 'GDXJ', 'BTC vs 初级金矿股(GDXJ)'),
        ('BTC', 'TLT', 'BTC vs 长期国债(TLT)'),
        ('BTC', 'DXY', 'BTC vs 美元指数(DXY)'),
    ]

    for date_str, case_name in test_cases:
        print(f"\n{'='*80}")
        print(f"{case_name} - {date_str}")
        print(f"{'='*80}")

        date = pd.Timestamp(date_str)

        for asset1, asset2, description in asset_pairs:
            if asset1 not in returns.columns or asset2 not in returns.columns:
                continue

            # 计算该日期的40天滚动相关性
            valid_mask = (~returns[asset1].isnull()) & (~returns[asset2].isnull())
            valid_returns = returns[valid_mask][[asset1, asset2]]

            # 找到该日期前最近的有效数据点
            available_dates = valid_returns.loc[:date].index
            if len(available_dates) < 40:
                continue

            # 取最近40个有效交易日
            recent_data = valid_returns.loc[available_dates[-40:]]

            if len(recent_data) >= 32:  # 至少80%数据
                corr = recent_data[asset1].corr(recent_data[asset2])

                # 标记负相关
                marker = "🔴" if corr < 0 else "  "
                strong = "⚠️ 强负相关" if corr < -0.2 else ""

                print(f"   {marker} {description:35s}: {corr:7.4f} {strong}")

    # 特别关注：寻找在关键时点转负的组合
    print("\n" + "="*80)
    print("🔍 寻找在关键时点相关性转负的资产组合")
    print("="*80)

    for asset1, asset2, description in asset_pairs:
        if asset1 not in returns.columns or asset2 not in returns.columns:
            continue

        # 计算完整的滚动相关性
        valid_mask = (~returns[asset1].isnull()) & (~returns[asset2].isnull())
        valid_returns = returns[valid_mask][[asset1, asset2]]

        correlation = valid_returns[asset1].rolling(window=40, min_periods=32).corr(valid_returns[asset2])

        # 检查在关键日期是否为负
        negative_dates = []
        for date_str, _ in test_cases:
            date = pd.Timestamp(date_str)
            available = correlation.loc[:date].dropna()
            if len(available) > 0:
                val = available.iloc[-1]
                if val < 0:
                    negative_dates.append(date_str)

        if len(negative_dates) >= 2:  # 至少在2个关键点负相关
            print(f"\n✅ {description}")
            print(f"   在 {len(negative_dates)}/3 个关键时点出现负相关: {negative_dates}")
            print(f"   相关性统计: 均值={correlation.mean():.3f}, 最小={correlation.min():.3f}")


if __name__ == '__main__':
    test_alternative_correlations()
