"""
对比旧数据(forward fill)vs新数据(正确处理)的相关性差异
验证Gemini专家的警告：forward fill是否扭曲了相关性
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt

print("="*70)
print("🔬 新旧数据对比分析")
print("="*70 + "\n")

# 1. 加载新数据（正确处理）
print("1️⃣  加载新数据（不使用forward fill）...")
new_df = pd.read_parquet('improved_data_prices.parquet')
new_returns = pd.read_parquet('improved_data_returns.parquet')
new_corr_df = pd.read_parquet('improved_data_correlation.parquet')

print(f"   数据范围: {new_df.index[0].date()} - {new_df.index[-1].date()}")
print(f"   总天数: {len(new_df)}")
print(f"   有效配对: {new_df[['BTC', 'Gold']].notna().all(axis=1).sum()}")
print(f"   平均40天有效配对: {new_corr_df['valid_pairs'].mean():.1f}/40\n")

# 2. 模拟旧数据（使用forward fill - 错误方法）
print("2️⃣  模拟旧数据（使用forward fill - 错误方法）...")

# 从新数据开始，但使用forward fill
old_df = new_df.copy()
old_df_filled = old_df.ffill()  # 这是旧方法：前向填充

# 计算收益率和相关性
old_returns_filled = np.log(old_df_filled / old_df_filled.shift(1))
old_corr_filled = old_returns_filled['BTC'].rolling(40).corr(old_returns_filled['Gold'])

print(f"   填充后有效配对: {old_df_filled[['BTC', 'Gold']].notna().all(axis=1).sum()}")
print(f"   （所有天都被填充了！）\n")

# 3. 关键对比
print("3️⃣  关键差异对比\n")

# 3.1 周末数据
print("📅 周末数据处理：")
weekend = new_df[new_df.index.dayofweek >= 5]

print(f"\n新方法（正确）：")
print(f"   周末Gold NaN数: {weekend['Gold'].isna().sum()}/{len(weekend)}")
print(f"   周末BTC有效数: {weekend['BTC'].notna().sum()}/{len(weekend)}")

weekend_filled = old_df_filled[old_df_filled.index.dayofweek >= 5]
print(f"\n旧方法（forward fill）：")
print(f"   周末Gold NaN数: {weekend_filled['Gold'].isna().sum()}/{len(weekend_filled)}")
print(f"   周末BTC有效数: {weekend_filled['BTC'].notna().sum()}/{len(weekend_filled)}")
print(f"   ⚠️  所有周末Gold都被填充了！")

# 3.2 收益率对比
print(f"\n\n📊 收益率统计：")

# 选择最近1年的数据对比
recent_period = '2024-01-01'
recent_new = new_returns[new_returns.index >= recent_period]
recent_old = old_returns_filled[old_returns_filled.index >= recent_period]

print(f"\n新方法（过去1年）：")
print(f"   BTC收益率标准差: {recent_new['BTC'].std():.6f}")
print(f"   Gold收益率标准差: {recent_new['Gold'].std():.6f}")
print(f"   Gold收益率为0的天数: {(recent_new['Gold'] == 0).sum()}")

print(f"\n旧方法（forward fill）：")
print(f"   BTC收益率标准差: {recent_old['BTC'].std():.6f}")
print(f"   Gold收益率标准差: {recent_old['Gold'].std():.6f}")
print(f"   Gold收益率为0的天数: {(recent_old['Gold'] == 0).sum()}")
print(f"   ⚠️  周末Gold收益率被强制为0！")

# 3.3 相关性对比
print(f"\n\n🔗 相关性对比：")

# 选择重叠时期
overlap_start = max(new_corr_df.index[0], old_corr_filled.index[0])
overlap_end = min(new_corr_df.index[-1], old_corr_filled.index[-1])

new_corr_overlap = new_corr_df.loc[overlap_start:overlap_end, 'correlation']
old_corr_overlap = old_corr_filled.loc[overlap_start:overlap_end]

# 移除NaN
valid_comparison = pd.DataFrame({
    'new': new_corr_overlap,
    'old': old_corr_overlap
}).dropna()

print(f"\n可对比时期: {len(valid_comparison)} 个数据点")
print(f"\n新方法（正确）：")
print(f"   平均相关性: {valid_comparison['new'].mean():.4f}")
print(f"   标准差: {valid_comparison['new'].std():.4f}")
print(f"   范围: [{valid_comparison['new'].min():.4f}, {valid_comparison['new'].max():.4f}]")

print(f"\n旧方法（forward fill）：")
print(f"   平均相关性: {valid_comparison['old'].mean():.4f}")
print(f"   标准差: {valid_comparison['old'].std():.4f}")
print(f"   范围: [{valid_comparison['old'].min():.4f}, {valid_comparison['old'].max():.4f}]")

# 计算差异
corr_diff = valid_comparison['new'] - valid_comparison['old']
print(f"\n差异统计：")
print(f"   平均差异: {corr_diff.mean():.4f}")
print(f"   绝对差异: {corr_diff.abs().mean():.4f}")
print(f"   最大差异: {corr_diff.abs().max():.4f}")

# 4. Gemini警告验证
print(f"\n\n" + "="*70)
print("🎯 Gemini专家警告验证")
print("="*70)

print(f"\nGemini警告：")
print(f'"40天窗口中将包含大约8-10个周末数据点（约占25%）"')
print(f'"在这些数据点上，您是在计算(BTC的真实波动)与(黄金的0波动)之间的相关性"')
print(f'"这会人为地将相关系数拉向0"')

print(f"\n验证结果：")

# 检查相关性是否被拉向0
if valid_comparison['old'].abs().mean() < valid_comparison['new'].abs().mean():
    print(f"✅ 验证通过！旧方法的相关性绝对值更小")
    print(f"   旧方法平均|相关性|: {valid_comparison['old'].abs().mean():.4f}")
    print(f"   新方法平均|相关性|: {valid_comparison['new'].abs().mean():.4f}")
    print(f"   差异: {(valid_comparison['new'].abs().mean() - valid_comparison['old'].abs().mean()):.4f}")
    print(f"\n🚨 结论：Gemini的警告是正确的！forward fill确实扭曲了相关性！")
else:
    print(f"❌ 未验证：数据可能需要进一步检查")

# 5. 具体案例分析
print(f"\n\n" + "="*70)
print("📖 具体案例：2024年某周数据")
print("="*70)

# 选择2024年某一周（包含周末）
case_start = '2024-06-24'  # 周一
case_end = '2024-06-30'    # 周日

case_new = new_df.loc[case_start:case_end]
case_old = old_df_filled.loc[case_start:case_end]

print(f"\n日期范围: {case_start} - {case_end}")
print(f"\n新方法（正确）：")
print(case_new[['BTC', 'Gold']].to_string())

print(f"\n旧方法（forward fill）：")
print(case_old[['BTC', 'Gold']].to_string())

print(f"\n对比说明：")
print(f"- 新方法：周末Gold=NaN（正确，因为市场休市）")
print(f"- 旧方法：周末Gold=周五收盘价（错误，人为填充）")

# 6. 保存对比结果
comparison_df = pd.DataFrame({
    'new_correlation': valid_comparison['new'],
    'old_correlation_ffill': valid_comparison['old'],
    'difference': corr_diff
})

comparison_df.to_parquet('correlation_comparison.parquet')

print(f"\n\n✅ 对比分析完成，结果已保存到 correlation_comparison.parquet")
print("="*70)
