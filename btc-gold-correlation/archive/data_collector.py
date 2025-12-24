"""
数据收集模块 - 方案B（快速验证版）
核心改进：使用XAU/USD现货，周末数据保持NaN，基于对数收益率计算相关性

数据源：
- BTC: yfinance BTC-USD (Coinbase)
- 黄金: yfinance XAUUSD=X (现货黄金)
- 美元指数: yfinance DX-Y.NYB
- 标普500: yfinance ^GSPC
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class DataCollector:
    """数据收集器 - 遵循Gemini建议的统计严谨性原则"""

    def __init__(self, start_date='2015-01-01', data_dir='data'):
        self.start_date = start_date
        self.end_date = datetime.now().strftime('%Y-%m-%d')
        self.data_dir = Path(data_dir)
        self.raw_dir = self.data_dir / 'raw'
        self.processed_dir = self.data_dir / 'processed'

        # 创建目录
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        # 数据源配置
        self.tickers = {
            'BTC': 'BTC-USD',      # Coinbase BTC价格
            'GOLD': 'GC=F',        # COMEX黄金期货（yfinance不提供XAU/USD现货）
            'DXY': 'DX-Y.NYB',     # 美元指数
            'SPX': '^GSPC'         # 标普500
        }

        # 注意：理想情况应使用XAU/USD现货，但yfinance不支持
        # GC=F是次优选择，交易时间接近24/5，需注意合约展期问题

    def download_raw_data(self, force_refresh=False):
        """
        下载原始数据

        参数:
            force_refresh: 是否强制重新下载（否则只增量更新）
        """
        print(f"=== 开始下载数据 ({self.start_date} 至 {self.end_date}) ===\n")

        all_data = {}

        for name, ticker in self.tickers.items():
            try:
                cache_file = self.raw_dir / f'{name}_raw.csv'

                # 检查是否需要增量更新
                if not force_refresh and cache_file.exists():
                    existing = pd.read_csv(cache_file, index_col=0, parse_dates=True)
                    # 确保是单列数据（只取Close价格）
                    if isinstance(existing.columns, pd.MultiIndex):
                        existing = existing.iloc[:, 0]  # 取第一列
                    elif 'Close' in existing.columns:
                        existing = existing['Close']
                    else:
                        existing = existing.iloc[:, 0]

                    existing.name = name
                    last_date = pd.Timestamp(existing.index[-1])

                    # 如果最后日期是今天或昨天，无需更新
                    days_diff = (pd.Timestamp.now() - last_date).days
                    if days_diff <= 1:
                        print(f"✓ {name:4s} - 使用缓存数据（最新: {last_date.date()}）")
                        all_data[name] = existing
                        continue

                    # 增量下载
                    start = (last_date + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    print(f"⟳ {name:4s} - 增量更新（从 {start}）")
                    new_data = yf.download(ticker, start=start, end=self.end_date,
                                          progress=False, auto_adjust=True)

                    if not new_data.empty:
                        # 只取Close价格
                        if 'Close' in new_data.columns:
                            new_data = new_data['Close']
                        elif isinstance(new_data, pd.DataFrame):
                            new_data = new_data.iloc[:, 0]

                        combined = pd.concat([existing, new_data])
                        combined = combined[~combined.index.duplicated(keep='last')]
                        all_data[name] = combined
                    else:
                        all_data[name] = existing
                else:
                    # 全量下载
                    print(f"⬇ {name:4s} - 全量下载")
                    data = yf.download(ticker, start=self.start_date, end=self.end_date,
                                      progress=False, auto_adjust=True)

                    # 只取Close价格
                    if 'Close' in data.columns:
                        data = data['Close']
                    elif isinstance(data, pd.DataFrame) and not data.empty:
                        data = data.iloc[:, 0]

                    data.name = name
                    all_data[name] = data

                # 保存原始数据（只保存Close价格）
                if all_data[name] is not None and not all_data[name].empty:
                    all_data[name].to_csv(cache_file, header=True)
                    print(f"  └─ 保存到: {cache_file}")
                    print(f"  └─ 数据点数: {len(all_data[name])}")

            except Exception as e:
                print(f"✗ {name:4s} - 下载失败: {e}")
                all_data[name] = None

        print("\n=== 原始数据下载完成 ===\n")
        return all_data

    def align_and_process_data(self, raw_data):
        """
        数据对齐和预处理 - 遵循Gemini的统计严谨性原则

        关键改进：
        1. 不使用forward fill填充周末数据
        2. 周末黄金/股市数据保持NaN
        3. 计算对数收益率
        4. 相关性计算时自动忽略NaN配对
        """
        print("=== 开始数据对齐和预处理 ===\n")

        # 1. 提取收盘价
        prices = pd.DataFrame()
        for name, data in raw_data.items():
            if data is not None and not data.empty:
                # yfinance返回的数据可能是DataFrame或Series
                if isinstance(data, pd.DataFrame):
                    prices[name] = data['Close'] if 'Close' in data.columns else data.iloc[:, 0]
                else:
                    prices[name] = data

        print("原始价格数据:")
        print(prices.head())
        print(f"\n数据形状: {prices.shape}")
        print(f"\n缺失值统计:")
        print(prices.isnull().sum())

        # 2. 数据质量检查
        print("\n--- 数据质量检查 ---")
        self._check_data_quality(prices)

        # 3. 周末数据处理（关键！）
        print("\n--- 周末数据处理策略 ---")
        print("✓ BTC: 保留周末数据（24/7交易）")
        print("✓ GOLD/DXY/SPX: 周末为NaN（正常现象）")
        print("✓ 相关性计算时将自动忽略NaN配对")
        print("✓ 不使用forward fill（避免伪相关性）")

        # 统计周末数据点
        if len(prices) > 0 and hasattr(prices.index, 'dayofweek'):
            weekend_mask = prices.index.dayofweek.isin([5, 6])
            weekend_stats = {
                'BTC周末数据点': (~prices.loc[weekend_mask, 'BTC'].isnull()).sum() if 'BTC' in prices.columns else 0,
                'GOLD周末数据点': (~prices.loc[weekend_mask, 'GOLD'].isnull()).sum() if 'GOLD' in prices.columns else 0,
            }
            print(f"\n周末数据统计: {weekend_stats}")

        # 4. 计算对数收益率（统计上更合适）
        print("\n--- 计算对数收益率 ---")
        returns = np.log(prices / prices.shift(1))
        returns = returns.replace([np.inf, -np.inf], np.nan)  # 处理无穷值

        print(f"收益率数据形状: {returns.shape}")
        print(f"收益率缺失值统计:")
        print(returns.isnull().sum())

        # 5. 基础统计信息
        print("\n--- 收益率基础统计 ---")
        print(returns.describe())

        # 6. 保存处理后的数据
        prices_file = self.processed_dir / 'aligned_prices.parquet'
        returns_file = self.processed_dir / 'log_returns.parquet'

        prices.to_parquet(prices_file)
        returns.to_parquet(returns_file)

        print(f"\n✓ 价格数据已保存: {prices_file}")
        print(f"✓ 收益率数据已保存: {returns_file}")

        print("\n=== 数据预处理完成 ===\n")

        return prices, returns

    def _check_data_quality(self, prices):
        """数据质量检查"""
        issues = []

        for col in prices.columns:
            data = prices[col].dropna()

            # 检查零值
            zero_count = (data == 0).sum()
            if zero_count > 0:
                issues.append(f"  ⚠ {col}: 发现 {zero_count} 个零值")

            # 检查异常波动（日收益率超过30%）
            returns = data.pct_change()
            extreme = returns[abs(returns) > 0.3]
            if len(extreme) > 0:
                issues.append(f"  ⚠ {col}: 发现 {len(extreme)} 个极端波动日 (>30%)")
                for date, ret in extreme.items():
                    issues.append(f"    └─ {date.date()}: {ret:.2%}")

            # 检查数据连续性（连续5天以上缺失）
            null_mask = prices[col].isnull()
            consecutive_nulls = null_mask.astype(int).groupby(
                (null_mask != null_mask.shift()).cumsum()
            ).sum()
            max_consecutive = consecutive_nulls.max()
            if max_consecutive > 5:
                issues.append(f"  ⚠ {col}: 最长连续缺失 {max_consecutive} 天")

        if issues:
            print("⚠ 发现数据质量问题:")
            for issue in issues:
                print(issue)
        else:
            print("✓ 数据质量检查通过")

    def calculate_correlation(self, returns, window=40):
        """
        计算BTC与黄金的滚动相关系数

        参数:
            returns: 对数收益率DataFrame
            window: 滚动窗口大小（默认40天）

        重要：只在两者都有数据的交易日上计算相关性（遵循Gemini建议）
        """
        print(f"=== 计算 {window} 天滚动相关系数 ===\n")

        if 'BTC' not in returns.columns or 'GOLD' not in returns.columns:
            print("✗ 缺少BTC或GOLD数据，无法计算相关性")
            return None

        # 关键：只保留两者都有数据的交易日
        valid_mask = (~returns['BTC'].isnull()) & (~returns['GOLD'].isnull())
        valid_returns = returns[valid_mask][['BTC', 'GOLD']].copy()

        print(f"总数据点: {len(returns)}")
        print(f"有效交易日（BTC和GOLD都有数据）: {len(valid_returns)}")
        print(f"数据范围: {valid_returns.index[0].date()} 至 {valid_returns.index[-1].date()}")

        # 方法：计算滚动窗口内两个序列的相关系数
        # min_periods设为window的80%，确保有足够数据点
        min_periods = int(window * 0.8)

        # 在有效数据上计算滚动相关性
        correlation = valid_returns['BTC'].rolling(
            window=window,
            min_periods=min_periods
        ).corr(valid_returns['GOLD'])

        # 将相关性结果重新索引回原始日期（保留NaN）
        full_correlation = pd.Series(index=returns.index, dtype=float)
        full_correlation.loc[correlation.index] = correlation

        valid_corr = correlation.dropna()

        if len(valid_corr) == 0:
            print("\n✗ 无有效相关性数据")
            return None

        print(f"\n相关性统计 (共 {len(valid_corr)} 个有效数据点):")
        print(valid_corr.describe())
        print(f"\n负相关出现次数: {(valid_corr < 0).sum()}")
        print(f"负相关占比: {(valid_corr < 0).sum() / len(valid_corr):.2%}")
        print(f"强负相关(<-0.2)次数: {(valid_corr < -0.2).sum()}")

        # 极端相关性
        print(f"\n极端相关性:")
        print(f"  最强正相关: {valid_corr.max():.4f} ({valid_corr.idxmax().date()})")
        print(f"  最强负相关: {valid_corr.min():.4f} ({valid_corr.idxmin().date()})")

        # 保存相关性数据（包含所有日期，非交易日为NaN）
        corr_file = self.processed_dir / f'btc_gold_correlation_{window}d.parquet'
        full_correlation.to_frame('correlation').to_parquet(corr_file)
        print(f"\n✓ 相关性数据已保存: {corr_file}")

        return full_correlation

    def run_full_pipeline(self, force_refresh=False):
        """运行完整的数据收集和处理流程"""
        print("╔" + "═" * 60 + "╗")
        print("║" + " " * 15 + "BTC-黄金相关性数据收集系统" + " " * 15 + "║")
        print("╚" + "═" * 60 + "╝\n")

        # 1. 下载原始数据
        raw_data = self.download_raw_data(force_refresh=force_refresh)

        # 2. 数据对齐和预处理
        prices, returns = self.align_and_process_data(raw_data)

        # 3. 计算相关性
        correlation = self.calculate_correlation(returns, window=40)

        print("\n" + "="*60)
        print("数据收集完成！现在可以进行相关性分析和策略回测。")
        print("="*60)

        return {
            'prices': prices,
            'returns': returns,
            'correlation': correlation
        }


def main():
    """主函数"""
    collector = DataCollector(start_date='2015-01-01')

    # 运行完整流程
    results = collector.run_full_pipeline(force_refresh=False)

    # 快速可视化相关性
    if results['correlation'] is not None:
        print("\n最近10个交易日的相关性:")
        print(results['correlation'].tail(10))


if __name__ == '__main__':
    main()
