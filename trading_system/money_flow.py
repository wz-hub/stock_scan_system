"""
资金流向监控模块 v2
使用现货交易量变化推断资金流向
"""
import requests
import pandas as pd
from datetime import datetime
from typing import Dict, List


class MoneyFlowMonitor:
    """资金流向监控器 - 现货版本"""
    
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
    
    def get_24hr_ticker(self) -> List[Dict]:
        """获取 24 小时行情"""
        try:
            url = f"{self.binance_url}/ticker/24hr"
            response = requests.get(url, timeout=15)
            return response.json()
        except Exception as e:
            print(f"❌ 获取行情失败：{e}")
            return []
    
    def calculate_money_flow(self, ticker_data: List[Dict]) -> List[Dict]:
        """
        计算资金流向
        
        使用 24h 成交量和价格变化推断资金流向：
        净流入 = 24h 成交量 × 涨跌幅 × 价格系数
        """
        all_data = []
        
        for item in ticker_data:
            symbol = item['symbol']
            
            # 只处理 USDT 交易对
            if not symbol.endswith('USDT'):
                continue
            
            # 排除稳定币
            stablecoins = ['USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'FDUSD', 'USD1']
            base_symbol = symbol.replace('USDT', '')
            if base_symbol in stablecoins:
                continue
            
            try:
                # 24h 成交量 (USDT)
                volume_usdt = float(item.get('quoteVolume', 0))
                
                # 24h 涨跌幅
                change_pct = float(item.get('priceChangePercent', 0))
                
                # 当前价格
                price = float(item.get('lastPrice', 0))
                
                # 推断资金流向
                # 上涨 + 放量 = 资金流入
                # 下跌 + 放量 = 资金流出
                # 净流量 = 成交量 × 涨跌幅（简化模型）
                net_flow = volume_usdt * (change_pct / 100)
                
                all_data.append({
                    "symbol": symbol,
                    "symbol_short": base_symbol,
                    "price": price,
                    "volume_24h": volume_usdt,
                    "change_pct": change_pct,
                    "net_flow": net_flow,
                    "net_flow_pct": change_pct,  # 用涨跌幅代替
                    "direction": "in" if net_flow > 0 else "out",
                    "timestamp": datetime.now()
                })
            
            except Exception as e:
                continue
        
        return all_data
    
    def get_money_flow_ranking(self, top_n: int = 50) -> Dict:
        """获取资金流向排行榜"""
        print(f"💰 获取资金流向数据...")
        
        # 获取 24h 行情
        ticker_data = self.get_24hr_ticker()
        print(f"  获取到 {len(ticker_data)} 个交易对")
        
        # 计算资金流向
        all_data = self.calculate_money_flow(ticker_data)
        print(f"  有效数据 {len(all_data)} 条")
        
        if not all_data:
            return {
                "inflow_top20": [],
                "outflow_top20": [],
                "pct_inflow_top20": [],
                "pct_outflow_top20": [],
                "all_data": [],
                "timestamp": datetime.now()
            }
        
        # 转换为 DataFrame
        df = pd.DataFrame(all_data)
        
        # 按净流量排序（绝对值）
        df_sorted = df.sort_values('net_flow', ascending=False)
        
        # 按变化百分比排序
        df_pct = df.sort_values('change_pct', ascending=False)
        
        # Top20
        inflow_top20 = df_sorted.head(20).to_dict('records')
        outflow_top20 = df_sorted.tail(20).iloc[::-1].to_dict('records')  # 反转，流出最多的在前
        pct_inflow_top20 = df_pct.head(20).to_dict('records')
        pct_outflow_top20 = df_pct.tail(20).iloc[::-1].to_dict('records')
        
        return {
            "inflow_top20": inflow_top20,
            "outflow_top20": outflow_top20,
            "pct_inflow_top20": pct_inflow_top20,
            "pct_outflow_top20": pct_outflow_top20,
            "all_data": all_data,
            "timestamp": datetime.now()
        }
    
    def get_scan_symbols(self, inflow_top_n: int = 20, outflow_top_n: int = 20) -> List[str]:
        """获取需要扫描的币种列表"""
        ranking = self.get_money_flow_ranking(top_n=50)
        
        symbols = set()
        
        for item in ranking['inflow_top20'][:inflow_top_n]:
            symbols.add(item['symbol'])
        
        for item in ranking['outflow_top20'][:outflow_top_n]:
            symbols.add(item['symbol'])
        
        return list(symbols)


def format_money_value(value: float) -> str:
    """格式化金额"""
    if abs(value) >= 1e9:
        return f"${value/1e9:.1f}B"
    elif abs(value) >= 1e6:
        return f"${value/1e6:.1f}M"
    elif abs(value) >= 1e3:
        return f"${value/1e3:.1f}K"
    else:
        return f"${value:.0f}"


# 测试
if __name__ == "__main__":
    print("💰 资金流向监控测试 (现货版)")
    print("="*80)
    
    monitor = MoneyFlowMonitor()
    ranking = monitor.get_money_flow_ranking(top_n=50)
    
    print("\n" + "="*80)
    print("🟢 资金净流入 Top20")
    print("="*80)
    print(f"{'排名':<4} {'合约':<12} {'净流量':<14} {'24h 成交量':<14} {'24h 涨跌':<10}")
    print("-"*80)
    
    for i, item in enumerate(ranking['inflow_top20'], 1):
        net_flow = format_money_value(item['net_flow'])
        volume = format_money_value(item['volume_24h'])
        change = f"{item['change_pct']:+.2f}%"
        direction = "↑" if item['net_flow'] > 0 else "↓"
        
        print(f"{i:<4} {item['symbol_short']:<12} {net_flow:>14} {volume:>14} {direction} {change:>8}")
    
    print("\n" + "="*80)
    print("🔴 资金净流出 Top20")
    print("="*80)
    print(f"{'排名':<4} {'合约':<12} {'净流量':<14} {'24h 成交量':<14} {'24h 涨跌':<10}")
    print("-"*80)
    
    for i, item in enumerate(ranking['outflow_top20'], 1):
        net_flow = format_money_value(item['net_flow'])
        volume = format_money_value(item['volume_24h'])
        change = f"{item['change_pct']:+.2f}%"
        direction = "↑" if item['net_flow'] > 0 else "↓"
        
        print(f"{i:<4} {item['symbol_short']:<12} {net_flow:>14} {volume:>14} {direction} {change:>8}")
    
    print(f"\n数据时间：{ranking['timestamp']}")
