"""
交易信号生成器 - 最终版本
生成完整但简洁的交易信号
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta
import pytz

# 北京时间时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader
from strategies import (
    TrendFollowingStrategy,
    Reversal123Strategy,
    SupportResistanceStrategy,
    PatternTradingStrategy,
    MACrossStrategy,
    VolatilityBreakoutStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    BreakoutStrategy,
    MultiTimeframeStrategy,
    VolatilitySqueezeStrategy,
    MoneyFlowStrategy,
    LiquidityHuntStrategy
)
from feishu_notifier import FeishuNotifier, SignalMessage
from ai_scorer import AIScorer
from technical_analyzer import get_technical_analysis
import json


@dataclass
class Signal:
    """交易信号 - 最终格式"""
    
    # === 基础信息 ===
    signal_id: str                    # 信号唯一 ID
    timestamp: str                    # 生成时间
    symbol: str                       # 交易标的
    timeframe: str                    # 时间周期
    
    # === 策略信息 ===
    strategy_name: str                # 策略名称
    strategy_category: str            # 策略类型
    
    # === 价格信息 ===
    current_price: str                # 当前价格（字符串保留完整精度）
    price_change_24h: float           # 24 小时涨跌幅
    
    # === 核心信号 ===
    action: str                       # BUY/SELL/WATCH
    direction: str                    # LONG/SHORT/NEUTRAL
    signal_type: str                  # OPEN/CLOSE/ADD
    priority: str                     # HIGH/MEDIUM/LOW
    confidence: float                 # 置信度 0-100
    
    # === 信号理由 ===
    reason: str                       # 文字说明
    pattern: str                      # 形态/信号类型
    
    # === 入场 ===
    entry_price: str                  # 建议入场价（字符串保留完整精度）
    entry_type: str                   # MARKET/LIMIT
    
    # === 风险管理 ===
    position_size_pct: float          # 建议仓位 %
    stop_loss_price: Optional[str]    # 止损价（字符串保留完整精度）
    stop_loss_pct: float              # 止损幅度 %
    take_profit_price: Optional[str]  # 目标价（字符串保留完整精度）
    take_profit_pct: float            # 目标幅度 %
    risk_reward_ratio: float          # 盈亏比
    
    # === 市场背景 ===
    trend_short: str                  # 短期趋势
    trend_medium: str                 # 中期趋势
    volatility: str                   # 波动率
    volume_status: str                # 成交量状态
    
    # === 策略表现 ===
    strategy_win_rate: float          # 策略胜率
    strategy_last_10: str             # 近 10 笔表现
    strategy_sharpe: float            # 夏普比率
    
    # === 风险提示 ===
    max_risk_amount: float            # 最大风险金额
    warnings: List[str]               # 风险警告
    
    # === AI 评分 ===
    ai_score: Optional[int] = None    # AI 评分 0-100
    ai_recommendation: Optional[str] = None  # AI 建议
    ai_reasons: Optional[List[str]] = None      # AI 分析理由
    ai_error: Optional[str] = None    # AI 错误信息
    
    # === 有效期 ===
    valid_until: str = ""             # 信号有效期
    
    # === 持仓建议 ===
    holding_period: Optional[Dict] = None  # {'min_days': 1, 'max_days': 5, 'expected_days': 3, 'type': 'swing'}
    stop_type: Optional[str] = None   # 'technical' / 'ATR' / 'liquidity_grab'
    take_profit_type: Optional[str] = None  # 'technical' / 'multiple_R'
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
    
    def to_message(self) -> str:
        """生成推送消息（中文版）"""
        # 操作翻译
        action_map = {"BUY": "买入", "SELL": "卖出", "WATCH": "观望"}
        action_cn = action_map.get(self.action, self.action)
        
        # 方向翻译
        direction_map = {"LONG": "做多", "SHORT": "做空", "NEUTRAL": "中性"}
        direction_cn = direction_map.get(self.direction, self.direction)
        
        # 信号类型翻译
        signal_type_map = {"OPEN": "开仓", "CLOSE": "平仓", "ADD": "加仓"}
        signal_type_cn = signal_type_map.get(self.signal_type, self.signal_type)
        
        # 优先级翻译和 emoji
        priority_map = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
        priority_cn = priority_map.get(self.priority, self.priority)
        priority_emoji = "🔴" if self.priority == "HIGH" else "🟡" if self.priority == "MEDIUM" else "🟢"
        
        # 方向 emoji
        direction_emoji = "📈" if self.direction == "LONG" else "📉" if self.direction == "SHORT" else "➡️"
        
        # 策略类型翻译
        strategy_category_map = {
            "Multi-Timeframe": "多周期",
            "Volatility": "波动率",
            "Money Flow": "资金流",
            "Market Structure": "市场结构",
            "Trend Following": "趋势跟踪",
            "Reversal": "反转"
        }
        strategy_category_cn = strategy_category_map.get(self.strategy_category, self.strategy_category)
        
        # 止损止盈类型翻译
        stop_type_map = {"technical": "技术位", "ATR": "波动率", "liquidity_grab": "流动性猎杀"}
        stop_type_cn = stop_type_map.get(self.stop_type, "")
        
        take_profit_type_map = {"technical": "技术位", "multiple_R": "风险倍数"}
        take_profit_type_cn = take_profit_type_map.get(self.take_profit_type, "")
        
        # 趋势翻译
        trend_map = {"BULLISH": "看涨", "BEARISH": "看跌", "NEUTRAL": "中性"}
        trend_short_cn = trend_map.get(self.trend_short, self.trend_short)
        trend_medium_cn = trend_map.get(self.trend_medium, self.trend_medium)
        
        # 波动率和成交量翻译
        volatility_map = {"HIGH": "高", "MEDIUM": "中", "LOW": "低"}
        volatility_cn = volatility_map.get(self.volatility, self.volatility)
        
        volume_map = {"HIGH": "放量", "NORMAL": "正常", "LOW": "缩量"}
        volume_cn = volume_map.get(self.volume_status, self.volume_status)
        
        # 持仓类型翻译
        holding_type_map = {"scalp": "超短线", "day": "日内", "swing": "波段", "position": "持仓"}
        
        # 转换为 float 用于格式化
        current_price_f = float(self.current_price)
        stop_loss_f = float(self.stop_loss_price) if self.stop_loss_price else 0
        take_profit_f = float(self.take_profit_price) if self.take_profit_price else 0
        
        # 构建消息
        msg = f"""
🟢【{self.strategy_name}】{self.symbol} {action_cn}

📅 时间：{self.timestamp[:16].replace('T', ' ')}
💰 价格：${current_price_f:,.2f}
📊 方向：{direction_cn} {direction_emoji}
🎯 类型：{signal_type_cn}

💡 信号理由:
{self.reason}

📐 风险管理:
├ 仓位：{self.position_size_pct}%
├ 止损：${stop_loss_f:,.2f} ({self.stop_loss_pct}%) {f"【{stop_type_cn}】" if stop_type_cn else ""}
├ 目标：${take_profit_f:,.2f} ({self.take_profit_pct}%) {f"【{take_profit_type_cn}】" if take_profit_type_cn else ""}
└ 盈亏比：{self.risk_reward_ratio}:1

⏱️ 持仓建议:
{f"├ 预期：{self.holding_period['expected_days']} 天 ({self.holding_period['min_days']}-{self.holding_period['max_days']}天)" if self.holding_period else "├ 预期：根据市场情况调整"}
└ 类型：{holding_type_map.get(self.holding_period.get('type', 'swing') if self.holding_period else 'swing', '波段')}

📈 信号质量:
├ 置信度：{self.confidence:.0f}% {priority_emoji}
├ 策略胜率：{self.strategy_win_rate:.1f}%
└ 夏普比率：{self.strategy_sharpe:.2f}

🌍 市场环境:
├ 趋势：{trend_short_cn} / {trend_medium_cn}
├ 波动率：{volatility_cn}
└ 成交量：{volume_cn}

⚠️ 风险：单笔最大亏损 ${self.max_risk_amount:,.0f}
{f"❗ 警告：{' | '.join(self.warnings)}" if self.warnings else ""}
━━━━━━━━━━━━━━━━━━━━━━
ID: {self.signal_id}
有效：{self.valid_until[:16].replace('T', ' ')}
""".strip()
        
        return msg


class SignalGenerator:
    """信号生成器"""
    
    def __init__(self, capital: float = 100000.0, risk_per_trade: float = 0.02,
                 enable_notification: bool = True):
        self.capital = capital
        self.risk_per_trade = risk_per_trade
        self.enable_notification = enable_notification
        
        # 加载通知配置
        self.notification_config = self._load_notification_config()
        
        # 初始化飞书推送
        if self.enable_notification and self.notification_config:
            webhook_url = self.notification_config.get('feishu', {}).get('webhook_url')
            if webhook_url:
                self.feishu_notifier = FeishuNotifier(webhook_url)
            else:
                self.feishu_notifier = None
        else:
            self.feishu_notifier = None
        
        self.strategies = {
            'trend_following': TrendFollowingStrategy(),
            'reversal_123': Reversal123Strategy(),
            'support_resistance': SupportResistanceStrategy(),
            'pattern': PatternTradingStrategy(),
            'ma_cross': MACrossStrategy(),
            'volatility_breakout': VolatilityBreakoutStrategy(),
            'bollinger': BollingerBandsStrategy(),
            'rsi': RSIStrategy(),
            'breakout': BreakoutStrategy(),
            'multi_timeframe': MultiTimeframeStrategy(),
            'volatility_squeeze': VolatilitySqueezeStrategy(),
            'money_flow': MoneyFlowStrategy(),
            'liquidity_hunt': LiquidityHuntStrategy()
        }
        
        self.strategy_stats = {
            'trend_following': {'win_rate': 48.6, 'sharpe': 0.30, 'last_10': '+5.2%'},
            'reversal_123': {'win_rate': 52.5, 'sharpe': 0.96, 'last_10': '+12.8%'},
            'support_resistance': {'win_rate': 55.0, 'sharpe': 0.48, 'last_10': '+3.5%'},
            'pattern': {'win_rate': 58.0, 'sharpe': 0.80, 'last_10': '+8.9%'},
            'ma_cross': {'win_rate': 52.0, 'sharpe': 0.83, 'last_10': '+7.2%'},
            'volatility_breakout': {'win_rate': 56.5, 'sharpe': 0.74, 'last_10': '+6.5%'},
            'bollinger': {'win_rate': 53.3, 'sharpe': 0.27, 'last_10': '+2.1%'},
            'rsi': {'win_rate': 54.0, 'sharpe': 0.38, 'last_10': '+4.3%'},
            'breakout': {'win_rate': 55.5, 'sharpe': 0.39, 'last_10': '+5.8%'},
            'multi_timeframe': {'win_rate': 58.0, 'sharpe': 1.05, 'last_10': '+15.3%'},
            'volatility_squeeze': {'win_rate': 55.0, 'sharpe': 1.20, 'last_10': '+18.5%'},
            'money_flow': {'win_rate': 60.0, 'sharpe': 1.15, 'last_10': '+22.1%'},
            'liquidity_hunt': {'win_rate': 57.0, 'sharpe': 1.25, 'last_10': '+19.8%'}
        }
    
    def _load_notification_config(self) -> dict:
        """加载通知配置"""
        config_path = Path('config/notification.json')
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {}
    
    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """计算 ATR"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift(1))
        low_close = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return atr if not pd.isna(atr) else df['close'].iloc[-1] * 0.02
    
    def determine_trend(self, df: pd.DataFrame) -> tuple:
        """判断趋势"""
        close = df['close'].iloc[-1]
        ma20 = df['close'].rolling(20).mean().iloc[-1]
        ma50 = df['close'].rolling(50).mean().iloc[-1]
        
        short = "BULLISH" if close > ma20 else "BEARISH"
        medium = "BULLISH" if close > ma50 else "BEARISH"
        
        return short, medium
    
    def determine_volatility(self, df: pd.DataFrame) -> str:
        """判断波动率"""
        returns = df['close'].pct_change()
        current_vol = returns.rolling(20).std().iloc[-1]
        avg_vol = returns.rolling(60).std().mean()
        
        if current_vol > avg_vol * 1.5:
            return "HIGH"
        elif current_vol < avg_vol * 0.7:
            return "LOW"
        return "MEDIUM"
    
    def determine_volume(self, df: pd.DataFrame) -> str:
        """判断成交量"""
        if 'volume' not in df.columns:
            return "N/A"
        
        current_vol = df['volume'].iloc[-1]
        avg_vol = df['volume'].rolling(20).mean().iloc[-1]
        
        if current_vol > avg_vol * 1.5:
            return "HIGH"
        elif current_vol < avg_vol * 0.7:
            return "LOW"
        return "NORMAL"
    
    def generate_signal(self, strategy_name: str, df: pd.DataFrame, 
                       signals_df: pd.DataFrame, symbol: str) -> Optional[Signal]:
        """为单个策略生成信号"""
        if len(signals_df) == 0:
            return None
        
        # 获取最新信号
        latest = signals_df.iloc[-1]
        
        if pd.isna(latest.get('position', np.nan)):
            return None
        
        current_position = int(latest.get('position', 0))
        prev_position = int(signals_df.iloc[-2].get('position', 0)) if len(signals_df) > 1 else 0
        
        # 没有仓位变化则不生成信号
        if current_position == prev_position:
            return None
        
        # 确定信号方向
        if current_position == 1:
            action = "BUY"
            direction = "LONG"
            signal_type = "OPEN"
        elif current_position == -1:
            action = "SELL"
            direction = "SHORT"
            signal_type = "OPEN"
        else:
            # 平仓信号
            if prev_position == 1:
                action = "SELL"
                direction = "NEUTRAL"
                signal_type = "CLOSE"
            elif prev_position == -1:
                action = "BUY"
                direction = "NEUTRAL"
                signal_type = "CLOSE"
            else:
                return None
        
        # 计算风险管理参数
        current_price = latest['close']
        atr = self.calculate_atr(df)
        
        # 止损和目标
        if direction == "LONG":
            stop_loss = current_price - 2 * atr
            take_profit = current_price + 3 * atr
        else:
            stop_loss = current_price + 2 * atr
            take_profit = current_price - 3 * atr
        
        stop_pct = abs(current_price - stop_loss) / current_price * 100
        take_profit_pct = abs(take_profit - current_price) / current_price * 100
        rr_ratio = take_profit_pct / stop_pct if stop_pct > 0 else 0
        
        # 仓位计算
        risk_amount = self.capital * self.risk_per_trade
        if stop_pct > 0:
            position_size = risk_amount / (current_price * stop_pct / 100)
            position_pct = (position_size * current_price) / self.capital * 100
        else:
            position_pct = 10.0
        
        position_pct = min(position_pct, 25.0)  # 最大 25% 仓位
        
        # 趋势判断
        trend_short, trend_medium = self.determine_trend(df)
        volatility = self.determine_volatility(df)
        volume_status = self.determine_volume(df)
        
        # 获取策略统计
        stats = self.strategy_stats.get(strategy_name, {})
        
        # 生成信号 ID
        signal_id = f"SIG-{datetime.now().strftime('%Y%m%d')}-{symbol.split('-')[0]}-{strategy_name.upper()[:4]}-{len(signals_df):03d}"
        
        # 获取信号理由
        pattern = latest.get('pattern', '') or latest.get('breakout_type', '') or latest.get('rsi_signal_type', '') or latest.get('bb_signal_type', '') or ''
        reason = self._generate_reason(strategy_name, action, direction, pattern, df)
        
        # 优先级和置信度
        if rr_ratio >= 2.5 and stats.get('win_rate', 50) > 50:
            priority = "HIGH"
            confidence = min(85, stats.get('win_rate', 50) + 20)
        elif rr_ratio >= 2.0:
            priority = "MEDIUM"
            confidence = min(75, stats.get('win_rate', 50) + 15)
        else:
            priority = "LOW"
            confidence = min(65, stats.get('win_rate', 50) + 10)
        
        # 警告
        warnings = []
        if volatility == "HIGH":
            warnings.append("高波动率")
        if position_pct > 20:
            warnings.append("仓位较重")
        
        signal = Signal(
            signal_id=signal_id,
            timestamp=datetime.now(BEIJING_TZ).strftime('%Y-%m-%dT%H:%M:%S'),  # 北京时间
            symbol=symbol,
            timeframe="1D",
            strategy_name=self.strategies[strategy_name].name,
            strategy_category=strategy_name,
            current_price=current_price,
            price_change_24h=df['close'].pct_change(1).iloc[-1] * 100 if len(df) > 1 else 0,
            action=action,
            direction=direction,
            signal_type=signal_type,
            priority=priority,
            confidence=confidence,
            reason=reason,
            pattern=pattern,
            entry_price=str(current_price),
            entry_type="MARKET",
            position_size_pct=round(position_pct, 1),
            stop_loss_price=str(stop_loss),
            stop_loss_pct=round(stop_pct, 2),
            take_profit_price=str(take_profit),
            take_profit_pct=round(take_profit_pct, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            trend_short=trend_short,
            trend_medium=trend_medium,
            volatility=volatility,
            volume_status=volume_status,
            strategy_win_rate=stats.get('win_rate', 50),
            strategy_last_10=stats.get('last_10', 'N/A'),
            strategy_sharpe=stats.get('sharpe', 0),
            max_risk_amount=round(self.capital * self.risk_per_trade, 0),
            warnings=warnings,
            valid_until=(datetime.now() + timedelta(days=1)).isoformat()
        )
        
        return signal
    
    def _generate_reason(self, strategy_name: str, action: str, direction: str, 
                        pattern: str, df: pd.DataFrame) -> str:
        """生成信号理由"""
        reasons = {
            'trend_following': f"趋势跟踪信号，{'做多' if direction == 'LONG' else '做空'}，突破 Donchian 通道",
            'reversal_123': f"123/2B 反转形态，{pattern or '趋势反转信号'}",
            'support_resistance': f"支撑阻力位交易，{'触及支撑' if direction == 'LONG' else '触及阻力'}",
            'pattern': f"图表形态突破，{pattern or '形态完成'}",
            'ma_cross': f"均线交叉，{'金叉' if direction == 'LONG' else '死叉'}",
            'volatility_breakout': f"波动率突破，{pattern or 'ATR 突破'}",
            'bollinger': f"布林带信号，{pattern or '带宽突破'}",
            'rsi': f"RSI 信号，{pattern or '超买超卖'}",
            'breakout': f"价格突破，{pattern or 'N 日高点突破'}"
        }
        
        return reasons.get(strategy_name, f"{strategy_name} 策略信号")
    
    def scan_all_strategies(self, df: pd.DataFrame, symbol: str, 
                           scan_last_days: int = 30) -> List[Signal]:
        """扫描所有策略生成信号"""
        signals = []
        
        for name, strategy in self.strategies.items():
            try:
                signals_df = strategy.generate_signals(df)
                
                # 扫描最近 N 天的所有信号变化
                recent_signals = self._find_recent_signals(
                    name, df, signals_df, symbol, scan_last_days
                )
                signals.extend(recent_signals)
                
            except Exception as e:
                print(f"策略 {name} 生成信号失败：{e}")
        
        # 按优先级和时间排序
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        signals.sort(key=lambda s: (
            priority_order.get(s.priority, 3),
            s.timestamp
        ), reverse=True)
        
        return signals
    
    def scan_multi_timeframe(self, symbol: str, rt=None) -> Optional[Signal]:
        """
        扫描多周期共振策略信号
        
        Args:
            symbol: 交易标的
            rt: RealtimeData 实例（可选）
        
        Returns:
            Signal 或 None
        """
        if rt is None:
            from realtime_data import RealtimeData
            rt = RealtimeData()
        
        try:
            # 获取多周期数据
            data_dict = {}
            for tf in ['1d', '4h', '1h']:
                df = rt.get_binance_klines(symbol, interval=tf, limit=200)
                if df.empty:
                    return None
                data_dict[tf.upper()] = df
            
            # 调用多周期策略
            mt_strategy = MultiTimeframeStrategy()
            signal_dict = mt_strategy.generate_signal(data_dict, symbol.replace('USDT', '-USD'))
            
            if signal_dict is None or signal_dict.get('action') == 'WAIT':
                return None
            
            # 转换为 Signal 对象
            from datetime import timedelta
            trend_short = "BULLISH" if signal_dict.get('direction') == 'LONG' else "BEARISH"
            trend_medium = trend_short
            
            signal = Signal(
                signal_id=f"MTF-{datetime.now().strftime('%Y%m%d%H')}-{symbol.split('-')[0]}",
                timestamp=datetime.now(BEIJING_TZ).strftime('%Y-%m-%dT%H:%M:%S'),
                symbol=symbol.replace('USDT', '-USD'),
                timeframe='1H',
                strategy_name=signal_dict['strategy_name'],
                strategy_category='Multi-Timeframe',
                current_price=signal_dict['current_price'],
                price_change_24h=data_dict['1D']['close'].pct_change(1).iloc[-1] * 100 if len(data_dict['1D']) > 1 else 0,
                action=signal_dict['action'],
                direction=signal_dict['direction'],
                signal_type='OPEN',
                priority='HIGH' if signal_dict['confidence'] >= 80 else 'MEDIUM',
                confidence=signal_dict['confidence'],
                reason=signal_dict['reason'],
                pattern=signal_dict['pattern'],
                entry_price=signal_dict['entry_price'],
                entry_type=signal_dict['entry_type'],
                position_size_pct=signal_dict['position_size_pct'],
                stop_loss_price=signal_dict['stop_loss_price'],
                stop_loss_pct=signal_dict['stop_loss_pct'],
                take_profit_price=signal_dict['take_profit_price'],
                take_profit_pct=signal_dict['take_profit_pct'],
                risk_reward_ratio=signal_dict['risk_reward_ratio'],
                trend_short=trend_short,
                trend_medium=trend_medium,
                volatility='MEDIUM',
                volume_status='NORMAL',
                strategy_win_rate=58.0,
                strategy_last_10='+15.3%',
                strategy_sharpe=1.05,
                max_risk_amount=self.capital * self.risk_per_trade,
                warnings=[],
                valid_until=(datetime.now() + timedelta(hours=4)).isoformat(),
                holding_period=signal_dict.get('holding_period'),
                stop_type=signal_dict.get('stop_type'),
                take_profit_type=signal_dict.get('take_profit_type')
            )
            
            return signal
            
        except Exception as e:
            print(f"多周期策略扫描失败 {symbol}: {e}")
            return None
    
    def _find_recent_signals(self, strategy_name: str, df: pd.DataFrame,
                            signals_df: pd.DataFrame, symbol: str,
                            scan_last_days: int = 30) -> List[Signal]:
        """扫描指定天数内的所有信号"""
        signals = []
        
        # 获取最近 N 天的数据
        cutoff_date = df.index[-1] - pd.Timedelta(days=scan_last_days)
        recent_mask = df.index >= cutoff_date
        
        if not recent_mask.any():
            return signals
        
        prev_position = 0
        
        for i in range(len(signals_df)):
            idx = signals_df.index[i]
            if idx < cutoff_date:
                continue
            
            row = signals_df.iloc[i]
            
            if pd.isna(row.get('position', np.nan)):
                continue
            
            current_position = int(row.get('position', 0))
            
            # 检测仓位变化
            if current_position != prev_position and current_position != 0:
                # 生成信号
                signal = self._create_signal_from_position(
                    strategy_name, df, signals_df, i, symbol,
                    current_position, prev_position
                )
                if signal:
                    # 修正时间戳为信号发生时间
                    signal.timestamp = idx.isoformat()
                    signal.valid_until = (idx + timedelta(days=1)).isoformat()
                    signal.signal_id = f"SIG-{idx.strftime('%Y%m%d')}-{symbol.split('-')[0]}-{strategy_name.upper()[:4]}-{len(signals):03d}"
                    signals.append(signal)
            
            prev_position = current_position
        
        return signals
    
    def _create_signal_from_position(self, strategy_name: str, df: pd.DataFrame,
                                     signals_df: pd.DataFrame, idx: int, 
                                     symbol: str, current_position: int,
                                     prev_position: int) -> Optional[Signal]:
        """根据仓位变化创建信号"""
        row = signals_df.iloc[idx]
        
        if current_position == 1:
            action = "BUY"
            direction = "LONG"
            signal_type = "OPEN"
        elif current_position == -1:
            action = "SELL"
            direction = "SHORT"
            signal_type = "OPEN"
        else:
            return None
        
        # 保留完整精度，转为字符串
        current_price = str(row['close'])
        
        # 交易量分析
        volume_info = ""
        volume_confirmed = False
        if 'volume' in df.columns and 'volume_ratio' in row:
            volume_ratio = row.get('volume_ratio', 1.0)
            volume_trend = row.get('volume_trend', 1.0)
            
            if pd.notna(volume_ratio):
                volume_confirmed = volume_ratio >= 1.5
                if volume_ratio >= 2.0:
                    volume_info = f"放量 {volume_ratio:.1f}倍 (强) ✅"
                elif volume_ratio >= 1.5:
                    volume_info = f"放量 {volume_ratio:.1f}倍 ✅"
                elif volume_ratio >= 1.0:
                    volume_info = f"平量 {volume_ratio:.1f}倍 ⚠️"
                else:
                    volume_info = f"缩量 {volume_ratio:.1f}倍 ❌"
        
        atr = self.calculate_atr(df)
        
        # 止损和目标
        if direction == "LONG":
            stop_loss = current_price - 2 * atr
            take_profit = current_price + 3 * atr
        else:
            stop_loss = current_price + 2 * atr
            take_profit = current_price - 3 * atr
        
        stop_pct = abs(current_price - stop_loss) / current_price * 100
        take_profit_pct = abs(take_profit - current_price) / current_price * 100
        rr_ratio = take_profit_pct / stop_pct if stop_pct > 0 else 0
        
        # 仓位
        risk_amount = self.capital * self.risk_per_trade
        if stop_pct > 0:
            position_size = risk_amount / (current_price * stop_pct / 100)
            position_pct = (position_size * current_price) / self.capital * 100
        else:
            position_pct = 10.0
        
        position_pct = min(position_pct, 25.0)
        
        # 趋势等
        trend_short, trend_medium = self.determine_trend(df)
        volatility = self.determine_volatility(df)
        volume_status = self.determine_volume(df)
        
        stats = self.strategy_stats.get(strategy_name, {})
        
        # 信号理由
        pattern = row.get('pattern', '') or row.get('breakout_type', '') or ''
        reason = self._generate_reason(strategy_name, action, direction, pattern, df)
        
        # 添加交易量信息到理由
        if volume_info:
            reason = f"{reason} | 成交量：{volume_info}"
        
        # 交易量过滤：缩量信号降低置信度
        if not volume_confirmed and volume_info:
            confidence = min(confidence, 50)  # 缩量信号置信度不超过 50%
            if priority == "HIGH":
                priority = "MEDIUM"
        
        # 优先级
        if rr_ratio >= 2.5 and stats.get('win_rate', 50) > 50:
            priority = "HIGH"
            confidence = min(85, stats.get('win_rate', 50) + 20)
        elif rr_ratio >= 2.0:
            priority = "MEDIUM"
            confidence = min(75, stats.get('win_rate', 50) + 15)
        else:
            priority = "LOW"
            confidence = min(65, stats.get('win_rate', 50) + 10)
        
        warnings = []
        if volatility == "HIGH":
            warnings.append("高波动率")
        if position_pct > 20:
            warnings.append("仓位较重")
        
        signal = Signal(
            signal_id=f"SIG-TEMP",
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            timeframe="1D",
            strategy_name=self.strategies[strategy_name].name,
            strategy_category=strategy_name,
            current_price=current_price,
            price_change_24h=df['close'].pct_change(1).iloc[idx] * 100 if idx > 0 else 0,
            action=action,
            direction=direction,
            signal_type=signal_type,
            priority=priority,
            confidence=confidence,
            reason=reason,
            pattern=str(pattern) if pattern else '',
            entry_price=str(current_price),
            entry_type="MARKET",
            position_size_pct=round(position_pct, 1),
            stop_loss_price=str(stop_loss),
            stop_loss_pct=round(stop_pct, 2),
            take_profit_price=str(take_profit),
            take_profit_pct=round(take_profit_pct, 2),
            risk_reward_ratio=round(rr_ratio, 2),
            trend_short=trend_short,
            trend_medium=trend_medium,
            volatility=volatility,
            volume_status=volume_status,
            strategy_win_rate=stats.get('win_rate', 50),
            strategy_last_10=stats.get('last_10', 'N/A'),
            strategy_sharpe=stats.get('sharpe', 0),
            max_risk_amount=round(self.capital * self.risk_per_trade, 0),
            warnings=warnings,
            valid_until=(datetime.now() + timedelta(days=1)).isoformat()
        )
        
        return signal


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='交易信号生成器')
    parser.add_argument('--symbol', type=str, default='BTC-USD', help='交易标的')
    parser.add_argument('--capital', type=float, default=100000.0, help='资金量')
    parser.add_argument('--output', type=str, default='signals', help='输出目录')
    parser.add_argument('--format', type=str, choices=['json', 'message', 'both'], 
                       default='both', help='输出格式')
    
    args = parser.parse_args()
    
    # 加载数据
    print(f"加载 {args.symbol} 数据...")
    loader = DataLoader()
    
    data_file = Path('data') / f"{args.symbol.replace('/', '_')}.csv"
    if data_file.exists():
        df = loader.load_csv(str(data_file))
    else:
        df = loader.download_yahoo(args.symbol, '2022-01-01', '2024-12-31')
    
    print(f"数据：{len(df)} 行，{df.index[0].date()} 至 {df.index[-1].date()}")
    
    # 生成信号
    generator = SignalGenerator(capital=args.capital)
    signals = generator.scan_all_strategies(df, args.symbol)
    
    # 输出
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    print(f"\n生成 {len(signals)} 个信号:\n")
    
    for signal in signals:
        print("="*80)
        
        if args.format in ['json', 'both']:
            print(f"\nJSON 格式:\n{signal.to_json()}\n")
        
        if args.format in ['message', 'both']:
            print(f"\n推送消息:\n{signal.to_message()}\n")
        
        # 保存到文件
        if args.format in ['json', 'both']:
            with open(output_dir / f"signal_{signal.signal_id}.json", 'w', encoding='utf-8') as f:
                f.write(signal.to_json())
        
        print("="*80)
    
    # 保存汇总
    if signals:
        with open(output_dir / f"signals_{timestamp}.json", 'w', encoding='utf-8') as f:
            json.dump([s.to_dict() for s in signals], f, indent=2, ensure_ascii=False)
        print(f"\n汇总已保存：{output_dir / f'signals_{timestamp}.json'}")
    
    return signals


if __name__ == '__main__':
    main()
