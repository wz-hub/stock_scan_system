#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crypto Scanner - 加密货币扫描器主程序

专注于加密货币策略扫描，已移除 A 股/美股支持
"""

import sys
import os
import argparse
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from crypto_data import CryptoFetcher
from strategies.crypto_btc_ma import strategy as btc_strategy
from strategies.crypto_eth_funding import strategy as eth_strategy

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/scan.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def scan_symbol(symbol: str, fetcher: CryptoFetcher):
    """
    扫描单个币种
    
    Args:
        symbol: 币种符号
        fetcher: 数据获取器
    """
    logger.info(f"Scanning {symbol}...")
    
    # 获取价格
    data = fetcher.get_price(symbol)
    if not data:
        logger.error(f"Failed to fetch price for {symbol}")
        print(f"❌ {symbol}: 数据获取失败")
        return
    
    # 打印基本信息
    print(f"\n{'='*60}")
    print(f"{symbol} - ${data['price']:,.2f}")
    print(f"24h Change: {data['change_24h']:+.2f}%")
    print(f"24h Volume: ${data['volume_24h']:,.0f}")
    if data.get('funding_rate'):
        print(f"Funding Rate: {data['funding_rate']*100:.4f}%")
    
    # 运行策略
    signals = []
    
    # BTC 策略
    if symbol == 'BTC':
        signal = btc_strategy.scan({}, data)
        if signal:
            signals.append(signal)
    
    # ETH 策略
    if symbol == 'ETH':
        signal = eth_strategy.scan({}, data)
        if signal:
            signals.append(signal)
    
    # 打印策略信号
    if signals:
        print(f"\n📊 策略信号:")
        for signal in signals:
            emoji = "🟢" if signal.get('signal') == 'buy' else "🔴" if signal.get('signal') == 'sell' else "⚪"
            print(f"  {emoji} {signal['type']}")
            print(f"     描述：{signal.get('description', 'N/A')}")
            print(f"     置信度：{signal.get('confidence', 0)}%")
            if signal.get('entry_price'):
                print(f"     入场：${signal['entry_price']:,.2f}")
            if signal.get('target_price'):
                print(f"     目标：${signal['target_price']:,.2f}")
            if signal.get('stop_loss'):
                print(f"     止损：${signal['stop_loss']:,.2f}")
    else:
        print(f"\n⚪ 暂无策略信号")
    
    print(f"{'='*60}\n")


def scan_all(fetcher: CryptoFetcher):
    """
    扫描所有主流币种
    
    Args:
        fetcher: 数据获取器
    """
    symbols = ['BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC']
    
    print(f"\n🪙 开始扫描 {len(symbols)} 个主流币种...\n")
    
    for symbol in symbols:
        try:
            scan_symbol(symbol, fetcher)
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")
            print(f"❌ {symbol}: {e}")


def show_top_gainers(fetcher: CryptoFetcher):
    """
    显示涨幅榜
    
    Args:
        fetcher: 数据获取器
    """
    print(f"\n📈 24h 涨幅榜 Top 10:\n")
    gainers = fetcher.get_top_gainers(10)
    
    for i, g in enumerate(gainers, 1):
        print(f"  {i}. {g['symbol']}: ${g['price']:,.2f} ({g['change_24h']:+.2f}%)")
    
    print()


def show_top_losers(fetcher: CryptoFetcher):
    """
    显示跌幅榜
    
    Args:
        fetcher: 数据获取器
    """
    print(f"\n📉 24h 跌幅榜 Top 10:\n")
    losers = fetcher.get_top_losers(10)
    
    for i, l in enumerate(losers, 1):
        print(f"  {i}. {l['symbol']}: ${l['price']:,.2f} ({l['change_24h']:+.2f}%)")
    
    print()


def monitor_whales(fetcher: CryptoFetcher):
    """
    监控大额转账
    
    Args:
        fetcher: 数据获取器
    """
    print(f"\n🐋 大额转账监控中... (阈值：$1,000,000)\n")
    alerts = fetcher.get_whale_alerts(threshold_usd=1000000)
    
    if alerts:
        for alert in alerts:
            print(f"  [{alert['timestamp']}] {alert['symbol']}: {alert['amount']} ({alert['usd_value']})")
    else:
        print("  暂无大额转账预警")
    
    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='🪙 Crypto Scanner - 加密货币策略扫描器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run.py --symbol BTC        扫描 BTC
  python run.py --all               扫描所有主流币种
  python run.py --top-gainers       显示涨幅榜
  python run.py --top-losers        显示跌幅榜
  python run.py --whale             监控大额转账
        """
    )
    
    parser.add_argument('--symbol', '-s', type=str, help='币种符号（如 BTC、ETH）')
    parser.add_argument('--all', '-a', action='store_true', help='扫描所有主流币种')
    parser.add_argument('--top-gainers', '-g', action='store_true', help='显示涨幅榜')
    parser.add_argument('--top-losers', '-l', action='store_true', help='显示跌幅榜')
    parser.add_argument('--whale', '-w', action='store_true', help='监控大额转账')
    parser.add_argument('--funding', '-f', action='store_true', help='显示资金费率')
    
    args = parser.parse_args()
    
    # 创建数据获取器
    fetcher = CryptoFetcher()
    
    # 根据参数执行
    if args.symbol:
        scan_symbol(args.symbol.upper(), fetcher)
    elif args.all:
        scan_all(fetcher)
    elif args.top_gainers:
        show_top_gainers(fetcher)
    elif args.top_losers:
        show_top_losers(fetcher)
    elif args.whale:
        monitor_whales(fetcher)
    elif args.funding:
        # 显示资金费率
        print(f"\n💰 资金费率监控:\n")
        for symbol in ['BTC', 'ETH', 'BNB', 'SOL']:
            data = fetcher.get_price(symbol)
            if data and data.get('funding_rate'):
                print(f"  {symbol}: {data['funding_rate']*100:.4f}%")
        print()
    else:
        parser.print_help()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 程序已中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序异常退出：{e}")
        print(f"\n❌ 程序异常：{e}")
        sys.exit(1)
