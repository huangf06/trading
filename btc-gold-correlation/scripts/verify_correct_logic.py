"""
重新验证作者的真实逻辑

作者真正的信号链条（从两则推文综合）：
1. 黄金先涨（侦察兵）
2. 黄金停下来/调整 → BTC与黄金相关性转负
3. BTC爆发式上涨（大军）

关键：不是"相关性转负时立即买入"，而是"相关性转负后的某个时点BTC会爆发"
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta


def analyze_gold_btc_sequence():
    """分析黄金-BTC的时间序列关系"""

    prices = pd.read_parquet('data/processed/aligned_prices.parquet')
    returns = pd.read_parquet('data/processed/log_returns.parquet')
    correlation = pd.read_parquet('data/processed/btc_gold_correlation_40d.parquet')

    print("="*80)
    print("重新验证：黄金先涨 → 相关性转负 → BTC爆发")
    print("="*80)

    # 寻找相关性转负的时点（从正转负）
    valid_corr = correlation['correlation'].dropna()

    # 找到相关性从正转负的时刻
    corr_turns_negative = []
    for i in range(1, len(valid_corr)):
        prev_val = valid_corr.iloc[i-1]
        curr_val = valid_corr.iloc[i]

        # 从正相关变为负相关，且负相关程度足够
        if prev_val > 0 and curr_val < -0.1:
            corr_turns_negative.append({
                'date': valid_corr.index[i],
                'correlation': curr_val,
                'prev_correlation': prev_val
            })

    print(f"\n找到 {len(corr_turns_negative)} 个相关性从正转负的时点\n")

    # 案例定义
    claimed_cases = [
        {'period': '2023年10月下旬', 'approx_date': '2023-10-20', 'start_price': 25000, 'end_price': 45000},
        {'period': '2024年2月初', 'approx_date': '2024-02-01', 'start_price': 40000, 'end_price': 70000},
        {'period': '2024年11月初', 'approx_date': '2024-11-01', 'start_price': 70000, 'end_price': 100000},
    ]

    for case in claimed_cases:
        date = pd.Timestamp(case['approx_date'])
        print(f"{'='*80}")
        print(f"{case['period']} - {case['approx_date']}")
        print(f"{'='*80}")

        # 1. 检查之前的黄金表现
        print("\n📊 第一步：黄金之前是否上涨？")

        # 查看该日期前3个月黄金的表现
        lookback_start = date - pd.Timedelta(days=90)
        gold_window = prices.loc[lookback_start:date, 'GOLD'].dropna()

        if len(gold_window) > 0:
            gold_gain = (gold_window.iloc[-1] / gold_window.iloc[0] - 1) * 100
            print(f"   黄金前3个月涨幅: {gold_gain:.1f}%")

            # 黄金是否在高位（近期峰值）
            gold_peak = gold_window.max()
            gold_current = gold_window.iloc[-1]
            from_peak = (gold_current / gold_peak - 1) * 100
            print(f"   距离近期峰值: {from_peak:.1f}%")

        # 2. 检查相关性何时转负
        print("\n📉 第二步：相关性何时转负？")

        # 查看该日期前后的相关性
        corr_window = correlation.loc[date - pd.Timedelta(days=60):date + pd.Timedelta(days=30)].dropna()

        if len(corr_window) > 0:
            # 找到最早转负的日期
            negative_dates = corr_window[corr_window['correlation'] < 0]
            if len(negative_dates) > 0:
                first_negative = negative_dates.index[0]
                print(f"   首次转负: {first_negative.date()} (相关性: {negative_dates.iloc[0]['correlation']:.4f})")

                days_before_claimed = (date - first_negative).days
                print(f"   距离声称日期: {days_before_claimed}天")

            # 显示该区间相关性范围
            print(f"   该时期相关性范围: {corr_window['correlation'].min():.4f} 至 {corr_window['correlation'].max():.4f}")

        # 3. 检查BTC在相关性转负后的表现
        print("\n🚀 第三步：BTC在相关性转负后的表现")

        # 从声称日期开始，找未来3个月的BTC峰值
        future_window_end = date + pd.Timedelta(days=120)
        btc_future = prices.loc[date:future_window_end, 'BTC'].dropna()

        if len(btc_future) > 0:
            btc_start = btc_future.iloc[0]
            btc_peak = btc_future.max()
            btc_gain = (btc_peak / btc_start - 1) * 100
            peak_date = btc_future.idxmax()
            days_to_peak = (peak_date - date).days

            print(f"   起始价: ${btc_start:,.0f}")
            print(f"   峰值价: ${btc_peak:,.0f} (+{btc_gain:.1f}%)")
            print(f"   到达峰值: {days_to_peak}天 ({peak_date.date()})")

            # 与作者声称对比
            claimed_gain = (case['end_price'] / case['start_price'] - 1) * 100
            print(f"   作者声称: ${case['start_price']:,} → ${case['end_price']:,} (+{claimed_gain:.0f}%)")

    # 统计分析：黄金涨后BTC的表现
    print(f"\n\n{'='*80}")
    print("📈 统计分析：黄金上涨后，BTC的表现")
    print(f"{'='*80}\n")

    # 找到黄金上涨周期（连续3个月涨幅>10%）
    gold_rallies = []
    window_size = 60  # 约3个月

    for i in range(window_size, len(prices)-120, 10):  # 每10天检查一次
        start_idx = i - window_size
        gold_window = prices.iloc[start_idx:i]['GOLD'].dropna()

        if len(gold_window) > 30:  # 确保有足够数据点
            gold_gain = (gold_window.iloc[-1] / gold_window.iloc[0] - 1) * 100

            if gold_gain > 10:  # 黄金涨幅>10%
                date = prices.index[i]

                # 查看之后3-6个月BTC的表现
                btc_future = prices.loc[date:date + pd.Timedelta(days=180), 'BTC'].dropna()

                if len(btc_future) > 0:
                    btc_start = btc_future.iloc[0]
                    btc_peak = btc_future.max()
                    btc_gain = (btc_peak / btc_start - 1) * 100

                    # 查看该时期相关性
                    corr_at_date = correlation.loc[date:date + pd.Timedelta(days=7)].dropna()
                    avg_corr = corr_at_date['correlation'].mean() if len(corr_at_date) > 0 else None

                    gold_rallies.append({
                        'date': date,
                        'gold_gain': gold_gain,
                        'btc_subsequent_gain': btc_gain,
                        'correlation': avg_corr,
                        'days_to_btc_peak': (btc_future.idxmax() - date).days
                    })

    # 筛选黄金涨后相关性转负的案例
    df = pd.DataFrame(gold_rallies)
    if len(df) > 0:
        df = df.drop_duplicates(subset=['date'], keep='first')

        print("黄金上涨周期统计（涨幅>10%）：")
        print(f"  总共发现: {len(df)} 个黄金上涨周期")
        print(f"  BTC平均后续涨幅: {df['btc_subsequent_gain'].mean():.1f}%")
        print(f"  BTC平均到峰时间: {df['days_to_btc_peak'].mean():.0f}天")

        # 按相关性分组
        negative_corr = df[df['correlation'] < 0]
        positive_corr = df[df['correlation'] > 0]

        print(f"\n当相关性为负时（{len(negative_corr)}个案例）：")
        if len(negative_corr) > 0:
            print(f"  BTC平均涨幅: {negative_corr['btc_subsequent_gain'].mean():.1f}%")

        print(f"\n当相关性为正时（{len(positive_corr)}个案例）：")
        if len(positive_corr) > 0:
            print(f"  BTC平均涨幅: {positive_corr['btc_subsequent_gain'].mean():.1f}%")

        # 显示前10个最佳案例
        print(f"\n\n前10个BTC最佳表现案例：")
        top_cases = df.nlargest(10, 'btc_subsequent_gain')
        print(top_cases[['date', 'gold_gain', 'btc_subsequent_gain', 'correlation', 'days_to_btc_peak']].to_string(index=False))


if __name__ == '__main__':
    analyze_gold_btc_sequence()
