"""
验证相关性转弱是否为BTC上涨的领先信号

核心问题：
当BTC-黄金相关性转弱（从强相关→弱相关/负相关）时，
是否预示着未来30/60/90天内BTC将有显著涨幅？

验证逻辑：
1. 识别所有"相关性转弱"的时点
2. 计算这些时点之后N天的BTC表现
3. 与随机时点的BTC表现对比
4. 计算信号的预测准确率和期望收益
"""

import pandas as pd
import numpy as np
from datetime import timedelta
from scipy import stats


def identify_correlation_weakening_signals():
    """识别相关性转弱的信号"""

    prices = pd.read_parquet('data/processed/aligned_prices.parquet')
    correlation = pd.read_parquet('data/processed/btc_gold_correlation_40d.parquet')['correlation'].dropna()

    print("="*90)
    print("验证：相关性转弱是否为BTC上涨的领先信号")
    print("="*90)

    # 定义"相关性转弱"的几种情况
    signal_definitions = {
        '从强正转弱正': {'from_min': 0.3, 'from_max': 1.0, 'to_min': -0.1, 'to_max': 0.15},
        '从正转负': {'from_min': 0.1, 'from_max': 1.0, 'to_min': -1.0, 'to_max': -0.05},
        '从任意转接近零': {'from_min': -1.0, 'from_max': 1.0, 'to_min': -0.1, 'to_max': 0.1},
        '相关性下降>0.2': {'type': 'decline', 'threshold': 0.2},
        '相关性下降>0.3': {'type': 'decline', 'threshold': 0.3},
    }

    all_results = {}

    for signal_name, criteria in signal_definitions.items():
        print(f"\n{'='*90}")
        print(f"信号定义：{signal_name}")
        print(f"{'='*90}")

        signals = []

        if criteria.get('type') == 'decline':
            # 基于相关性下降幅度
            threshold = criteria['threshold']

            for i in range(20, len(correlation)):
                current_corr = correlation.iloc[i]
                # 查看过去10-20天的相关性
                past_corr = correlation.iloc[i-20:i-10].mean()

                decline = past_corr - current_corr

                if decline >= threshold:  # 相关性下降超过阈值
                    signals.append({
                        'date': correlation.index[i],
                        'correlation': current_corr,
                        'past_correlation': past_corr,
                        'decline': decline
                    })
        else:
            # 基于相关性从某区间转到另一区间
            for i in range(20, len(correlation)):
                current_corr = correlation.iloc[i]
                # 过去10-20天的平均相关性
                past_corr = correlation.iloc[i-20:i-10].mean()

                # 检查是否满足"从...转..."的条件
                from_condition = (criteria['from_min'] <= past_corr <= criteria['from_max'])
                to_condition = (criteria['to_min'] <= current_corr <= criteria['to_max'])

                if from_condition and to_condition:
                    signals.append({
                        'date': correlation.index[i],
                        'correlation': current_corr,
                        'past_correlation': past_corr,
                        'decline': past_corr - current_corr
                    })

        # 去重（避免连续触发）
        if signals:
            df_signals = pd.DataFrame(signals)
            # 相邻30天内只保留第一个信号
            df_signals = df_signals.sort_values('date')
            df_signals['days_since_last'] = df_signals['date'].diff().dt.days
            df_signals = df_signals[(df_signals['days_since_last'].isna()) | (df_signals['days_since_last'] > 30)]
            signals = df_signals.to_dict('records')

        print(f"\n识别到 {len(signals)} 个信号")

        if len(signals) == 0:
            print("无信号，跳过")
            continue

        # 计算这些信号后的BTC表现
        forward_periods = [30, 60, 90]
        results = {period: [] for period in forward_periods}

        for signal in signals:
            date = signal['date']
            btc_start = prices.loc[date, 'BTC'] if date in prices.index else None

            if pd.isna(btc_start):
                continue

            for period in forward_periods:
                end_date = date + pd.Timedelta(days=period)
                btc_future = prices.loc[date:end_date, 'BTC'].dropna()

                if len(btc_future) > 5:
                    btc_peak = btc_future.max()
                    btc_end = btc_future.iloc[-1]

                    gain_to_peak = (btc_peak / btc_start - 1) * 100
                    gain_to_end = (btc_end / btc_start - 1) * 100

                    results[period].append({
                        'date': date,
                        'gain_to_peak': gain_to_peak,
                        'gain_to_end': gain_to_end
                    })

        # 统计结果
        print(f"\n前瞻性表现：")
        print(f"{'期间':<10s} {'信号数':>8s} {'平均涨至峰':>12s} {'中位涨至峰':>12s} {'平均持有至末':>15s} {'胜率(>0)':>10s}")
        print("-"*90)

        signal_results = {}

        for period in forward_periods:
            if results[period]:
                gains_peak = [r['gain_to_peak'] for r in results[period]]
                gains_end = [r['gain_to_end'] for r in results[period]]

                avg_peak = np.mean(gains_peak)
                median_peak = np.median(gains_peak)
                avg_end = np.mean(gains_end)
                win_rate = sum(1 for g in gains_end if g > 0) / len(gains_end) * 100

                print(f"{period}天后     {len(results[period]):>6d}    {avg_peak:>10.1f}%    {median_peak:>10.1f}%    {avg_end:>13.1f}%    {win_rate:>8.1f}%")

                signal_results[period] = {
                    'count': len(results[period]),
                    'avg_peak': avg_peak,
                    'median_peak': median_peak,
                    'avg_end': avg_end,
                    'win_rate': win_rate,
                    'all_gains': gains_end
                }

        all_results[signal_name] = signal_results

    # 对比：随机时点的BTC表现（基准）
    print(f"\n\n{'='*90}")
    print("基准对比：随机时点的BTC表现")
    print(f"{'='*90}\n")

    # 随机选择与信号数量相同的时点
    valid_dates = prices['BTC'].dropna().index
    np.random.seed(42)

    baseline_results = {}

    for period in forward_periods:
        random_gains_peak = []
        random_gains_end = []

        # 随机选择200个时点
        for _ in range(200):
            idx = np.random.randint(0, len(valid_dates) - period - 10)
            date = valid_dates[idx]
            btc_start = prices.loc[date, 'BTC']

            end_date = date + pd.Timedelta(days=period)
            btc_future = prices.loc[date:end_date, 'BTC'].dropna()

            if len(btc_future) > 5:
                btc_peak = btc_future.max()
                btc_end = btc_future.iloc[-1]

                random_gains_peak.append((btc_peak / btc_start - 1) * 100)
                random_gains_end.append((btc_end / btc_start - 1) * 100)

        avg_peak = np.mean(random_gains_peak)
        median_peak = np.median(random_gains_peak)
        avg_end = np.mean(random_gains_end)
        win_rate = sum(1 for g in random_gains_end if g > 0) / len(random_gains_end) * 100

        baseline_results[period] = {
            'avg_peak': avg_peak,
            'median_peak': median_peak,
            'avg_end': avg_end,
            'win_rate': win_rate
        }

    print(f"{'期间':<10s} {'样本数':>8s} {'平均涨至峰':>12s} {'中位涨至峰':>12s} {'平均持有至末':>15s} {'胜率(>0)':>10s}")
    print("-"*90)
    for period in forward_periods:
        br = baseline_results[period]
        print(f"{period}天后     {200:>6d}    {br['avg_peak']:>10.1f}%    {br['median_peak']:>10.1f}%    {br['avg_end']:>13.1f}%    {br['win_rate']:>8.1f}%")

    # 统计检验
    print(f"\n\n{'='*90}")
    print("统计显著性检验（信号 vs 随机基准）")
    print(f"{'='*90}\n")

    for signal_name, signal_data in all_results.items():
        if not signal_data:
            continue

        print(f"\n信号：{signal_name}")
        print("-"*90)

        for period in forward_periods:
            if period not in signal_data:
                continue

            signal_gains = signal_data[period]['all_gains']
            baseline_gains = []

            # 重新生成基准数据（与信号数量相同）
            for _ in range(len(signal_gains)):
                idx = np.random.randint(0, len(valid_dates) - period - 10)
                date = valid_dates[idx]
                btc_start = prices.loc[date, 'BTC']
                end_date = date + pd.Timedelta(days=period)
                btc_future = prices.loc[date:end_date, 'BTC'].dropna()
                if len(btc_future) > 5:
                    btc_end = btc_future.iloc[-1]
                    baseline_gains.append((btc_end / btc_start - 1) * 100)

            # t检验
            if len(signal_gains) >= 5 and len(baseline_gains) >= 5:
                t_stat, p_value = stats.ttest_ind(signal_gains, baseline_gains)

                signal_avg = np.mean(signal_gains)
                baseline_avg = np.mean(baseline_gains)
                outperformance = signal_avg - baseline_avg

                significance = "✅ 显著" if p_value < 0.05 else ("⚠️  边缘" if p_value < 0.1 else "❌ 不显著")

                print(f"  {period}天: 信号{signal_avg:>6.1f}% vs 基准{baseline_avg:>6.1f}% | "
                      f"超额{outperformance:>+6.1f}% | p={p_value:.4f} {significance}")

    # 最佳信号推荐
    print(f"\n\n{'='*90}")
    print("🏆 最佳信号推荐")
    print(f"{'='*90}\n")

    # 找到表现最好的信号（60天期）
    best_signals = []
    for signal_name, signal_data in all_results.items():
        if 60 in signal_data and signal_data[60]['count'] >= 5:
            best_signals.append({
                'name': signal_name,
                'avg_gain': signal_data[60]['avg_end'],
                'median_gain': signal_data[60]['median_peak'],
                'win_rate': signal_data[60]['win_rate'],
                'sample_size': signal_data[60]['count']
            })

    if best_signals:
        df_best = pd.DataFrame(best_signals).sort_values('median_gain', ascending=False)
        print("按60天后中位涨至峰值排序：\n")
        print(df_best.to_string(index=False))

        print("\n推荐：")
        top_signal = df_best.iloc[0]
        print(f"  最佳信号: {top_signal['name']}")
        print(f"  样本数: {top_signal['sample_size']}")
        print(f"  60天后平均持有收益: {top_signal['avg_gain']:.1f}%")
        print(f"  60天内中位峰值收益: {top_signal['median_gain']:.1f}%")
        print(f"  胜率: {top_signal['win_rate']:.1f}%")

        # 与基准对比
        baseline_60 = baseline_results[60]
        outperform = top_signal['avg_gain'] - baseline_60['avg_end']
        print(f"\n  超越随机基准: {outperform:+.1f}%")

        if outperform > 10:
            print(f"  ✅ 该信号具有显著的预测价值！")
        elif outperform > 5:
            print(f"  ⚠️  该信号有一定预测价值，但优势不明显")
        else:
            print(f"  ❌ 该信号无明显预测价值")

    print("\n" + "="*90)


if __name__ == '__main__':
    identify_correlation_weakening_signals()
