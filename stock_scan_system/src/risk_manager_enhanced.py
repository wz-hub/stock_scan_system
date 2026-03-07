# -*- coding: utf-8 -*-
"""
增强版风险管理系统

功能：
- 动态仓位管理（凯利公式）
- ATR 动态止损
- 相关性分析
- 风险预警
- 最大回撤控制
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PositionConfig:
    """仓位配置"""
    total_capital: float
    max_position_pct: float = 0.25  # 单标的最大仓位 25%
    max_total_position: float = 0.95  # 最大总仓位 95%
    risk_per_trade: float = 0.02  # 单笔交易风险 2%


class EnhancedRiskManager:
    """增强版风险管理器"""
    
    def __init__(self, config: PositionConfig):
        """
        初始化风险管理器
        
        Args:
            config: 仓位配置
        """
        self.config = config
        self.positions: Dict[str, Dict] = {}  # 当前持仓
        self.trade_history: List[Dict] = []
    
    def calculate_position_size(self, symbol: str, entry_price: float, 
                                 stop_loss: float, current_capital: float) -> int:
        """
        计算仓位大小（基于风险）
        
        Args:
            symbol: 股票代码
            entry_price: 入场价
            stop_loss: 止损价
            current_capital: 当前资金
            
        Returns:
            建议股数
        """
        # 计算每股风险
        risk_per_share = entry_price - stop_loss
        if risk_per_share <= 0:
            logger.warning(f"Invalid stop loss for {symbol}")
            return 0
        
        # 凯利公式计算最优仓位
        win_rate = self._estimate_win_rate(symbol)
        profit_ratio = self._estimate_profit_ratio(symbol)
        
        kelly_pct = self._kelly_criterion(win_rate, profit_ratio)
        kelly_pct = min(kelly_pct, self.config.max_position_pct)  # 限制最大仓位
        
        # 基于风险计算仓位
        risk_amount = current_capital * self.config.risk_per_trade
        shares_by_risk = int(risk_amount / risk_per_share)
        
        # 基于凯利计算仓位
        shares_by_kelly = int((current_capital * kelly_pct) / entry_price)
        
        # 取较小值
        shares = min(shares_by_risk, shares_by_kelly)
        
        # 检查总仓位限制
        current_total_position = self._get_total_position_value(current_capital)
        max_allowed = current_capital * self.config.max_total_position - current_total_position
        
        if shares * entry_price > max_allowed:
            shares = int(max_allowed / entry_price)
        
        logger.info(f"{symbol}: position={shares} shares, kelly={kelly_pct:.2%}, risk={shares_by_risk} shares")
        return max(0, shares)
    
    def _kelly_criterion(self, win_rate: float, profit_ratio: float) -> float:
        """
        凯利公式
        
        Args:
            win_rate: 胜率
            profit_ratio: 盈亏比
            
        Returns:
            最优仓位比例
        """
        # f* = p - q/b
        # p = 胜率，q = 1-p, b = 盈亏比
        p = win_rate
        q = 1 - p
        b = profit_ratio
        
        kelly = p - q / b if b > 0 else 0
        
        # 半凯利（降低风险）
        return kelly / 2
    
    def _estimate_win_rate(self, symbol: str) -> float:
        """估算胜率（基于历史交易）"""
        symbol_trades = [t for t in self.trade_history if t.get('symbol') == symbol]
        
        if len(symbol_trades) == 0:
            return 0.55  # 默认 55%
        
        winning_trades = sum(1 for t in symbol_trades if t.get('profit', 0) > 0)
        return winning_trades / len(symbol_trades)
    
    def _estimate_profit_ratio(self, symbol: str) -> float:
        """估算盈亏比"""
        symbol_trades = [t for t in self.trade_history if t.get('symbol') == symbol]
        
        if len(symbol_trades) == 0:
            return 2.0  # 默认 2:1
        
        wins = [t['profit'] for t in symbol_trades if t['profit'] > 0]
        losses = [abs(t['profit']) for t in symbol_trades if t['profit'] < 0]
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 1
        
        return avg_win / avg_loss if avg_loss > 0 else 2.0
    
    def _get_total_position_value(self, current_capital: float) -> float:
        """计算当前总持仓价值"""
        total = 0
        for symbol, pos in self.positions.items():
            total += pos.get('shares', 0) * pos.get('current_price', 0)
        return total
    
    def calculate_stop_loss(self, symbol: str, entry_price: float, 
                            atr: Optional[float] = None, method: str = 'atr') -> float:
        """
        计算止损价
        
        Args:
            symbol: 股票代码
            entry_price: 入场价
            atr: ATR 值（可选）
            method: 方法（'atr'/'percent'/'support'）
            
        Returns:
            止损价
        """
        if method == 'atr':
            # ATR 动态止损
            if atr is None:
                atr = self._calculate_atr(symbol)
            stop_loss = entry_price - 2 * atr
        elif method == 'percent':
            # 固定百分比止损
            stop_loss = entry_price * 0.95
        elif method == 'support':
            # 支撑位止损
            stop_loss = self._find_support_level(symbol)
        else:
            stop_loss = entry_price * 0.95
        
        return round(stop_loss, 2)
    
    def _calculate_atr(self, symbol: str, period: int = 14) -> float:
        """计算 ATR（平均真实波幅）"""
        # 简化实现，实际应该从历史数据计算
        # 这里返回一个估计值
        return 1.0
    
    def _find_support_level(self, symbol: str) -> float:
        """查找支撑位"""
        # 简化实现
        return 0
    
    def add_position(self, symbol: str, shares: int, entry_price: float, 
                     stop_loss: float, target_price: float):
        """
        添加持仓记录
        
        Args:
            symbol: 股票代码
            shares: 股数
            entry_price: 入场价
            stop_loss: 止损价
            target_price: 目标价
        """
        self.positions[symbol] = {
            'shares': shares,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'target_price': target_price,
            'current_price': entry_price,
            'pnl': 0,
            'pnl_pct': 0,
            'opened_at': pd.Timestamp.now(),
        }
        logger.info(f"Position opened: {symbol} x{shares} @ ¥{entry_price}")
    
    def update_position(self, symbol: str, current_price: float):
        """
        更新持仓
        
        Args:
            symbol: 股票代码
            current_price: 当前价
        """
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        shares = pos['shares']
        entry_price = pos['entry_price']
        
        # 计算盈亏
        pnl = (current_price - entry_price) * shares
        pnl_pct = (current_price - entry_price) / entry_price * 100
        
        pos['current_price'] = current_price
        pos['pnl'] = pnl
        pos['pnl_pct'] = pnl_pct
        
        # 检查止损/止盈
        if current_price <= pos['stop_loss']:
            logger.warning(f"Stop loss triggered for {symbol}")
        if current_price >= pos['target_price']:
            logger.info(f"Target reached for {symbol}")
    
    def close_position(self, symbol: str, exit_price: float) -> float:
        """
        平仓
        
        Args:
            symbol: 股票代码
            exit_price: 出场价
            
        Returns:
            盈亏
        """
        if symbol not in self.positions:
            return 0
        
        pos = self.positions[symbol]
        pnl = (exit_price - pos['entry_price']) * pos['shares']
        
        # 记录交易历史
        self.trade_history.append({
            'symbol': symbol,
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'shares': pos['shares'],
            'profit': pnl,
            'opened_at': pos['opened_at'],
            'closed_at': pd.Timestamp.now(),
        })
        
        # 删除持仓
        del self.positions[symbol]
        
        logger.info(f"Position closed: {symbol} PnL=¥{pnl:.2f}")
        return pnl
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """
        获取风险指标
        
        Returns:
            风险指标字典
        """
        if not self.trade_history:
            return {}
        
        profits = [t['profit'] for t in self.trade_history]
        
        # 计算指标
        total_pnl = sum(profits)
        avg_win = np.mean([p for p in profits if p > 0]) if any(p > 0 for p in profits) else 0
        avg_loss = np.mean([p for p in profits if p < 0]) if any(p < 0 for p in profits) else 0
        
        win_rate = sum(1 for p in profits if p > 0) / len(profits) if profits else 0
        profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # 最大回撤
        max_drawdown = self._calculate_max_drawdown()
        
        return {
            'total_pnl': total_pnl,
            'total_trades': len(self.trade_history),
            'win_rate': win_rate * 100,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': abs(avg_loss),
            'max_drawdown': max_drawdown,
            'current_positions': len(self.positions),
        }
    
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.trade_history:
            return 0
        
        # 计算累计盈亏曲线
        cumulative = []
        total = 0
        for trade in self.trade_history:
            total += trade['profit']
            cumulative.append(total)
        
        # 计算回撤
        peak = cumulative[0]
        max_dd = 0
        
        for value in cumulative:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        
        return max_dd * 100
    
    def check_portfolio_risk(self) -> List[str]:
        """
        检查组合风险
        
        Returns:
            风险预警列表
        """
        warnings = []
        
        # 检查仓位集中度
        total_value = sum(p['shares'] * p['current_price'] for p in self.positions.values())
        
        for symbol, pos in self.positions.items():
            position_value = pos['shares'] * pos['current_price']
            if total_value > 0:
                position_pct = position_value / total_value
                if position_pct > 0.5:
                    warnings.append(f"⚠️ {symbol} 仓位过重 ({position_pct:.1%})")
        
        # 检查止损
        for symbol, pos in self.positions.items():
            if pos['current_price'] <= pos['stop_loss'] * 1.01:
                warnings.append(f"🚨 {symbol} 触及止损线")
        
        return warnings


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    config = PositionConfig(total_capital=100000)
    risk_manager = EnhancedRiskManager(config)
    
    # 测试仓位计算
    shares = risk_manager.calculate_position_size('601138', 28.5, 27.0, 100000)
    print(f"Suggested position: {shares} shares")
    
    # 添加持仓
    risk_manager.add_position('601138', shares, 28.5, 27.0, 31.0)
    
    # 更新价格
    risk_manager.update_position('601138', 29.0)
    
    # 查看风险指标
    metrics = risk_manager.get_risk_metrics()
    print(f"Risk metrics: {metrics}")
