"""
快速验证历史案例 - 验证Twitter中提到的5个BTC暴涨案例

根据research_plan.md第3.2节，需要验证：
1. 相关性是否确实转负
2. BTC实际涨幅
3. 涨幅耗时
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def verify_historical_cases():
    """验证5个历史案例"""

    # 加载数据
    prices = pd.read_parquet('data/processed/aligned_prices.parquet')
    correlation = pd.read_parquet('data/processed/btc_gold_correlation_40d.parquet')

    # 定义案例（从research_plan.md）
    cases = [
        {
            'name': '2023年10月下旬',
            'start_date': '2023-10-20',
            'claimed_start_price': 25000,
            'claimed_end_price': 45000,
            'claimed_gain': '80%',
            'end_date': '2024-01-01',  # 估算3个月
        },
        {
            'name': '2024年2月初',
            'start_date': '2024-02-01',
            'claimed_start_price': 40000,
            'claimed_end_price': 70000,
            'claimed_gain': '75%',
            'end_date': '2024-05-01',  # 估算3个月
        },
        {
            'name': '2024年11月初',
            'start_date': '2024-11-01',
            'claimed_start_price': 70000,
            'claimed_end_price': 100000,
            'claimed_gain': '43%',
            'end_date': '2025-02-01',  # 估算3个月
        },
        {
            'name': '2025年4月下旬',
            'start_date': '2025-04-20',
            'claimed_start_price': 80000,
            'claimed_end_price': 120000,
            'claimed_gain': '50%',
            'status': '预测',
        },
        {
            'name': '2025年10月中下旬',
            'start_date': '2025-10-15',
            'claimed_start_price': 105000,
            'claimed_end_price': 150000,
            'claimed_gain': '43%',
            'status': '预测',
        },
    ]

    print("="*80)
    print("BTC-黄金相关性转负案例验证")
    print("="*80)
    print()

    results = []

    for i, case in enumerate(cases, 1):
        print(f"\n{'='*80}")
        print(f"案例 {i}: {case['name']}")
        print(f"{'='*80}")

        # 如果是预测，跳过验证
        if case.get('status') == '预测':
            print(f"⏭️  这是未来预测，无法验证")
            print(f"   声称起始价: ${case['claimed_start_price']:,}")
            print(f"   声称目标价: ${case['claimed_end_price']:,}")
            print(f"   声称涨幅: {case['claimed_gain']}")

            # 检查当前相关性
            start = pd.Timestamp(case['start_date'])
            if start in correlation.index:
                corr_val = correlation.loc[start, 'correlation']
                if pd.notna(corr_val):
                    print(f"   当前相关性: {corr_val:.4f} {'✓负相关' if corr_val < 0 else '✗正相关'}")
            continue

        start = pd.Timestamp(case['start_date'])
        end = pd.Timestamp(case['end_date'])

        # 1. 检查相关性是否转负
        print("\n📊 相关性检查:")

        # 查看起始日前后10天的相关性
        window_start = start - pd.Timedelta(days=10)
        window_end = start + pd.Timedelta(days=10)
        corr_window = correlation.loc[window_start:window_end, 'correlation'].dropna()

        if len(corr_window) > 0:
            print(f"   起始日前后相关性范围: {corr_window.min():.4f} 至 {corr_window.max():.4f}")

            # 起始日的相关性
            corr_at_start = None
            for offset in range(11):  # 查找前后5天
                check_date = start + pd.Timedelta(days=offset-5)
                if check_date in correlation.index:
                    val = correlation.loc[check_date, 'correlation']
                    if pd.notna(val):
                        corr_at_start = val
                        actual_start = check_date
                        break

            if corr_at_start is not None:
                is_negative = corr_at_start < 0
                print(f"   起始日相关性: {corr_at_start:.4f} ({'✅ 负相关' if is_negative else '❌ 正相关'})")

                # 检查是否是从正转负
                prev_corr = correlation.loc[:actual_start].iloc[-10:-1]['correlation'].dropna()
                if len(prev_corr) > 0:
                    was_positive = (prev_corr > 0).mean() > 0.5
                    print(f"   之前趋势: {'正相关' if was_positive else '负相关'}")
            else:
                print(f"   ⚠️  起始日无相关性数据")
        else:
            print(f"   ⚠️  起始日期附近无相关性数据")

        # 2. 检查BTC实际价格变化
        print(f"\n💰 BTC价格变化:")

        # 找到实际的起始和结束价格
        actual_start_price = None
        actual_end_price = None

        # 起始价
        for offset in range(11):
            check_date = start + pd.Timedelta(days=offset-5)
            if check_date in prices.index and pd.notna(prices.loc[check_date, 'BTC']):
                actual_start_price = prices.loc[check_date, 'BTC']
                actual_start_date = check_date
                break

        # 结束价 - 找到起始日后的峰值
        if actual_start_price is not None:
            future_prices = prices.loc[actual_start_date:end, 'BTC'].dropna()
            if len(future_prices) > 0:
                actual_end_price = future_prices.max()
                peak_date = future_prices.idxmax()
                days_to_peak = (peak_date - actual_start_date).days

        if actual_start_price and actual_end_price:
            actual_gain = (actual_end_price / actual_start_price - 1) * 100
            claimed_gain = float(case['claimed_gain'].rstrip('%'))

            print(f"   声称: ${case['claimed_start_price']:,} → ${case['claimed_end_price']:,} ({case['claimed_gain']})")
            print(f"   实际: ${actual_start_price:,.0f} → ${actual_end_price:,.0f} (+{actual_gain:.1f}%)")
            print(f"   涨幅耗时: {days_to_peak}天")
            print(f"   峰值日期: {peak_date.date()}")

            # 判断
            gain_match = abs(actual_gain - claimed_gain) < 20  # 允许20%误差
            if gain_match:
                print(f"   ✅ 涨幅基本匹配")
            else:
                print(f"   ⚠️  涨幅差异较大 (差{actual_gain - claimed_gain:.1f}%)")

            results.append({
                'case': case['name'],
                'correlation_negative': corr_at_start < 0 if corr_at_start else None,
                'claimed_gain': claimed_gain,
                'actual_gain': actual_gain,
                'days_to_peak': days_to_peak,
            })
        else:
            print(f"   ⚠️  无法获取完整价格数据")

    # 总结
    print(f"\n\n{'='*80}")
    print("📈 验证总结")
    print(f"{'='*80}\n")

    if results:
        df = pd.DataFrame(results)
        print(df.to_string(index=False))

        print(f"\n✅ 相关性转负的案例: {df['correlation_negative'].sum()}/{len(df)}")
        print(f"📊 平均实际涨幅: {df['actual_gain'].mean():.1f}%")
        print(f"⏱️  平均到达峰值天数: {df['days_to_peak'].mean():.0f}天")


if __name__ == '__main__':
    verify_historical_cases()
