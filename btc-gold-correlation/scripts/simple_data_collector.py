"""
简化的数据收集脚本 - 专注于核心功能
基于Gemini专家反馈，解决数据源问题
"""

import ccxt
import pandas as pd
import numpy as np
import yfinance as yf
from pandas_datareader import data as pdr
import time
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')


def fetch_btc_combined(start_date='2015-01-01'):
    """
    组合获取BTC数据
    - yfinance: 2015-至今 (历史全覆盖)
    - Binance: 2017-至今 (交叉验证)
    """
    print("📈 获取BTC数据...")

    # 首先尝试yfinance（覆盖2015-至今）
    try:
        print("  - yfinance BTC-USD...")
        btc_yf = yf.download('BTC-USD', start=start_date, progress=False)

        if isinstance(btc_yf.columns, pd.MultiIndex):
            close_col = [col for col in btc_yf.columns if col[0] == 'Close'][0]
            btc = btc_yf[close_col].rename('BTC')
        else:
            btc = btc_yf['Close'].rename('BTC')

        print(f"  ✅ yfinance: {len(btc)} 条 ({btc.index[0].date()} - {btc.index[-1].date()})")
        return btc

    except Exception as e:
        print(f"  ❌ yfinance失败: {e}")

    # 备用方案：Binance（仅2017年后）
    try:
        print("  - Binance (仅2017年后)...")
        exchange = ccxt.binance({'enableRateLimit': True})
        since = int(datetime.strptime('2017-08-01', '%Y-%m-%d').timestamp() * 1000)

        all_data = []
        limit = 1000

        while True:
            ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1d', since=since, limit=limit)
            if not ohlcv or len(ohlcv) == 0:
                break

            all_data.extend(ohlcv)
            since = ohlcv[-1][0] + 86400000

            if len(ohlcv) < limit:
                break

            time.sleep(0.5)

        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
        btc = df.set_index('date')['close'].rename('BTC')

        print(f"  ✅ Binance: {len(btc)} 条")
        return btc

    except Exception as e:
        print(f"  ❌ Binance也失败: {e}")
        return None


def fetch_gold_yfinance(start_date='2015-01-01'):
    """从yfinance获取GLD（黄金ETF）"""
    print("🥇 获取黄金数据 (GLD ETF)...")

    try:
        gld = yf.download('GLD', start=start_date, progress=False)

        # 处理多级列索引
        if isinstance(gld.columns, pd.MultiIndex):
            # 提取Close列
            close_col = [col for col in gld.columns if col[0] == 'Close'][0]
            gold = gld[close_col].rename('Gold')
        else:
            gold = gld['Close'].rename('Gold')

        print(f"✅ Gold: {len(gold)} 条记录")
        return gold

    except Exception as e:
        print(f"❌ 黄金数据失败: {e}")
        return None


def fetch_indices(start_date='2015-01-01'):
    """从FRED获取DXY和SPX"""
    print("📊 获取宏观指标 (FRED)...")

    try:
        dxy = pdr.DataReader('DTWEXBGS', 'fred', start_date)['DTWEXBGS'].rename('DXY')
        print(f"✅ DXY: {len(dxy)} 条记录")
    except:
        dxy = None
        print("⚠️  DXY获取失败")

    try:
        spx = pdr.DataReader('SP500', 'fred', start_date)['SP500'].rename('SPX')
        print(f"✅ SPX: {len(spx)} 条记录")
    except:
        spx = None
        print("⚠️  SPX获取失败")

    return dxy, spx


def combine_data(btc, gold, dxy=None, spx=None):
    """合并所有数据 - 不填充NaN"""
    print("\n🔄 合并数据...")

    df = pd.DataFrame({'BTC': btc, 'Gold': gold})

    if dxy is not None:
        df['DXY'] = dxy
    if spx is not None:
        df['SPX'] = spx

    print(f"\n数据范围: {df.index[0].date()} 至 {df.index[-1].date()}")
    print(f"总天数: {len(df)}\n")

    for col in df.columns:
        valid = df[col].notna().sum()
        print(f"{col}: {valid} 有效点 ({valid/len(df)*100:.1f}%)")

    # 检查周末数据
    weekend = df[df.index.dayofweek >= 5]
    print(f"\n周末数据检查 ({len(weekend)}天):")
    for col in df.columns:
        weekend_valid = weekend[col].notna().sum()
        print(f"{col}: {weekend_valid} 个周末有数据", end='')
        if col == 'BTC':
            print(" ✅")
        elif weekend_valid < len(weekend) * 0.1:
            print(" ✅")
        else:
            print(" ⚠️")

    return df


def calculate_all(df, window=40):
    """计算收益率和相关性"""
    print("\n📈 计算收益率和相关性...")

    # 对数收益率
    returns = np.log(df / df.shift(1))

    # 相关性
    if 'Gold' in returns.columns:
        corr = returns['BTC'].rolling(window).corr(returns['Gold'])
        both_valid = returns[['BTC', 'Gold']].notna().all(axis=1)
        valid_pairs = both_valid.rolling(window).sum()

        print(f"平均有效配对: {valid_pairs.mean():.1f}/{window}")
    else:
        corr = None
        valid_pairs = None

    return returns, corr, valid_pairs


def save_all(df, returns, corr, valid_pairs):
    """保存数据"""
    print("\n💾 保存数据...")

    df.to_parquet('improved_data_prices.parquet')
    returns.to_parquet('improved_data_returns.parquet')

    if corr is not None:
        corr_df = pd.DataFrame({'correlation': corr, 'valid_pairs': valid_pairs})
        corr_df.to_parquet('improved_data_correlation.parquet')

    print("✅ 已保存到Parquet文件")


def main():
    print("="*60)
    print("🚀 简化数据收集脚本 v2")
    print("="*60 + "\n")

    # 获取数据
    btc = fetch_btc_combined('2015-01-01')
    gold = fetch_gold_yfinance('2015-01-01')
    dxy, spx = fetch_indices('2015-01-01')

    # 合并
    df = combine_data(btc, gold, dxy, spx)

    # 计算
    returns, corr, valid_pairs = calculate_all(df)

    # 保存
    save_all(df, returns, corr, valid_pairs)

    print("\n" + "="*60)
    print("✅ 完成！")
    print("="*60)

    return df, returns, corr


if __name__ == '__main__':
    df, returns, corr = main()
