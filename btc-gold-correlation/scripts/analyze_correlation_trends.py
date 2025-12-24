"""
分析相关性变化趋势与BTC涨幅的关系

核心假设：BTC的大涨通常开始于BTC-黄金相关性最弱（接近0或刚转负）的时候
而不是相关性深度负值或高度正值的时候
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta


def analyze_correlation_trend_and_btc_rallies():
    """分析相关性趋势与BTC涨幅的关系"""

    prices = pd.read_parquet('data/processed/aligned_prices.parquet')
    returns = pd.read_parquet('data/processed/log_returns.parquet')
    correlation = pd.read_parquet('data/processed/btc_gold_correlation_40d.parquet')['correlation']

    print("="*90)
    print("分析：BTC大涨是否始于相关性最弱时刻")
    print("="*90)

    # 1. 找到所有BTC的显著上涨周期
    print("\n📊 第一步：识别BTC的显著上涨周期")
    print("-"*90)

    btc_rallies = []
    lookback = 30  # 回溯30天找起点
    forward = 120  # 前瞻120天找峰值

    for i in range(lookback, len(prices) - forward, 5):  # 每5天检查一次
        date = prices.index[i]
        btc_price = prices.iloc[i]['BTC']

        if pd.isna(btc_price):
            continue

        # 查看未来120天的峰值
        future_prices = prices.iloc[i:i+forward]['BTC'].dropna()
        if len(future_prices) < 30:
            continue

        peak_price = future_prices.max()
        gain = (peak_price / btc_price - 1) * 100

        # 只关注涨幅>30%的显著上涨
        if gain > 30:
            peak_date = future_prices.idxmax()
            days_to_peak = (peak_date - date).days

            # 获取该日期的相关性
            corr_value = None
            corr_trend = None  # 相关性变化趋势

            if date in correlation.index:
                corr_value = correlation.loc[date]

                # 计算相关性趋势（过去20天的变化）
                past_corr = correlation.loc[:date].tail(20)
                if len(past_corr) > 10:
                    corr_trend = past_corr.iloc[-1] - past_corr.iloc[0]  # 正值=上升，负值=下降

            # 黄金同期表现
            gold_start = prices.iloc[i]['GOLD']
            gold_at_peak = prices.loc[peak_date]['GOLD'] if peak_date in prices.index else None
            gold_gain = (gold_at_peak / gold_start - 1) * 100 if gold_at_peak and not pd.isna(gold_at_peak) and not pd.isna(gold_start) else None

            btc_rallies.append({
                'start_date': date,
                'peak_date': peak_date,
                'days_to_peak': days_to_peak,
                'btc_gain': gain,
                'btc_start_price': btc_price,
                'btc_peak_price': peak_price,
                'correlation_at_start': corr_value,
                'correlation_trend': corr_trend,
                'gold_gain': gold_gain
            })

    # 去重（避免同一个上涨周期被多次计数）
    df = pd.DataFrame(btc_rallies)
    df = df.sort_values('btc_gain', ascending=False).drop_duplicates(
        subset=['peak_date'], keep='first'
    ).sort_values('start_date')

    print(f"共识别出 {len(df)} 个显著BTC上涨周期（涨幅>30%）\n")

    # 2. 按相关性区间分组分析
    print("="*90)
    print("📈 第二步：按起始相关性分组分析")
    print("="*90)

    df_valid = df.dropna(subset=['correlation_at_start'])

    # 定义相关性区间
    bins = [-1, -0.3, -0.1, 0.1, 0.3, 1]
    labels = ['强负相关(<-0.3)', '弱负相关(-0.3~-0.1)', '接近零(-0.1~0.1)', '弱正相关(0.1~0.3)', '强正相关(>0.3)']
    df_valid['corr_group'] = pd.cut(df_valid['correlation_at_start'], bins=bins, labels=labels)

    print("\n相关性区间统计：")
    print("-"*90)
    for label in labels:
        group = df_valid[df_valid['corr_group'] == label]
        if len(group) > 0:
            print(f"\n{label} ({len(group)}个案例):")
            print(f"  平均BTC涨幅: {group['btc_gain'].mean():.1f}%")
            print(f"  最大BTC涨幅: {group['btc_gain'].max():.1f}%")
            print(f"  平均到峰时间: {group['days_to_peak'].mean():.0f}天")

    # 3. 关键发现：相关性趋势分析
    print("\n\n" + "="*90)
    print("🔍 第三步：相关性变化趋势分析")
    print("="*90)

    df_trend = df.dropna(subset=['correlation_trend'])

    print("\n按相关性变化趋势分组：")
    print("-"*90)

    # 下降趋势（从正变负或从高变低）
    declining = df_trend[df_trend['correlation_trend'] < -0.1]
    print(f"\n📉 相关性快速下降（趋势<-0.1）- {len(declining)}个案例:")
    if len(declining) > 0:
        print(f"  平均BTC涨幅: {declining['btc_gain'].mean():.1f}%")
        print(f"  平均到峰时间: {declining['days_to_peak'].mean():.0f}天")

    # 稳定/小幅变化
    stable = df_trend[(df_trend['correlation_trend'] >= -0.1) & (df_trend['correlation_trend'] <= 0.1)]
    print(f"\n➡️  相关性稳定（趋势-0.1~0.1）- {len(stable)}个案例:")
    if len(stable) > 0:
        print(f"  平均BTC涨幅: {stable['btc_gain'].mean():.1f}%")
        print(f"  平均到峰时间: {stable['days_to_peak'].mean():.0f}天")

    # 上升趋势
    rising = df_trend[df_trend['correlation_trend'] > 0.1]
    print(f"\n📈 相关性快速上升（趋势>0.1）- {len(rising)}个案例:")
    if len(rising) > 0:
        print(f"  平均BTC涨幅: {rising['btc_gain'].mean():.1f}%")
        print(f"  平均到峰时间: {rising['days_to_peak'].mean():.0f}天")

    # 4. 综合分析：相关性绝对值 vs 涨幅
    print("\n\n" + "="*90)
    print("💡 第四步：相关性强度与BTC涨幅的关系")
    print("="*90)

    df_valid['corr_abs'] = df_valid['correlation_at_start'].abs()

    # 按相关性绝对值分组
    print("\n按相关性强度分组（不区分正负）：")
    print("-"*90)

    weak_corr = df_valid[df_valid['corr_abs'] < 0.15]  # 弱相关
    medium_corr = df_valid[(df_valid['corr_abs'] >= 0.15) & (df_valid['corr_abs'] < 0.35)]  # 中等
    strong_corr = df_valid[df_valid['corr_abs'] >= 0.35]  # 强相关

    print(f"\n🎯 弱相关（|相关性|<0.15）- {len(weak_corr)}个案例:")
    print(f"  平均BTC涨幅: {weak_corr['btc_gain'].mean():.1f}%")
    print(f"  中位数涨幅: {weak_corr['btc_gain'].median():.1f}%")

    print(f"\n📊 中等相关（|相关性|0.15~0.35）- {len(medium_corr)}个案例:")
    print(f"  平均BTC涨幅: {medium_corr['btc_gain'].mean():.1f}%")
    print(f"  中位数涨幅: {medium_corr['btc_gain'].median():.1f}%")

    print(f"\n🔗 强相关（|相关性|>0.35）- {len(strong_corr)}个案例:")
    print(f"  平均BTC涨幅: {strong_corr['btc_gain'].mean():.1f}%")
    print(f"  中位数涨幅: {strong_corr['btc_gain'].median():.1f}%")

    # 5. 最佳案例详细列表
    print("\n\n" + "="*90)
    print("🏆 前15个最大BTC涨幅案例详情")
    print("="*90)

    top_rallies = df.nlargest(15, 'btc_gain')

    print("\n{:12s} {:>8s} {:>8s} {:>6s} {:>8s} {:>8s} {:>10s}".format(
        '起始日期', 'BTC涨幅', '天数', '黄金%', '起始相关性', '相关性趋势', '相关性强度'
    ))
    print("-"*90)

    for _, row in top_rallies.iterrows():
        corr = row['correlation_at_start']
        corr_str = f"{corr:.3f}" if pd.notna(corr) else "N/A"

        trend = row['correlation_trend']
        trend_str = f"{trend:+.3f}" if pd.notna(trend) else "N/A"

        abs_corr = abs(corr) if pd.notna(corr) else None
        strength = "弱" if abs_corr and abs_corr < 0.15 else ("中" if abs_corr and abs_corr < 0.35 else "强")

        gold = row['gold_gain']
        gold_str = f"{gold:+6.1f}%" if pd.notna(gold) else "N/A"

        print("{:12s} {:>7.1f}% {:>6d}天 {:>8s} {:>10s} {:>10s} {:>10s}".format(
            row['start_date'].strftime('%Y-%m-%d'),
            row['btc_gain'],
            row['days_to_peak'],
            gold_str,
            corr_str,
            trend_str,
            strength
        ))

    # 6. 关键结论
    print("\n\n" + "="*90)
    print("📌 关键结论")
    print("="*90)

    # 计算相关性在不同区间的中位数涨幅
    weak_median = weak_corr['btc_gain'].median() if len(weak_corr) > 0 else 0
    medium_median = medium_corr['btc_gain'].median() if len(medium_corr) > 0 else 0
    strong_median = strong_corr['btc_gain'].median() if len(strong_corr) > 0 else 0

    print(f"\n1. 相关性强度与BTC涨幅关系：")
    print(f"   弱相关(|r|<0.15): 中位数涨幅 {weak_median:.1f}%")
    print(f"   中等相关: 中位数涨幅 {medium_median:.1f}%")
    print(f"   强相关: 中位数涨幅 {strong_median:.1f}%")

    if weak_median > medium_median and weak_median > strong_median:
        print(f"\n   ✅ 验证：BTC大涨确实更容易发生在相关性较弱时！")
    else:
        print(f"\n   ❌ 数据不支持：弱相关时BTC涨幅并非最大")

    # 相关性下降趋势
    if len(declining) > 0 and len(rising) > 0:
        decline_avg = declining['btc_gain'].mean()
        rise_avg = rising['btc_gain'].mean()

        print(f"\n2. 相关性变化趋势：")
        print(f"   相关性下降时: 平均涨幅 {decline_avg:.1f}%")
        print(f"   相关性上升时: 平均涨幅 {rise_avg:.1f}%")

        if decline_avg > rise_avg * 1.2:
            print(f"\n   ✅ 验证：相关性下降（解耦）时BTC涨幅更大！")
        else:
            print(f"\n   ⚠️  差异不明显")

    # 保存结果
    output_file = 'data/processed/btc_rallies_with_correlation.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✅ 详细数据已保存至: {output_file}")


if __name__ == '__main__':
    analyze_correlation_trend_and_btc_rallies()
