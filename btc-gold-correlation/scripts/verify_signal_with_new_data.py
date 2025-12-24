"""
使用改进的新数据重新验证信号
对比新旧数据的验证结果

数据源：
- 新数据: improved_data_*.parquet (不使用forward fill)
- 旧数据: data/processed/*.parquet (使用forward fill)
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')


def load_new_data():
    """加载新数据（正确处理的）"""
    prices = pd.read_parquet('improved_data_prices.parquet')
    correlation = pd.read_parquet('improved_data_correlation.parquet')['correlation'].dropna()

    return prices, correlation


def load_old_data():
    """加载旧数据（可能被forward fill污染的）"""
    try:
        prices = pd.read_parquet('data/processed/aligned_prices.parquet')
        correlation = pd.read_parquet('data/processed/btc_gold_correlation_40d.parquet')['correlation'].dropna()
        return prices, correlation
    except:
        return None, None


def identify_signals(correlation, signal_name, criteria):
    """识别信号"""
    signals = []

    if criteria.get('type') == 'decline':
        threshold = criteria['threshold']

        for i in range(20, len(correlation)):
            current_corr = correlation.iloc[i]
            past_corr = correlation.iloc[i-20:i-10].mean()
            decline = past_corr - current_corr

            if decline >= threshold:
                signals.append({
                    'date': correlation.index[i],
                    'correlation': current_corr,
                    'past_correlation': past_corr,
                    'decline': decline
                })
    else:
        for i in range(20, len(correlation)):
            current_corr = correlation.iloc[i]
            past_corr = correlation.iloc[i-20:i-10].mean()

            from_condition = (criteria['from_min'] <= past_corr <= criteria['from_max'])
            to_condition = (criteria['to_min'] <= current_corr <= criteria['to_max'])

            if from_condition and to_condition:
                signals.append({
                    'date': correlation.index[i],
                    'correlation': current_corr,
                    'past_correlation': past_corr,
                    'decline': past_corr - current_corr
                })

    # 去重
    if signals:
        df_signals = pd.DataFrame(signals)
        df_signals = df_signals.sort_values('date')
        df_signals['days_since_last'] = df_signals['date'].diff().dt.days
        df_signals = df_signals[(df_signals['days_since_last'].isna()) | (df_signals['days_since_last'] > 30)]
        signals = df_signals.to_dict('records')

    return signals


def calculate_forward_returns(signals, prices, periods=[30, 60, 90]):
    """计算前瞻性收益"""
    results = {period: [] for period in periods}

    for signal in signals:
        date = signal['date']
        btc_start = prices.loc[date, 'BTC'] if date in prices.index else None

        if pd.isna(btc_start):
            continue

        for period in periods:
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

    return results


def calculate_baseline(prices, periods=[30, 60, 90], n_samples=200):
    """计算随机基准"""
    valid_dates = prices['BTC'].dropna().index
    np.random.seed(42)

    baseline_results = {}

    for period in periods:
        random_gains_peak = []
        random_gains_end = []

        for _ in range(n_samples):
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

        baseline_results[period] = {
            'avg_peak': np.mean(random_gains_peak),
            'median_peak': np.median(random_gains_peak),
            'avg_end': np.mean(random_gains_end),
            'win_rate': sum(1 for g in random_gains_end if g > 0) / len(random_gains_end) * 100,
            'all_gains': random_gains_end
        }

    return baseline_results


def run_full_verification(prices, correlation, data_label):
    """运行完整验证"""

    print("="*90)
    print(f"📊 {data_label} - 信号验证")
    print("="*90)
    print(f"\n数据范围: {prices.index[0].date()} 至 {prices.index[-1].date()}")
    print(f"总天数: {len(prices)}")
    print(f"相关性数据点: {len(correlation)}\n")

    # 信号定义
    signal_definitions = {
        '从强正转弱正': {'from_min': 0.3, 'from_max': 1.0, 'to_min': -0.1, 'to_max': 0.15},
        '从正转负': {'from_min': 0.1, 'from_max': 1.0, 'to_min': -1.0, 'to_max': -0.05},
        '从任意转接近零': {'from_min': -1.0, 'from_max': 1.0, 'to_min': -0.1, 'to_max': 0.1},
        '相关性下降>0.2': {'type': 'decline', 'threshold': 0.2},
        '相关性下降>0.3': {'type': 'decline', 'threshold': 0.3},
    }

    all_results = {}

    for signal_name, criteria in signal_definitions.items():
        signals = identify_signals(correlation, signal_name, criteria)

        if len(signals) == 0:
            continue

        results = calculate_forward_returns(signals, prices)

        # 存储结果
        signal_data = {}
        for period in [30, 60, 90]:
            if results[period]:
                gains_peak = [r['gain_to_peak'] for r in results[period]]
                gains_end = [r['gain_to_end'] for r in results[period]]

                signal_data[period] = {
                    'count': len(results[period]),
                    'avg_peak': np.mean(gains_peak),
                    'median_peak': np.median(gains_peak),
                    'avg_end': np.mean(gains_end),
                    'win_rate': sum(1 for g in gains_end if g > 0) / len(gains_end) * 100,
                    'all_gains': gains_end,
                    'signals': signals
                }

        all_results[signal_name] = signal_data

    # 计算基准
    baseline = calculate_baseline(prices)

    return all_results, baseline


def print_signal_summary(signal_name, signal_data, baseline, periods=[30, 60, 90]):
    """打印信号摘要"""
    print(f"\n{'='*90}")
    print(f"信号：{signal_name}")
    print(f"{'='*90}\n")

    print(f"{'期间':<10s} {'信号数':>8s} {'平均涨至峰':>12s} {'中位涨至峰':>12s} {'平均持有至末':>15s} {'胜率(>0)':>10s} {'超额收益':>10s}")
    print("-"*90)

    for period in periods:
        if period in signal_data:
            sd = signal_data[period]
            bl = baseline[period]
            outperform = sd['avg_end'] - bl['avg_end']

            print(f"{period}天后     {sd['count']:>6d}    {sd['avg_peak']:>10.1f}%    {sd['median_peak']:>10.1f}%    "
                  f"{sd['avg_end']:>13.1f}%    {sd['win_rate']:>8.1f}%    {outperform:>+8.1f}%")


def compare_new_vs_old():
    """对比新旧数据的验证结果"""

    print("\n" + "🔬"*45)
    print("数据源对比验证：新数据(正确) vs 旧数据(可能被污染)")
    print("🔬"*45 + "\n")

    # 加载数据
    new_prices, new_correlation = load_new_data()
    old_prices, old_correlation = load_old_data()

    # 新数据验证
    print("\n" + "🆕"*45)
    new_results, new_baseline = run_full_verification(new_prices, new_correlation, "新数据（不使用forward fill）")

    # 打印新数据的信号结果
    for signal_name, signal_data in new_results.items():
        if signal_data:
            print_signal_summary(signal_name, signal_data, new_baseline)

    # 打印新数据基准
    print(f"\n\n{'='*90}")
    print("新数据 - 随机基准")
    print(f"{'='*90}\n")
    print(f"{'期间':<10s} {'样本数':>8s} {'平均涨至峰':>12s} {'中位涨至峰':>12s} {'平均持有至末':>15s} {'胜率(>0)':>10s}")
    print("-"*90)
    for period in [30, 60, 90]:
        bl = new_baseline[period]
        print(f"{period}天后     {200:>6d}    {bl['avg_peak']:>10.1f}%    {bl['median_peak']:>10.1f}%    "
              f"{bl['avg_end']:>13.1f}%    {bl['win_rate']:>8.1f}%")

    # 旧数据验证（如果存在）
    if old_prices is not None and old_correlation is not None:
        print("\n\n" + "📦"*45)
        old_results, old_baseline = run_full_verification(old_prices, old_correlation, "旧数据（可能使用forward fill）")

        # 打印旧数据的信号结果
        for signal_name, signal_data in old_results.items():
            if signal_data:
                print_signal_summary(signal_name, signal_data, old_baseline)

        # 打印旧数据基准
        print(f"\n\n{'='*90}")
        print("旧数据 - 随机基准")
        print(f"{'='*90}\n")
        print(f"{'期间':<10s} {'样本数':>8s} {'平均涨至峰':>12s} {'中位涨至峰':>12s} {'平均持有至末':>15s} {'胜率(>0)':>10s}")
        print("-"*90)
        for period in [30, 60, 90]:
            bl = old_baseline[period]
            print(f"{period}天后     {200:>6d}    {bl['avg_peak']:>10.1f}%    {bl['median_peak']:>10.1f}%    "
                  f"{bl['avg_end']:>13.1f}%    {bl['win_rate']:>8.1f}%")

        # 对比分析
        print("\n\n" + "⚖️ "*45)
        print("关键对比：新 vs 旧")
        print("⚖️ "*45 + "\n")

        # 对比最佳信号（从强正转弱正）
        signal_name = '从强正转弱正'
        if signal_name in new_results and signal_name in old_results:
            print(f"信号：{signal_name}\n")
            print(f"{'指标':<25s} {'新数据':>15s} {'旧数据':>15s} {'差异':>15s}")
            print("-"*75)

            for period in [60]:  # 重点看60天
                if period in new_results[signal_name] and period in old_results[signal_name]:
                    new_sd = new_results[signal_name][period]
                    old_sd = old_results[signal_name][period]

                    # 信号数量
                    diff_count = new_sd['count'] - old_sd['count']
                    print(f"信号触发次数              {new_sd['count']:>12d}次    {old_sd['count']:>12d}次    {diff_count:>+12d}次")

                    # 平均收益
                    diff_avg = new_sd['avg_end'] - old_sd['avg_end']
                    print(f"60天平均收益            {new_sd['avg_end']:>13.1f}%  {old_sd['avg_end']:>13.1f}%  {diff_avg:>+13.1f}%")

                    # 胜率
                    diff_wr = new_sd['win_rate'] - old_sd['win_rate']
                    print(f"胜率                    {new_sd['win_rate']:>13.1f}%  {old_sd['win_rate']:>13.1f}%  {diff_wr:>+13.1f}%")

                    # 超额收益
                    new_outperform = new_sd['avg_end'] - new_baseline[period]['avg_end']
                    old_outperform = old_sd['avg_end'] - old_baseline[period]['avg_end']
                    diff_outperform = new_outperform - old_outperform
                    print(f"超额收益(vs基准)        {new_outperform:>+13.1f}%  {old_outperform:>+13.1f}%  {diff_outperform:>+13.1f}%")

                    # 统计检验
                    if len(new_sd['all_gains']) >= 3 and len(old_sd['all_gains']) >= 3:
                        # 新数据 vs 基准
                        new_t, new_p = stats.ttest_ind(new_sd['all_gains'], new_baseline[period]['all_gains'])
                        old_t, old_p = stats.ttest_ind(old_sd['all_gains'], old_baseline[period]['all_gains'])

                        new_sig = "✅ 显著" if new_p < 0.05 else ("⚠️  边缘" if new_p < 0.1 else "❌ 不显著")
                        old_sig = "✅ 显著" if old_p < 0.05 else ("⚠️  边缘" if old_p < 0.1 else "❌ 不显著")

                        print(f"\np值(vs基准)               {new_p:>13.4f}    {old_p:>13.4f}")
                        print(f"统计显著性             {new_sig:>15s}  {old_sig:>15s}")
    else:
        print("\n⚠️  未找到旧数据，无法进行对比")

    # 最终结论
    print("\n\n" + "="*90)
    print("🎯 最终结论")
    print("="*90 + "\n")

    # 检查最佳信号
    best_signal_name = '从强正转弱正'
    if best_signal_name in new_results and 60 in new_results[best_signal_name]:
        new_sd = new_results[best_signal_name][60]
        new_outperform = new_sd['avg_end'] - new_baseline[60]['avg_end']

        print(f"使用新数据（正确方法）的验证结果：\n")
        print(f"  最佳信号: {best_signal_name}")
        print(f"  触发次数: {new_sd['count']}")
        print(f"  60天平均收益: {new_sd['avg_end']:.1f}%")
        print(f"  胜率: {new_sd['win_rate']:.1f}%")
        print(f"  超额收益: {new_outperform:+.1f}%")

        # t检验
        if len(new_sd['all_gains']) >= 3:
            new_t, new_p = stats.ttest_ind(new_sd['all_gains'], new_baseline[60]['all_gains'])
            print(f"  p值: {new_p:.4f}")

            if new_p < 0.05:
                print(f"\n  ✅ 结论：使用正确数据后，信号仍然具有统计显著性！")
            elif new_outperform > 15:
                print(f"\n  ⚠️  结论：虽然统计不显著(p={new_p:.3f})，但经济显著性明显（超额收益>{new_outperform:.1f}%）")
                print(f"     这可能是因为样本量较小({new_sd['count']}个信号)")
            else:
                print(f"\n  ❌ 结论：信号表现一般，建议谨慎使用")

        # 与旧数据对比结论
        if old_prices is not None and old_correlation is not None:
            if best_signal_name in old_results and 60 in old_results[best_signal_name]:
                old_sd = old_results[best_signal_name][60]

                print(f"\n与旧数据对比：")
                print(f"  信号数量变化: {new_sd['count']} vs {old_sd['count']} ({new_sd['count'] - old_sd['count']:+d})")
                print(f"  收益率变化: {new_sd['avg_end']:.1f}% vs {old_sd['avg_end']:.1f}% ({new_sd['avg_end'] - old_sd['avg_end']:+.1f}%)")

                if abs(new_sd['count'] - old_sd['count']) <= 2 and abs(new_sd['avg_end'] - old_sd['avg_end']) < 5:
                    print(f"\n  ✅ 新旧数据结果相似，说明原发现是真实的市场规律！")
                    print(f"     Gemini警告的forward fill问题虽然存在，但影响有限。")
                elif new_sd['avg_end'] > old_sd['avg_end']:
                    print(f"\n  📈 新数据显示信号更强！这说明去除forward fill后，真实信号被增强了。")
                else:
                    print(f"\n  📉 新数据显示信号变弱。需要进一步分析原因。")

    print("\n" + "="*90)

    # 保存结果
    results_summary = {
        'new_results': new_results,
        'new_baseline': new_baseline
    }

    if old_prices is not None:
        results_summary['old_results'] = old_results
        results_summary['old_baseline'] = old_baseline

    return results_summary


if __name__ == '__main__':
    results = compare_new_vs_old()
    print("\n✅ 验证完成！")
