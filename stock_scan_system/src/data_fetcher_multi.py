# -*- coding: utf-8 -*-
"""
多数据源容错数据获取模块

支持：
- A 股：东方财富（主）+ 腾讯财经（备用）
- 美股：Yahoo Finance（主）+ Alpha Vantage（备用）
- 加密货币：Binance（主）+ CoinGecko（备用）
"""

import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class MultiSourceDataFetcher:
    """多数据源容错获取器"""
    
    def __init__(self):
        self.sources = {
            'a_share': ['eastmoney', 'tencent'],
            'us_stock': ['yahoo', 'alphavantage'],
            'crypto': ['binance', 'coingecko'],
        }
        self.cache = {}
        self.cache_ttl = 300  # 5 分钟缓存
        
    def fetch_price(self, symbol: str, market: str) -> Optional[Dict[str, Any]]:
        """
        获取价格（带故障切换）
        
        Args:
            symbol: 股票代码（如 601138、NVDA、BTC）
            market: 市场（a_share、us_stock、crypto）
            
        Returns:
            价格数据字典，失败返回 None
        """
        # 检查缓存
        cache_key = f"{market}:{symbol}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_data
        
        # 尝试多个数据源
        sources = self.sources.get(market, [])
        for source in sources:
            try:
                logger.info(f"Trying {source} for {symbol}")
                data = getattr(self, f'_fetch_from_{source}')(symbol, market)
                if data:
                    # 缓存成功结果
                    self.cache[cache_key] = (time.time(), data)
                    logger.info(f"Successfully fetched {symbol} from {source}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to fetch from {source}: {e}")
                continue
        
        logger.error(f"All sources failed for {symbol}")
        return None
    
    def _fetch_from_eastmoney(self, symbol: str, market: str) -> Optional[Dict]:
        """东方财富数据源"""
        import akshare as ak
        try:
            # A 股实时行情
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == symbol]
            if len(stock_data) == 0:
                return None
            
            return {
                'symbol': symbol,
                'price': float(stock_data['最新价'].iloc[0]),
                'change': float(stock_data['涨跌幅'].iloc[0]),
                'volume': float(stock_data['成交量'].iloc[0]),
                'turnover': float(stock_data['成交额'].iloc[0]),
                'high': float(stock_data['最高'].iloc[0]),
                'low': float(stock_data['最低'].iloc[0]),
                'open': float(stock_data['今开'].iloc[0]),
                'prev_close': float(stock_data['昨收'].iloc[0]),
                'timestamp': datetime.now(),
                'source': 'eastmoney'
            }
        except Exception as e:
            logger.error(f"Eastmoney fetch failed: {e}")
            return None
    
    def _fetch_from_tencent(self, symbol: str, market: str) -> Optional[Dict]:
        """腾讯财经数据源（备用）"""
        import requests
        try:
            url = f"http://qt.gtimg.cn/q={symbol}"
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                return None
            
            # 解析腾讯数据格式
            data = response.content.decode('gbk').split('~')
            if len(data) < 50:
                return None
            
            return {
                'symbol': symbol,
                'price': float(data[3]),
                'change': float(data[32]),
                'volume': float(data[6]),
                'turnover': float(data[37]),
                'high': float(data[33]),
                'low': float(data[34]),
                'open': float(data[5]),
                'prev_close': float(data[4]),
                'timestamp': datetime.now(),
                'source': 'tencent'
            }
        except Exception as e:
            logger.error(f"Tencent fetch failed: {e}")
            return None
    
    def _fetch_from_yahoo(self, symbol: str, market: str) -> Optional[Dict]:
        """Yahoo Finance 数据源"""
        import yfinance as yf
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.fast_info
            return {
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'change': float(data['regularMarketChangePercent']),
                'volume': float(data['lastVolume']),
                'high': float(data['dayHigh']),
                'low': float(data['dayLow']),
                'open': float(data['regularMarketOpen']),
                'prev_close': float(data['previousClose']),
                'timestamp': datetime.now(),
                'source': 'yahoo'
            }
        except Exception as e:
            logger.error(f"Yahoo fetch failed: {e}")
            return None
    
    def _fetch_from_alphavantage(self, symbol: str, market: str) -> Optional[Dict]:
        """Alpha Vantage 数据源（备用）"""
        import requests
        import os
        api_key = os.getenv('ALPHA_VANTAGE_KEY', 'demo')
        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            response = requests.get(url, timeout=5)
            data = response.json()
            quote = data.get('Global Quote', {})
            return {
                'symbol': symbol,
                'price': float(quote.get('05. price', 0)),
                'change': float(quote.get('10. change percent', 0)),
                'volume': float(quote.get('06. volume', 0)),
                'timestamp': datetime.now(),
                'source': 'alphavantage'
            }
        except Exception as e:
            logger.error(f"AlphaVantage fetch failed: {e}")
            return None
    
    def _fetch_from_binance(self, symbol: str, market: str) -> Optional[Dict]:
        """Binance 数据源"""
        import requests
        try:
            # 币安 API
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT"
            response = requests.get(url, timeout=5)
            data = response.json()
            return {
                'symbol': symbol,
                'price': float(data['lastPrice']),
                'change': float(data['priceChangePercent']),
                'volume': float(data['volume']),
                'turnover': float(data['quoteVolume']),
                'high': float(data['highPrice']),
                'low': float(data['lowPrice']),
                'timestamp': datetime.now(),
                'source': 'binance'
            }
        except Exception as e:
            logger.error(f"Binance fetch failed: {e}")
            return None
    
    def _fetch_from_coingecko(self, symbol: str, market: str) -> Optional[Dict]:
        """CoinGecko 数据源（备用）"""
        import requests
        try:
            # CoinGecko API
            coin_id = symbol.lower()
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            response = requests.get(url, timeout=5)
            data = response.json()
            market_data = data.get('market_data', {})
            return {
                'symbol': symbol,
                'price': market_data.get('current_price', {}).get('usd', 0),
                'change': market_data.get('price_change_percentage_24h', 0),
                'volume': market_data.get('total_volume', {}).get('usd', 0),
                'high': market_data.get('high_24h', {}).get('usd', 0),
                'low': market_data.get('low_24h', {}).get('usd', 0),
                'timestamp': datetime.now(),
                'source': 'coingecko'
            }
        except Exception as e:
            logger.error(f"CoinGecko fetch failed: {e}")
            return None
    
    def get_history(self, symbol: str, market: str, days: int = 30) -> List[Dict]:
        """获取历史数据"""
        # 简化实现，实际应该从数据库或 API 获取
        logger.info(f"Fetching {days} days history for {symbol}")
        return []
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("Cache cleared")


# 兼容旧接口
class DataFetcher(MultiSourceDataFetcher):
    """向后兼容的 DataFetcher 类"""
    pass


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    fetcher = MultiSourceDataFetcher()
    
    # 测试 A 股
    print("Testing A 股...")
    data = fetcher.fetch_price('601138', 'a_share')
    print(f"Result: {data}")
    
    # 测试美股
    print("\nTesting 美股...")
    data = fetcher.fetch_price('NVDA', 'us_stock')
    print(f"Result: {data}")
    
    # 测试加密货币
    print("\nTesting 加密货币...")
    data = fetcher.fetch_price('BTC', 'crypto')
    print(f"Result: {data}")
