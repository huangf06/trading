"""
改进的数据收集脚本 - 使用更可靠的数据源
基于Gemini专家反馈，解决原方案的致命缺陷

数据源升级：
- BTC: Binance交易所原始数据（CCXT库）
- 黄金: XAU/USD现货（Alpha Vantage API）
- DXY: FRED官方数据
- SPX: FRED官方数据

关键改进：
1. 不使用forward fill填充周末数据
2. 保留NaN，让pandas.corr()自动处理
3. 只在两者都交易的日子计算相关性
"""

import ccxt
import pandas as pd
import numpy as np
from alpha_vantage.foreignexchange import ForeignExchange
from pandas_datareader import data as pdr
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Alpha Vantage API密钥
ALPHA_VANTAGE_KEY = '11A6UEZO56SX8FC9'


def fetch_btc_data(start_date='2015-01-01', end_date=None):
    """
    从Binance获取BTC/USDT日线数据

    优点：
    - 交易所一手数据，质量高
    - 24/7交易，真实反映市场
    - UTC 00:00对齐
    """
    print("📈 正在从Binance获取BTC数据...")

    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })

        # 将日期转换为毫秒时间戳
        since = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)

        # 获取所有历史数据
        all_ohlcv = []
        limit = 1000  # Binance一次最多返回1000条

        while True:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since, limit=limit)

            if not ohlcv:
                break

            all_ohlcv.extend(ohlcv)

            # 更新since为最后一条数据的时间戳+1天
            since = ohlcv[-1][0] + 86400000

            # 如果指定了结束日期
            if end_date:
                end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
                if since >= end_timestamp:
                    break

            # 如果获取的数据少于limit，说明已经到最新数据
            if len(ohlcv) < limit:
                break

            time.sleep(exchange.rateLimit / 1000)  # 遵守速率限制

            # 进度提示
            last_date = datetime.fromtimestamp(ohlcv[-1][0] / 1000).strftime('%Y-%m-%d')
            print(f"  已获取到: {last_date}", end='\r')

        # 转换为DataFrame
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('date', inplace=True)

        print(f"\n✅ BTC数据获取完成: {len(df)} 条记录 ({df.index[0].date()} 至 {df.index[-1].date()})")

        return df[['close']].rename(columns={'close': 'BTC'})

    except Exception as e:
        print(f"❌ BTC数据获取失败: {e}")
        print("⚠️  回退到yfinance备用方案...")

        # 备用方案：使用yfinance
        import yfinance as yf
        btc = yf.download('BTC-USD', start=start_date, end=end_date, progress=False)
        return btc[['Close']].rename(columns={'Close': 'BTC'})


def fetch_gold_data_alphavantage(api_key, start_date='2015-01-01'):
    """
    从Alpha Vantage获取XAU/USD现货日线数据

    优点：
    - 真实的现货黄金价格（而非ETF或期货）
    - 24/5交易，与BTC时段最接近
    - 免费API，质量可靠
    """
    print("🥇 正在从Alpha Vantage获取黄金数据...")

    try:
        # 使用直接的requests调用，因为alpha_vantage库可能有问题
        import requests

        url = f'https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=XAU&to_symbol=USD&outputsize=full&apikey={api_key}'

        response = requests.get(url)
        data = response.json()

        # 检查错误
        if 'Error Message' in data:
            raise Exception(data['Error Message'])
        if 'Note' in data:
            raise Exception(data['Note'])
        if 'Time Series FX (Daily)' not in data:
            raise Exception(f"Unexpected response: {list(data.keys())}")

        # 解析数据
        time_series = data['Time Series FX (Daily)']

        # 转换为DataFrame
        df_data = []
        for date_str, values in time_series.items():
            df_data.append({
                'date': pd.to_datetime(date_str),
                'close': float(values['4. close'])
            })

        df = pd.DataFrame(df_data)
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        df = df[df.index >= start_date]

        gold = df['close'].rename('Gold')

        print(f"✅ 黄金数据获取完成: {len(gold)} 条记录 ({gold.index[0].date()} 至 {gold.index[-1].date()})")

        return pd.DataFrame(gold)

    except Exception as e:
        print(f"❌ Alpha Vantage获取失败: {e}")
        print("⚠️  尝试备用方案...")
        return None


def fetch_gold_data_yfinance_backup(start_date='2015-01-01', end_date=None):
    """
    备用方案：从yfinance获取GLD ETF数据
    注意：这不是最佳方案，但作为备份
    """
    print("🥇 使用备用方案: yfinance GLD ETF...")

    import yfinance as yf
    gold = yf.download('GLD', start=start_date, end=end_date, progress=False)

    if not gold.empty:
        print(f"✅ GLD数据获取完成: {len(gold)} 条记录")

        # 处理可能的多级列索引
        if isinstance(gold.columns, pd.MultiIndex):
            gold.columns = gold.columns.droplevel(1)

        # 确保索引是DatetimeIndex
        if not isinstance(gold.index, pd.DatetimeIndex):
            gold.index = pd.to_datetime(gold.index)

        # 检查列名
        if 'Close' in gold.columns:
            return gold[['Close']].rename(columns={'Close': 'Gold'})
        else:
            # 使用第一列（通常是收盘价）
            return pd.DataFrame({' Gold': gold.iloc[:, 3]})  # 第4列通常是Close
    else:
        print("❌ GLD数据获取失败")
        return None


def fetch_dxy_data(start_date='2015-01-01', end_date=None):
    """
    从FRED获取美元指数

    优点：
    - 官方权威数据
    - 免费、稳定
    - 质量极高
    """
    print("💵 正在从FRED获取美元指数...")

    try:
        dxy = pdr.DataReader('DTWEXBGS', 'fred', start_date, end_date)

        print(f"✅ DXY数据获取完成: {len(dxy)} 条记录")

        return dxy.rename(columns={'DTWEXBGS': 'DXY'})

    except Exception as e:
        print(f"❌ DXY数据获取失败: {e}")
        return None


def fetch_spx_data(start_date='2015-01-01', end_date=None):
    """
    从FRED获取S&P 500指数
    """
    print("📊 正在从FRED获取S&P 500...")

    try:
        spx = pdr.DataReader('SP500', 'fred', start_date, end_date)

        print(f"✅ SPX数据获取完成: {len(spx)} 条记录")

        return spx.rename(columns={'SP500': 'SPX'})

    except Exception as e:
        print(f"❌ SPX数据获取失败: {e}")
        return None


def align_data_correctly(btc, gold, dxy=None, spx=None):
    """
    正确的数据对齐方案

    关键改进：
    1. 不使用forward fill
    2. 保留NaN
    3. pandas.corr()会自动忽略NaN配对

    这样计算相关性时，只在两者都交易的日子进行计算
    """
    print("\n🔄 正在对齐数据...")

    # 外连接合并（保留所有日期）
    # 修复：确保所有Series都是1维的
    df = btc.copy()

    if gold is not None:
        if isinstance(gold, pd.DataFrame):
            df = df.join(gold, how='outer')
        else:
            df['Gold'] = gold

    if dxy is not None:
        if isinstance(dxy, pd.DataFrame):
            df = df.join(dxy, how='outer')
        else:
            df['DXY'] = dxy

    if spx is not None:
        if isinstance(spx, pd.DataFrame):
            df = df.join(spx, how='outer')
        else:
            df['SPX'] = spx

    # 统计信息
    print(f"\n📅 数据范围: {df.index[0].date()} 至 {df.index[-1].date()}")
    print(f"📊 总天数: {len(df)}")
    print(f"\n各资产数据点数量:")
    for col in df.columns:
        valid_count = df[col].notna().sum()
        coverage = valid_count / len(df) * 100
        print(f"  {col}: {valid_count} ({coverage:.1f}%)")

    # 检查周末数据（关键验证）
    weekend_data = df[df.index.dayofweek >= 5]

    print(f"\n🔍 周末数据检查 (共{len(weekend_data)}个周末日):")
    for col in df.columns:
        weekend_count = weekend_data[col].notna().sum()
        print(f"  {col}: {weekend_count} 个有效点", end='')

        if col == 'BTC':
            print(" (正常，BTC 24/7交易)")
        elif weekend_count > len(weekend_data) * 0.1:
            print(" ⚠️  异常！周末不应该有这么多数据")
        else:
            print(" ✅ (正常，周末休市)")

    return df


def calculate_returns(df):
    """
    计算对数收益率

    注意：不填充NaN！
    """
    print("\n📈 计算收益率...")

    returns = np.log(df / df.shift(1))

    # 统计
    print(f"\n收益率统计:")
    for col in returns.columns:
        valid = returns[col].dropna()
        print(f"  {col}: {len(valid)} 个有效收益率点")

    return returns


def calculate_correlation(returns, window=40):
    """
    计算滚动相关性

    pandas的rolling.corr()会自动忽略配对中的NaN
    """
    print(f"\n🔗 计算{window}天滚动相关性...")

    if 'Gold' not in returns.columns:
        print("❌ 缺少黄金数据，无法计算相关性")
        return None

    correlation = returns['BTC'].rolling(window).corr(returns['Gold'])

    # 计算有效窗口大小
    both_valid = returns[['BTC', 'Gold']].notna().all(axis=1)
    valid_pairs = both_valid.rolling(window).sum()

    avg_valid = valid_pairs.mean()
    min_valid = valid_pairs.min()

    print(f"✅ 相关性计算完成")
    print(f"  平均有效配对数: {avg_valid:.1f}/{window} ({avg_valid/window*100:.1f}%)")
    print(f"  最小有效配对数: {min_valid:.0f}/{window}")

    # 警告：如果有效配对数太少
    if avg_valid < window * 0.8:
        print(f"⚠️  警告：平均有效配对数低于80%，相关性可能不够稳健")

    return correlation, valid_pairs


def validate_data_quality(df, returns):
    """
    数据质量验证
    """
    print("\n" + "="*60)
    print("📋 数据质量验证")
    print("="*60)

    # 1. 平稳性检验（ADF检验）
    print("\n1️⃣  平稳性检验 (ADF Test):")

    try:
        from statsmodels.tsa.stattools import adfuller

        for col in returns.columns:
            result = adfuller(returns[col].dropna())
            p_value = result[1]
            is_stationary = "✅ 平稳" if p_value < 0.05 else "❌ 非平稳"
            print(f"  {col}: p={p_value:.4f} {is_stationary}")

    except ImportError:
        print("  ⚠️  statsmodels未安装，跳过ADF检验")
        print("  安装命令: pip install statsmodels")

    # 2. 基本统计
    print("\n2️⃣  收益率基本统计:")
    print(returns.describe())

    # 3. 缺失值模式
    print("\n3️⃣  缺失值模式分析:")

    # 检查是否有连续大量缺失
    for col in df.columns:
        missing = df[col].isna()
        if missing.any():
            # 找出最长的连续缺失
            groups = (missing != missing.shift()).cumsum()
            max_consecutive = missing.groupby(groups).sum().max()
            print(f"  {col}: 最长连续缺失 {max_consecutive} 天")
        else:
            print(f"  {col}: 无缺失值")

    print("\n" + "="*60)


def save_data(df, returns, correlation, valid_pairs, filename_base='improved_data'):
    """
    保存数据到Parquet格式
    """
    print(f"\n💾 保存数据到Parquet...")

    # 保存原始价格
    price_file = f'{filename_base}_prices.parquet'
    df.to_parquet(price_file)
    print(f"  ✅ 价格数据: {price_file}")

    # 保存收益率
    returns_file = f'{filename_base}_returns.parquet'
    returns.to_parquet(returns_file)
    print(f"  ✅ 收益率数据: {returns_file}")

    # 保存相关性
    if correlation is not None:
        corr_df = pd.DataFrame({
            'correlation': correlation,
            'valid_pairs': valid_pairs
        })
        corr_file = f'{filename_base}_correlation.parquet'
        corr_df.to_parquet(corr_file)
        print(f"  ✅ 相关性数据: {corr_file}")

    print(f"\n✅ 所有数据已保存")


def main():
    """
    主函数：执行完整的数据收集流程
    """
    print("="*60)
    print("🚀 改进的数据收集脚本")
    print("="*60)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # 配置
    START_DATE = '2015-01-01'
    END_DATE = None  # None表示到今天

    # 1. 获取BTC数据
    btc = fetch_btc_data(START_DATE, END_DATE)

    # 2. 获取黄金数据
    gold = fetch_gold_data_alphavantage(ALPHA_VANTAGE_KEY, START_DATE)

    # 如果Alpha Vantage失败，使用备用方案
    if gold is None or gold.empty:
        gold = fetch_gold_data_yfinance_backup(START_DATE, END_DATE)

    # 3. 获取辅助数据
    dxy = fetch_dxy_data(START_DATE, END_DATE)
    spx = fetch_spx_data(START_DATE, END_DATE)

    # 4. 对齐数据（关键步骤！）
    df = align_data_correctly(btc, gold, dxy, spx)

    # 5. 计算收益率
    returns = calculate_returns(df)

    # 6. 计算相关性
    correlation, valid_pairs = calculate_correlation(returns, window=40)

    # 7. 数据质量验证
    validate_data_quality(df, returns)

    # 8. 保存数据
    save_data(df, returns, correlation, valid_pairs)

    print("\n" + "="*60)
    print(f"✅ 数据收集完成！")
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    return df, returns, correlation


if __name__ == '__main__':
    df, returns, correlation = main()
