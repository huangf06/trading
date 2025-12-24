# BTC-黄金相关性研究 - 后续验证计划

**文档日期**: 2025-10-30
**基于**: correlation_signal_findings.md + gemini_feedback.md

---

## 执行摘要

当前研究发现了有价值的信号（从强正相关转弱），但存在**两个致命缺陷**：
1. ⚠️ **数据源问题**：使用yfinance + forward fill导致相关性计算被系统性扭曲
2. ⚠️ **样本量过小**：仅5个信号，统计显著性不足(p=0.459)

**优先级**: 必须先解决数据源问题，再扩大样本量验证

---

## 第一阶段：数据源升级（🔴 最高优先级）

### 问题诊断

#### 当前方案的致命缺陷

```
问题链：
yfinance GC=F (黄金期货)
  ↓
周末/节假日无数据
  ↓
使用forward fill填充
  ↓
黄金周末收益率 = 0
  ↓
BTC周末有真实波动 vs 黄金0波动
  ↓
40天窗口中25%数据是伪造的（8-10个周末）
  ↓
相关性被系统性拉向0
  ↓
观察到的"相关性转弱"可能是数据伪影！
```

#### Gemini专家评审结论

> "这个缺陷将严重污染您的相关性计算，可能导致整个研究的结论无效。"

### 解决方案：更换数据源

| 资产 | ❌ 当前源 | ✅ 推荐源 | 数据接口 | 理由 |
|-----|---------|----------|---------|------|
| **BTC** | yfinance BTC-USD | **Binance/Coinbase** | CCXT库 | 交易所一手数据，24/7交易 |
| **黄金** | yfinance GC=F | **XAU/USD现货** | Alpha Vantage API | 24/5交易，与BTC时段匹配 |
| **DXY** | yfinance DX-Y.NYB | **FRED DTWEXBGS** | pandas-datareader | 官方权威数据 |
| **SPX** | yfinance ^GSPC | **FRED SP500** | pandas-datareader | 官方权威数据 |

### 实施步骤

#### Step 1: 安装依赖

```bash
pip install ccxt alpha-vantage pandas-datareader
```

#### Step 2: 数据收集脚本（改进版）

```python
import ccxt
import pandas as pd
from alpha_vantage.foreignexchange import ForeignExchange
from pandas_datareader import data as pdr
import numpy as np

# 1. BTC数据（使用CCXT）
def fetch_btc_data(start_date='2015-01-01'):
    """从Binance获取BTC/USDT日线数据"""
    exchange = ccxt.binance()
    since = exchange.parse8601(f'{start_date}T00:00:00Z')

    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('date', inplace=True)

    return df['close'].rename('BTC')

# 2. 黄金数据（使用Alpha Vantage）
def fetch_gold_data(api_key, start_date='2015-01-01'):
    """获取XAU/USD现货日线数据"""
    fx = ForeignExchange(key=api_key, output_format='pandas')
    data, meta = fx.get_currency_exchange_daily(
        from_symbol='XAU',
        to_symbol='USD',
        outputsize='full'
    )

    data.index = pd.to_datetime(data.index)
    data = data.sort_index()
    data = data[data.index >= start_date]

    return data['4. close'].rename('Gold').astype(float)

# 3. DXY数据（使用FRED）
def fetch_dxy_data(start_date='2015-01-01'):
    """从FRED获取美元指数"""
    dxy = pdr.DataReader('DTWEXBGS', 'fred', start_date)
    return dxy['DTWEXBGS'].rename('DXY')

# 4. SPX数据（使用FRED）
def fetch_spx_data(start_date='2015-01-01'):
    """从FRED获取S&P500"""
    spx = pdr.DataReader('SP500', 'fred', start_date)
    return spx['SP500'].rename('SPX')

# 5. 数据对齐（关键！）
def align_data_correctly():
    """
    正确的数据对齐方案：
    - 不使用forward fill
    - 保留NaN，让pandas.corr()自动处理
    """
    # 获取所有数据
    btc = fetch_btc_data()
    gold = fetch_gold_data(api_key='YOUR_ALPHA_VANTAGE_KEY')
    dxy = fetch_dxy_data()
    spx = fetch_spx_data()

    # 外连接合并（保留所有日期，包括周末）
    df = pd.DataFrame({
        'BTC': btc,
        'Gold': gold,
        'DXY': dxy,
        'SPX': spx
    })

    # 计算对数收益率（不填充NaN！）
    returns = np.log(df / df.shift(1))

    # 验证：周末的黄金/DXY/SPX应该是NaN
    print("周末数据检查（应该看到NaN）:")
    print(returns[returns.index.dayofweek >= 5].head())

    return returns

# 6. 计算相关性（pandas自动忽略NaN）
def calculate_correlation(returns, window=40):
    """
    pandas的rolling.corr()会自动忽略配对中的NaN
    这意味着只在两者都交易的日子计算相关性
    """
    correlation = returns['BTC'].rolling(window).corr(returns['Gold'])

    # 检查有效窗口大小
    valid_pairs = returns[['BTC', 'Gold']].notna().all(axis=1).rolling(window).sum()
    print(f"平均有效配对数：{valid_pairs.mean():.1f}/{window}")

    return correlation
```

#### Step 3: 数据质量验证

```python
# 关键验证点
def validate_data_quality(returns):
    """数据质量检查清单"""

    # 1. 检查平稳性（ADF检验）
    from statsmodels.tsa.stattools import adfuller

    for col in returns.columns:
        result = adfuller(returns[col].dropna())
        print(f"{col} ADF p-value: {result[1]:.4f} ({'平稳' if result[1] < 0.05 else '非平稳'})")

    # 2. 检查周末数据处理
    weekend_btc = returns[returns.index.dayofweek >= 5]['BTC'].dropna()
    weekend_gold = returns[returns.index.dayofweek >= 5]['Gold'].dropna()

    print(f"\n周末数据点：")
    print(f"  BTC: {len(weekend_btc)} 个有效点（正常，24/7交易）")
    print(f"  Gold: {len(weekend_gold)} 个有效点（应接近0）")

    # 3. 交叉验证（与旧数据对比）
    # TODO: 计算新旧相关性的差异

    return True
```

#### Step 4: 重新运行完整分析

```python
# 使用新数据重新验证所有发现
def rerun_full_analysis():
    """
    重新运行verify_leading_signal.py的所有逻辑
    对比结果：
    - 信号触发次数是否变化？
    - 平均收益率是否变化？
    - p值是否改善？
    """
    pass  # 详见第二阶段
```

### 预期结果

#### 如果新数据验证成功
- ✅ 信号逻辑仍然有效
- ✅ 收益率可能更高/更稳定（噪音减少）
- ✅ p值可能改善（真实信号增强）
- → **继续第二阶段**

#### 如果新数据推翻结论
- ❌ 原有发现是数据伪影
- ❌ 需要重新寻找其他模式
- → **回到探索阶段**

---

## 第二阶段：扩大样本量（统计显著性提升）

### 当前问题
- 仅5个信号，p=0.459 (需要<0.05)
- 统计功效不足，无法排除偶然性

### 解决方案

#### 策略1: 时间维度扩展

```python
# 1. 扩展历史数据到更早期
# 当前：2015-2025 (10年)
# 目标：2013-2025 (12年，覆盖2013-2014早期牛市)

# 难点：早期BTC数据质量差，需要多交易所交叉验证
exchanges = ['binance', 'coinbase', 'kraken', 'bitstamp']
# 取中位数价格，剔除异常值
```

#### 策略2: 参数维度扩展

```python
# 测试多个窗口期，寻找稳健信号
test_windows = [30, 35, 40, 45, 50, 60]

# 使用Bonferroni校正控制多重比较
alpha_corrected = 0.05 / len(test_windows)

# 如果多个窗口都显示显著性，说明信号稳健
```

#### 策略3: 资产维度扩展

```python
# 将同样的逻辑应用到其他加密资产
test_assets = [
    'BTC',  # 原有
    'ETH',  # 以太坊（市值第二）
    'BNB',  # 币安币
    'SOL',  # Solana
]

# 如果多个资产都有效，说明这是加密市场的通用规律
# Meta-analysis：合并多个资产的结果提升统计功效
```

#### 策略4: 放宽信号定义（增加样本）

```python
# 当前最佳信号：从>0.3降至<0.15 (5次)
# 测试：
signal_variants = [
    {'from': 0.25, 'to': 0.15},  # 稍微放宽
    {'from': 0.30, 'to': 0.20},  # 稍微放宽
    {'drop': 0.25},              # 相关性下降>0.25
]

# 权衡：样本量 vs 信号质量
# 目标：找到"样本量足够大 & 收益率仍然可观"的平衡点
```

---

## 第三阶段：稳健性测试

### 研究计划中建议的测试（research_plan.md第四、五节）

#### 1. Bootstrap重采样

```python
from scipy.stats import bootstrap

def bootstrap_test(signal_returns, random_returns, n_iterations=10000):
    """
    Bootstrap检验超额收益的显著性
    """
    def mean_diff(signal, random):
        return np.mean(signal) - np.mean(random)

    result = bootstrap(
        (signal_returns, random_returns),
        mean_diff,
        n_resamples=n_iterations,
        method='percentile'
    )

    return result.confidence_interval
```

#### 2. Walk-forward分析

```python
# 避免过拟合：滚动训练-测试分割
def walk_forward_analysis(data, train_years=5, test_years=1):
    """
    - 前5年训练（寻找最佳参数）
    - 后1年测试（验证样本外表现）
    - 滚动向前
    """
    results = []

    for start_year in range(2015, 2024):
        train_data = data[start_year:start_year+train_years]
        test_data = data[start_year+train_years:start_year+train_years+test_years]

        # 在训练集找最佳阈值
        best_params = optimize_on_train(train_data)

        # 在测试集评估
        test_performance = evaluate_on_test(test_data, best_params)
        results.append(test_performance)

    return results
```

#### 3. Granger因果检验

```python
from statsmodels.tsa.stattools import grangercausalitytests

# 验证相关性变化是否"领先"于BTC价格变化
def test_causality(correlation, btc_returns, max_lag=30):
    """
    H0: 相关性变化不能预测BTC收益
    H1: 相关性变化能预测BTC收益（领先指标）
    """
    data = pd.DataFrame({
        'corr_change': correlation.diff(),
        'btc_return': btc_returns
    }).dropna()

    results = grangercausalitytests(data[['btc_return', 'corr_change']], max_lag)

    return results
```

#### 4. 压力测试

```python
# 测试极端市场环境下的表现
stress_scenarios = {
    '2020-03 COVID暴跌': ('2020-03-01', '2020-03-31'),
    '2022 熊市': ('2022-01-01', '2022-12-31'),
    '2021 牛市': ('2021-01-01', '2021-12-31'),
}

for name, (start, end) in stress_scenarios.items():
    subset_performance = evaluate_strategy(data[start:end])
    print(f"{name}: {subset_performance}")
```

---

## 第四阶段：机制探究（回答"为什么"）

### Gemini提到的关键问题（research_plan.md第五节）

#### 问题1: 为什么负相关（或弱相关）会导致BTC上涨？

**需要验证的假说**：

1. **避险资金轮动假说**
   ```python
   # 检验逻辑：
   # - 黄金先涨（避险情绪）
   # - 相关性减弱时，资金从黄金转向BTC
   # - 测试：检查黄金涨幅与后续BTC涨幅的关系

   def test_rotation_hypothesis(data):
       """在信号触发前，黄金是否经历过上涨？"""
       for signal_date in signal_dates:
           gold_return_60d_before = data.loc[signal_date-60:signal_date, 'Gold'].pct_change().sum()
           btc_return_60d_after = data.loc[signal_date:signal_date+60, 'BTC'].pct_change().sum()

           print(f"黄金前60天: {gold_return_60d_before:.1%}, BTC后60天: {btc_return_60d_after:.1%}")
   ```

2. **流动性驱动假说**
   ```python
   # 加入联储资产负债表数据
   # 检验：流动性扩张 → 黄金涨 → 相关性减弱 → BTC独立上涨

   def test_liquidity_hypothesis(data):
       """相关性减弱是否与流动性环境相关？"""
       # 数据源：FRED 'WALCL' (美联储总资产)
       fed_balance = fetch_fed_balance_sheet()
       # 分析逻辑...
   ```

3. **市场情绪转换假说**
   ```python
   # 黄金代表"恐惧"，BTC代表"贪婪"
   # 相关性减弱 = 市场情绪从恐惧转向贪婪

   # 可能的辅助数据：
   # - Crypto Fear & Greed Index
   # - VIX（波动率指数）
   # - Put/Call Ratio
   ```

#### 问题2: 是否存在领先-滞后关系？

```python
# 使用Cross-correlation分析
def cross_correlation_analysis(gold_returns, btc_returns, max_lag=60):
    """
    计算不同时间滞后下的相关性
    lag=0:  同期相关性
    lag>0:  黄金领先BTC
    lag<0:  BTC领先黄金
    """
    correlations = []

    for lag in range(-max_lag, max_lag+1):
        if lag >= 0:
            corr = gold_returns[:-lag or None].corr(btc_returns[lag:])
        else:
            corr = gold_returns[-lag:].corr(btc_returns[:lag or None])

        correlations.append({'lag': lag, 'correlation': corr})

    # 绘制Cross-correlation图
    # 如果在lag=正数时出现峰值，说明黄金领先BTC

    return pd.DataFrame(correlations)
```

---

## 第五阶段：对比其他相关性指标

### 测试其他"黄金"的定义

```python
# 当前：XAU/USD (现货黄金)
# 对比：
alternatives = {
    'GLD': 'SPDR黄金ETF',
    'GLDM': 'iShares黄金ETF（费用更低）',
    'IAU': 'iShares黄金信托',
    'GDX': '黄金矿业股ETF（更高波动）',
    'PAXG': '链上黄金代币（去中心化）',
}

# 问题：哪个"黄金"与BTC的相关性最具预测性？
# 假设：如果PAXG（加密黄金）效果更好，说明这是加密市场内部的资金轮动
```

### 测试其他资产的相关性

```python
# 不仅仅是黄金，测试与其他资产的相关性变化
test_correlations = {
    'Gold': '避险资产',
    'SPX': '风险资产',
    'DXY': '美元强弱',
    'US10Y': '利率',
    'Oil': '大宗商品',
}

# 问题：哪个相关性变化最具预测性？
# 可能发现：BTC与SPX的相关性变化更重要（风险偏好指标）
```

---

## 实施时间表

### 第1周：数据源升级（必须完成）
- [ ] Day 1-2: 搭建新数据收集脚本（CCXT + Alpha Vantage + FRED）
- [ ] Day 3-4: 数据质量验证（ADF检验、周末数据检查、交叉验证）
- [ ] Day 5-7: 重新运行完整分析，对比新旧结果

### 第2周：扩大样本量（如果第1周验证成功）
- [ ] Day 8-9: 扩展历史数据到2013年
- [ ] Day 10-11: 多窗口期测试（30-60天）
- [ ] Day 12-14: 应用到ETH/BNB/SOL，Meta-analysis

### 第3周：稳健性测试
- [ ] Day 15-16: Bootstrap重采样 + Walk-forward分析
- [ ] Day 17-18: Granger因果检验 + 交叉相关分析
- [ ] Day 19-21: 压力测试（2020暴跌、2022熊市）

### 第4周：机制探究与报告
- [ ] Day 22-24: 资金轮动假说验证（黄金涨幅 vs BTC后续表现）
- [ ] Day 25-26: 流动性驱动假说（联储数据）
- [ ] Day 27-28: 撰写最终研究报告

---

## 决策树

```
数据源升级完成
    │
    ├─── 新数据推翻原结论？
    │     └─── YES → 停止项目或重新探索
    │
    └─── NO → 原结论依然成立
          │
          ├─── 样本量扩展（多窗口/多资产）
          │     │
          │     ├─── p值<0.05？
          │     │     └─── YES → 统计显著！继续稳健性测试
          │     │
          │     └─── NO → 样本量仍不足
          │            └─── 决策：接受"经济显著但统计不显著"？
          │                 ├─── YES → 小仓位实盘验证
          │                 └─── NO → 停止项目
          │
          └─── 稳健性测试全部通过？
                ├─── YES → 进入实盘测试阶段
                └─── NO → 识别失效场景，调整策略
```

---

## 关键风险提示

### 风险1: 数据升级后发现原结论无效
**概率**: 30-40%（Gemini专家认为这是"可能"的）
**后果**: 需要回到探索阶段，寻找其他模式
**缓解**: 尽早完成数据升级，避免后续无效工作

### 风险2: 样本量不足，永远无法达到统计显著性
**概率**: 50%
**后果**: 只能作为"辅助信号"，不能单独使用
**缓解**:
- 扩展到多个加密资产（ETH, BNB, SOL）
- 接受"经济显著性"作为标准（实盘小仓位验证）

### 风险3: 信号在未来失效（市场演化）
**概率**: 未知（所有量化策略的通病）
**后果**: 实盘亏损
**缓解**:
- 持续监控信号有效性
- 设置严格止损
- 结合其他指标（不单独使用）

---

## 成功标准

### 最低标准（可以进入小仓位实盘）
- ✅ 使用正确数据源（XAU/USD + CCXT BTC）
- ✅ 新数据验证信号仍有效
- ✅ 样本量>10个信号
- ✅ 胜率>70%
- ✅ 超额收益>15%
- ✅ Walk-forward测试通过

### 理想标准（可以作为主要策略）
- ✅ 上述所有条件
- ✅ p值<0.05（统计显著）
- ✅ Sharpe比率>1.0
- ✅ 多资产验证通过（BTC + ETH + 其他）
- ✅ 机制解释清晰（因果关系明确）
- ✅ 压力测试通过（2020暴跌、2022熊市）

---

## 参考文献与工具

### 数据源
- [CCXT文档](https://docs.ccxt.com/)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)
- [FRED API](https://fred.stlouisfed.org/docs/api/fred/)

### 统计方法
- Bootstrap: `scipy.stats.bootstrap`
- ADF检验: `statsmodels.tsa.stattools.adfuller`
- Granger因果: `statsmodels.tsa.stattools.grangercausalitytests`

### 回测框架
- Backtrader: Python回测框架
- Zipline: Quantopian开源框架
- VectorBT: 高性能向量化回测

---

**最后更新**: 2025-10-30
**下次审查**: 完成数据源升级后（预计1周内）

**行动呼吁**:
1. 立即开始数据源升级（注册Alpha Vantage API密钥）
2. 暂停其他分析，直到数据源问题解决
3. 1周后重新评估项目可行性
