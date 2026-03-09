"""
实时数据模块 - 支持 Binance/coinmarketcap
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import time


class RealtimeData:
    """实时数据获取"""
    
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.coincap_url = "https://api.coincap.io/v2"
    
    def get_binance_klines(self, symbol: str = "BTCUSDT", interval: str = "1d", limit: int = 500) -> pd.DataFrame:
        """
        获取 Binance K 线数据
        
        参数:
            symbol: 交易对 (BTCUSDT, ETHUSDT)
            interval: 时间周期 (1m, 5m, 15m, 1h, 4h, 1d, 1w)
            limit: 返回数量 (最多 1000)
        """
        try:
            # 使用币安 US 或主站
            urls = [
                f"https://api.binance.us/api/v3/klines",
                f"https://api.binance.com/api/v3/klines",
                f"https://api1.binance.com/api/v3/klines"
            ]
            
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            for url in urls:
                try:
                    response = requests.get(url, params=params, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        break
                except:
                    continue
            else:
                print("所有 Binance API 都无法访问")
                return pd.DataFrame()
            
            # 转换为 DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_quote_volume', 'ignore'
            ])
            
            # 转换时间戳
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # 转换数值类型
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = df[col].astype(float)
            
            # 重命名列
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }, inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
        
        except Exception as e:
            print(f"获取 Binance 数据失败：{e}")
            return pd.DataFrame()
    
    def get_binance_ticker(self, symbol: str = "BTCUSDT") -> Dict:
        """获取实时价格"""
        try:
            url = f"{self.binance_url}/ticker/24hr"
            params = {"symbol": symbol}
            
            response = requests.get(url, params=params, timeout=10)
            return response.json()
        
        except Exception as e:
            print(f"获取实时价格失败：{e}")
            return {}
    
    def get_top_volume_symbols(self, limit: int = 100) -> List[str]:
        """获取成交量前 N 的币种"""
        try:
            url = f"{self.binance_url}/ticker/24hr"
            response = requests.get(url, timeout=15)
            data = response.json()
            
            # 只保留 USDT 交易对
            usdt_pairs = [item for item in data if item['symbol'].endswith('USDT')]
            
            # 按 USDT 交易量排序
            df = pd.DataFrame(usdt_pairs)
            df['quoteVolume'] = pd.to_numeric(df['quoteVolume'])
            df = df.sort_values('quoteVolume', ascending=False)
            
            # 排除稳定币
            stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USD1']
            df = df[~df['symbol'].str.replace('USDT', '').isin(stablecoins)]
            
            return df.head(limit)['symbol'].tolist()
        
        except Exception as e:
            print(f"❌ 获取成交量排行失败：{e}")
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
    
    def get_multiple_klines(self, symbols: List[str] = ["BTCUSDT", "ETHUSDT"], 
                           interval: str = "1d", limit: int = 500) -> Dict[str, pd.DataFrame]:
        """获取多个交易对的 K 线"""
        result = {}
        for symbol in symbols:
            df = self.get_binance_klines(symbol, interval, limit)
            if not df.empty:
                result[symbol] = df
        return result
    
    def stream_price(self, symbol: str = "btcusdt"):
        """
        获取 WebSocket 实时价格流（一次性获取最新价格）
        实际使用需要 WebSocket 连接
        """
        try:
            url = f"https://stream.binance.com:9443/ws/{symbol}@ticker"
            response = requests.get(url, timeout=5)
            return response.json()
        except:
            return {}
    
    def get_current_price(self, symbol: str = "BTC-USD") -> float:
        """获取当前价格"""
        binance_symbol = symbol.replace("-", "").replace(".USD", "USDT")
        if not binance_symbol.endswith("USDT"):
            binance_symbol = binance_symbol + "USDT"
        
        ticker = self.get_binance_ticker(binance_symbol)
        if ticker:
            return float(ticker.get('lastPrice', 0))
        return 0.0
    
    def get_price_change(self, symbol: str = "BTC-USD") -> Dict:
        """获取 24 小时涨跌"""
        binance_symbol = symbol.replace("-", "").replace(".USD", "USDT")
        if not binance_symbol.endswith("USDT"):
            binance_symbol = binance_symbol + "USDT"
        
        ticker = self.get_binance_ticker(binance_symbol)
        if ticker:
            return {
                'price': float(ticker.get('lastPrice', 0)),
                'change_24h': float(ticker.get('priceChangePercent', 0)),
                'high_24h': float(ticker.get('highPrice', 0)),
                'low_24h': float(ticker.get('lowPrice', 0)),
                'volume_24h': float(ticker.get('volume', 0))
            }
        return {}


# 便捷函数
def get_realtime_data(symbol: str = "BTC-USD", days: int = 500) -> pd.DataFrame:
    """获取实时 K 线数据"""
    rt = RealtimeData()
    
    # 转换符号
    binance_symbol = symbol.replace("-", "").replace(".USD", "USDT")
    if not binance_symbol.endswith("USDT"):
        binance_symbol = binance_symbol + "USDT"
    
    # 根据时间范围选择周期
    if days <= 5:
        interval = "5m"
    elif days <= 30:
        interval = "1h"
    else:
        interval = "1d"
    
    df = rt.get_binance_klines(binance_symbol, interval, min(days, 1000))
    return df


def get_realtime_price(symbol: str = "BTC-USD") -> Dict:
    """获取实时价格信息"""
    rt = RealtimeData()
    return rt.get_price_change(symbol)


# 测试
if __name__ == "__main__":
    print("📊 测试实时数据...")
    
    # 获取 K 线
    df = get_realtime_data("BTC-USD", days=100)
    print(f"\n✅ BTC K 线数据：{len(df)} 条")
    print(f"最新价格：${df['close'].iloc[-1]:,.2f}")
    print(f"时间范围：{df.index[0]} 至 {df.index[-1]}")
    
    # 获取实时价格
    price_info = get_realtime_price("BTC-USD")
    print(f"\n💰 BTC 实时价格:")
    print(f"  当前价：${price_info.get('price', 0):,.2f}")
    print(f"  24h 涨跌：{price_info.get('change_24h', 0):+.2f}%")
    print(f"  24h 最高：${price_info.get('high_24h', 0):,.2f}")
    print(f"  24h 最低：${price_info.get('low_24h', 0):,.2f}")
