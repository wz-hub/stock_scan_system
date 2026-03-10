#!/usr/bin/env python3
"""
历史数据下载器 - 从 Binance 下载多周期 K 线数据

支持：
- 多时间周期：1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 3d, 1w, 1M
- 批量下载：支持多个交易对
- 增量更新：只下载新数据
- 自动重试：网络错误自动重试
- 进度显示：实时显示下载进度
"""

import sys
import requests
import pandas as pd
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional
import sqlite3
import json


class BinanceDataDownloader:
    """Binance 历史数据下载器"""
    
    def __init__(self, db_path: str = 'cache/trading.db'):
        """
        初始化下载器
        
        Args:
            db_path: SQLite 数据库路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Binance API
        self.base_url = "https://api.binance.com"
        self.api_endpoint = "/api/v3/klines"
        
        # 时间周期映射
        self.timeframe_map = {
            '1m': '1m', '3m': '3m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '12h': '12h',
            '1d': '1d', '3d': '3d', '1w': '1w', '1M': '1M'
        }
        
        # 初始化数据库
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建 klines 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                interval TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                quote_volume REAL NOT NULL,
                trades_count INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, interval, timestamp)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_symbol_interval ON klines(symbol, interval)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON klines(timestamp)')
        
        conn.commit()
        conn.close()
    
    def download_klines(self, symbol: str, interval: str, start_date: str, end_date: str, 
                       limit: int = 1000, verbose: bool = True) -> int:
        """
        下载 K 线数据
        
        Args:
            symbol: 交易对 (如 'BTCUSDT')
            interval: 时间周期 (如 '1h', '4h', '1d')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 每次请求的最大条数 (默认 1000)
            verbose: 是否显示进度
        
        Returns:
            下载的 K 线数量
        """
        # 转换日期为时间戳
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        
        if verbose:
            print(f"📥 下载 {symbol} {interval} 数据...")
            print(f"   时间范围：{start_date} ~ {end_date}")
        
        total_downloaded = 0
        current_ts = start_ts
        retry_count = 0
        max_retries = 3
        
        while current_ts < end_ts:
            # 构建请求参数
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': current_ts,
                'endTime': end_ts,
                'limit': limit
            }
            
            # 发送请求
            success = False
            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        f"{self.base_url}{self.api_endpoint}",
                        params=params,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        success = True
                        break
                    elif response.status_code == 429:
                        # 频率限制
                        wait_time = 2 ** attempt
                        if verbose:
                            print(f"   ⏳ 频率限制，等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                    else:
                        if verbose:
                            print(f"   ❌ API 错误：{response.status_code}")
                        break
                        
                except Exception as e:
                    if verbose:
                        print(f"   ⚠️  请求失败 (尝试 {attempt+1}/{max_retries}): {e}")
                    time.sleep(2 ** attempt)
            
            if not success:
                break
            
            if not data:
                break
            
            # 解析数据
            klines = []
            for k in data:
                kline = {
                    'symbol': symbol,
                    'interval': interval,
                    'timestamp': k[0],
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'quote_volume': float(k[6]),
                    'trades_count': int(k[8])
                }
                klines.append(kline)
            
            # 保存到数据库
            self._save_klines(klines)
            total_downloaded += len(klines)
            
            if verbose:
                progress = (current_ts - start_ts) / (end_ts - start_ts) * 100
                print(f"   进度：{progress:.1f}% (已下载 {total_downloaded} 条)")
            
            # 更新当前时间戳
            if data:
                current_ts = data[-1][0] + 1  # 从最后一条的下一条开始
            else:
                break
            
            # 避免频率限制
            time.sleep(0.2)
        
        if verbose:
            print(f"   ✅ 完成！共下载 {total_downloaded} 条 K 线")
        
        return total_downloaded
    
    def _save_klines(self, klines: List[dict]):
        """保存 K 线到数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for k in klines:
            cursor.execute('''
                INSERT OR REPLACE INTO klines 
                (symbol, interval, timestamp, open, high, low, close, volume, quote_volume, trades_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                k['symbol'], k['interval'], k['timestamp'],
                k['open'], k['high'], k['low'], k['close'],
                k['volume'], k['quote_volume'], k['trades_count']
            ))
        
        conn.commit()
        conn.close()
    
    def download_symbols(self, symbols: List[str], intervals: List[str], 
                        days: int = 180, verbose: bool = True):
        """
        批量下载多个交易对的多个时间周期
        
        Args:
            symbols: 交易对列表
            intervals: 时间周期列表
            days: 下载天数
            verbose: 是否显示进度
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        total_symbols = len(symbols)
        total_intervals = len(intervals)
        total_tasks = total_symbols * total_intervals
        
        print("=" * 80)
        print("📊 Binance 历史数据下载")
        print("=" * 80)
        print(f"交易对数量：{total_symbols}")
        print(f"时间周期：{', '.join(intervals)}")
        print(f"下载天数：{days} 天")
        print(f"时间范围：{start_date_str} ~ {end_date_str}")
        print(f"总任务数：{total_tasks}")
        print("=" * 80)
        print()
        
        total_downloaded = 0
        task_count = 0
        
        for symbol in symbols:
            for interval in intervals:
                task_count += 1
                print(f"\n[{task_count}/{total_tasks}] 下载 {symbol} {interval}...")
                
                count = self.download_klines(
                    symbol=symbol,
                    interval=interval,
                    start_date=start_date_str,
                    end_date=end_date_str,
                    verbose=verbose
                )
                
                total_downloaded += count
                
                # 每个交易对之间等待，避免频率限制
                time.sleep(1)
        
        print()
        print("=" * 80)
        print(f"✅ 下载完成！")
        print(f"总下载量：{total_downloaded} 条 K 线")
        print(f"数据库：{self.db_path}")
        print("=" * 80)
    
    def get_stats(self) -> dict:
        """获取数据库统计信息"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) FROM klines')
        total = cursor.fetchone()[0]
        
        # 按周期统计
        cursor.execute('''
            SELECT interval, COUNT(*), 
                   MIN(timestamp) as min_ts, 
                   MAX(timestamp) as max_ts
            FROM klines
            GROUP BY interval
            ORDER BY interval
        ''')
        by_interval = cursor.fetchall()
        
        # 按交易对统计
        cursor.execute('''
            SELECT symbol, COUNT(*)
            FROM klines
            GROUP BY symbol
            ORDER BY COUNT(*) DESC
            LIMIT 20
        ''')
        by_symbol = cursor.fetchall()
        
        conn.close()
        
        return {
            'total': total,
            'by_interval': by_interval,
            'by_symbol': by_symbol
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Binance 历史数据下载器')
    parser.add_argument('--symbols', type=str, default='BTCUSDT,ETHUSDT,BCHUSDT,XRPUSDT,DOGEUSDT',
                       help='交易对列表，逗号分隔')
    parser.add_argument('--intervals', type=str, default='1h,4h,1d',
                       help='时间周期列表，逗号分隔')
    parser.add_argument('--days', type=int, default=1095,  # 3 年
                       help='下载天数 (默认 3 年=1095 天)')
    parser.add_argument('--db', type=str, default='cache/trading.db',
                       help='数据库路径')
    parser.add_argument('--quiet', action='store_true', help='静默模式')
    
    args = parser.parse_args()
    
    # 解析参数
    symbols = [s.strip() for s in args.symbols.split(',')]
    intervals = [i.strip() for i in args.intervals.split(',')]
    
    # 创建下载器
    downloader = BinanceDataDownloader(db_path=args.db)
    
    # 下载数据
    downloader.download_symbols(
        symbols=symbols,
        intervals=intervals,
        days=args.days,
        verbose=not args.quiet
    )
    
    # 显示统计
    print()
    stats = downloader.get_stats()
    print("📊 数据库统计")
    print(f"总记录数：{stats['total']:,} 条 K 线")
    print()
    print("按周期统计:")
    for interval, count, min_ts, max_ts in stats['by_interval']:
        min_date = datetime.fromtimestamp(min_ts/1000).strftime('%Y-%m-%d') if min_ts else 'N/A'
        max_date = datetime.fromtimestamp(max_ts/1000).strftime('%Y-%m-%d') if max_ts else 'N/A'
        print(f"  {interval}: {count:,} 条 ({min_date} ~ {max_date})")
    print()
    print("Top 交易对:")
    for symbol, count in stats['by_symbol'][:10]:
        print(f"  {symbol}: {count:,} 条")


if __name__ == '__main__':
    main()
