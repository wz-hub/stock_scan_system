"""
技术分析数据补充模块
为 AI 评分提供完整的技术分析数据
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.last_row = df.iloc[-1] if len(df) > 0 else None
    
    def calculate_multi_timeframe(self, symbol: str) -> Dict:
        """多时间周期分析"""
        # 简化版本：从当前数据推断
        # 实际应该获取不同周期的数据
        
        if self.last_row is None:
            return {}
        
        # 计算不同周期的趋势
        close = self.last_row['close']
        ma20 = self.df['close'].rolling(20).mean().iloc[-1] if len(self.df) >= 20 else close
        ma50 = self.df['close'].rolling(50).mean().iloc[-1] if len(self.df) >= 50 else close
        ma200 = self.df['close'].rolling(200).mean().iloc[-1] if len(self.df) >= 200 else close
        
        return {
            "1H": {"trend": "N/A", "note": "需要小时线数据"},
            "4H": {"trend": "N/A", "note": "需要 4 小时线数据"},
            "1D": {
                "trend": "BULLISH" if close > ma20 else "BEARISH",
                "price_vs_ma20": f"{(close/ma20 - 1)*100:+.2f}%"
            },
            "1W": {
                "trend": "BULLISH" if close > ma50 else "BEARISH",
                "price_vs_ma50": f"{(close/ma50 - 1)*100:+.2f}%"
            },
            "1M": {
                "trend": "BULLISH" if close > ma200 else "BEARISH",
                "price_vs_ma200": f"{(close/ma200 - 1)*100:+.2f}%"
            }
        }
    
    def calculate_indicators(self) -> Dict:
        """计算技术指标"""
        if self.last_row is None:
            return {}
        
        indicators = {}
        
        # RSI
        indicators['RSI'] = self._calculate_rsi()
        
        # MACD
        indicators['MACD'] = self._calculate_macd()
        
        # KDJ
        indicators['KDJ'] = self._calculate_kdj()
        
        # 布林带
        indicators['布林带'] = self._calculate_bollinger()
        
        # ATR
        indicators['ATR'] = self._calculate_atr()
        
        # 成交量
        if 'volume' in self.df.columns:
            indicators['成交量'] = self._analyze_volume()
        
        return indicators
    
    def _calculate_rsi(self, period: int = 14) -> Dict:
        """计算 RSI"""
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0.0).rolling(period).mean()
        loss = -delta.where(delta < 0, 0.0).rolling(period).mean()
        
        if gain.iloc[-1] == 0:
            rsi = 0
        elif loss.iloc[-1] == 0:
            rsi = 100
        else:
            rs = gain.iloc[-1] / loss.iloc[-1]
            rsi = 100 - (100 / (1 + rs))
        
        status = "超买" if rsi > 70 else "超卖" if rsi < 30 else "中性"
        
        return {
            "value": round(rsi, 2),
            "status": status
        }
    
    def _calculate_macd(self) -> Dict:
        """计算 MACD"""
        exp1 = self.df['close'].ewm(span=12, adjust=False).mean()
        exp2 = self.df['close'].ewm(span=26, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        
        status = "金叉" if current_macd > current_signal else "死叉"
        
        return {
            "MACD": round(current_macd, 2),
            "Signal": round(current_signal, 2),
            "Histogram": round(current_hist, 2),
            "status": status
        }
    
    def _calculate_kdj(self) -> Dict:
        """计算 KDJ"""
        low_n = self.df['low'].rolling(9).min()
        high_n = self.df['high'].rolling(9).max()
        
        rsv = (self.df['close'] - low_n) / (high_n - low_n) * 100
        
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d
        
        current_k = k.iloc[-1]
        current_d = d.iloc[-1]
        current_j = j.iloc[-1]
        
        status = "超买" if current_k > 80 else "超卖" if current_k < 20 else "中性"
        
        return {
            "K": round(current_k, 2),
            "D": round(current_d, 2),
            "J": round(current_j, 2),
            "status": status
        }
    
    def _calculate_bollinger(self) -> Dict:
        """计算布林带"""
        middle = self.df['close'].rolling(20).mean()
        std = self.df['close'].rolling(20).std()
        upper = middle + 2 * std
        lower = middle - 2 * std
        
        current_price = self.last_row['close']
        current_upper = upper.iloc[-1]
        current_lower = lower.iloc[-1]
        current_middle = middle.iloc[-1]
        
        position = "上轨" if current_price > current_upper else "下轨" if current_price < current_lower else "中轨"
        width = (current_upper - current_lower) / current_middle * 100
        
        return {
            "上轨": round(current_upper, 2),
            "中轨": round(current_middle, 2),
            "下轨": round(current_lower, 2),
            "position": position,
            "width": f"{width:.2f}%"
        }
    
    def _calculate_atr(self, period: int = 14) -> Dict:
        """计算 ATR"""
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift(1))
        low_close = abs(self.df['low'] - self.df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        
        current_price = self.last_row['close']
        atr_pct = atr / current_price * 100
        
        return {
            "value": round(atr, 2),
            "percent": f"{atr_pct:.2f}%"
        }
    
    def _analyze_volume(self) -> Dict:
        """分析成交量"""
        if 'volume' not in self.df.columns:
            return {}
        
        volume = self.df['volume']
        volume_sma20 = volume.rolling(20).mean()
        
        current_volume = volume.iloc[-1]
        avg_volume = volume_sma20.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # 成交量趋势
        volume_trend_5 = volume.rolling(5).mean().iloc[-1] / avg_volume if avg_volume > 0 else 1.0
        
        status = "放量" if volume_ratio >= 1.5 else "平量" if volume_ratio >= 0.8 else "缩量"
        
        return {
            "current": round(current_volume, 0),
            "avg_20": round(avg_volume, 0),
            "ratio": f"{volume_ratio:.2f}倍",
            "trend_5d": f"{volume_trend_5:.2f}倍",
            "status": status
        }
    
    def calculate_support_resistance(self) -> Dict:
        """计算支撑阻力位"""
        if len(self.df) < 50:
            return {}
        
        # 寻找局部高点和低点
        recent_highs = self.df[self.df['high'] == self.df['high'].rolling(20).max()]['high'].dropna()
        recent_lows = self.df[self.df['low'] == self.df['low'].rolling(20).min()]['low'].dropna()
        
        # 取最近的几个关键点
        supports = sorted(recent_lows.tail(3).tolist()) if len(recent_lows) > 0 else []
        resistances = sorted(recent_highs.tail(3).tolist(), reverse=True) if len(recent_highs) > 0 else []
        
        # 添加整数关口
        current_price = self.last_row['close']
        price_round = round(current_price, -3)  # 千位整数
        
        if price_round not in supports and price_round < current_price:
            supports.append(price_round)
        if price_round * 1.05 not in resistances and price_round * 1.05 > current_price:
            resistances.append(price_round * 1.05)
        
        return {
            "supports": [round(s, 2) for s in supports],
            "resistances": [round(r, 2) for r in resistances],
            "current_price": round(current_price, 2)
        }
    
    def get_full_analysis(self, symbol: str) -> Dict:
        """获取完整技术分析"""
        return {
            "indicators": self.calculate_indicators(),
            "timeframe_analysis": self.calculate_multi_timeframe(symbol),
            "support_resistance": self.calculate_support_resistance(),
            "volume_analysis": self.calculate_indicators().get('成交量', {})
        }


def get_technical_analysis(df: pd.DataFrame, symbol: str) -> Dict:
    """便捷函数：获取技术分析"""
    analyzer = TechnicalAnalyzer(df)
    return analyzer.get_full_analysis(symbol)


# 测试
if __name__ == "__main__":
    from backtest.data_loader import DataLoader
    
    print("📊 技术分析模块测试")
    
    loader = DataLoader()
    df = loader.load_csv('data/BTC-USD.csv')
    
    analysis = get_technical_analysis(df, 'BTC-USD')
    
    print("\n技术指标:")
    for key, value in analysis.get('indicators', {}).items():
        print(f"  {key}: {value}")
    
    print("\n多时间周期:")
    for tf, data in analysis.get('timeframe_analysis', {}).items():
        print(f"  {tf}: {data}")
    
    print("\n支撑阻力:")
    sr = analysis.get('support_resistance', {})
    print(f"  支撑：{sr.get('supports', [])}")
    print(f"  阻力：{sr.get('resistances', [])}")
