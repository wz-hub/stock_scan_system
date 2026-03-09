"""
回测引擎核心
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Trade:
    """交易记录"""
    entry_date: str
    entry_price: float
    exit_date: Optional[str]
    exit_price: Optional[float]
    direction: str  # 'long' or 'short'
    size: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ''


@dataclass
class Position:
    """当前持仓"""
    direction: str = ''  # '', 'long', 'short'
    entry_price: float = 0.0
    entry_date: str = ''
    size: float = 0.0


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000.0, 
                 commission: float = 0.001,
                 slippage: float = 0.0005):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.position = Position()
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.daily_returns: List[float] = []
        
    def reset(self):
        """重置引擎状态"""
        self.capital = self.initial_capital
        self.position = Position()
        self.trades = []
        self.equity_curve = [self.initial_capital]
        self.daily_returns = []
    
    def buy(self, price: float, date: str, size: Optional[float] = None, 
            reason: str = 'signal'):
        """开多/平空"""
        if self.position.direction == 'short':
            # 平空
            pnl = (self.position.entry_price - price) * self.position.size
            self.capital += pnl
            trade = Trade(
                entry_date=self.position.entry_date,
                entry_price=self.position.entry_price,
                exit_date=date,
                exit_price=price,
                direction='short',
                size=self.position.size,
                pnl=pnl,
                pnl_pct=pnl / (self.position.entry_price * self.position.size) if self.position.entry_price * self.position.size > 0 else 0,
                exit_reason=reason
            )
            self.trades.append(trade)
            self.position = Position()
        
        if self.position.direction == '':
            # 开多 - 使用固定fractional 仓位 (20%)
            if size is None:
                risk_per_trade = 0.20  # 每笔交易 20% 资金
                size = (self.capital * risk_per_trade) / price
            cost = price * size
            if cost > 0 and cost <= self.capital:
                self.capital -= cost
                self.position = Position(
                    direction='long',
                    entry_price=price,
                    entry_date=date,
                    size=size
                )
    
    def sell(self, price: float, date: str, reason: str = 'signal'):
        """平多/开空"""
        if self.position.direction == 'long':
            # 平多
            proceeds = price * self.position.size
            pnl = (price - self.position.entry_price) * self.position.size
            self.capital += proceeds
            trade = Trade(
                entry_date=self.position.entry_date,
                entry_price=self.position.entry_price,
                exit_date=date,
                exit_price=price,
                direction='long',
                size=self.position.size,
                pnl=pnl,
                pnl_pct=pnl / (self.position.entry_price * self.position.size) if self.position.entry_price * self.position.size > 0 else 0,
                exit_reason=reason
            )
            self.trades.append(trade)
            self.position = Position()
    
    def close_all(self, price: float, date: str):
        """平仓所有头寸"""
        if self.position.direction == 'long':
            self.sell(price, date, reason='end')
        elif self.position.direction == 'short':
            self.buy(price, date, reason='end')
    
    def update_equity(self, current_price: float):
        """更新权益曲线"""
        if self.position.direction == 'long':
            equity = self.capital + self.position.size * current_price
        elif self.position.direction == 'short':
            equity = self.capital + self.position.size * (self.position.entry_price - current_price)
        else:
            equity = self.capital
        self.equity_curve.append(max(0, equity))  # 权益不能为负
    
    def get_metrics(self) -> Dict:
        """计算回测指标"""
        if not self.trades:
            return {}
        
        trades_df = pd.DataFrame([
            {
                'entry_date': t.entry_date,
                'exit_date': t.exit_date,
                'direction': t.direction,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct
            }
            for t in self.trades
        ])
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] <= 0])
        
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
        avg_loss = abs(trades_df[trades_df['pnl'] <= 0]['pnl'].mean()) if losing_trades > 0 else 0
        
        profit_factor = avg_win / avg_loss if avg_loss > 0 else float('inf')
        
        total_pnl = trades_df['pnl'].sum()
        total_return = total_pnl / self.initial_capital
        
        # 最大回撤
        equity_series = pd.Series(self.equity_curve)
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # 夏普比率
        if len(self.equity_curve) > 1:
            returns = pd.Series(self.equity_curve).pct_change().dropna()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'final_equity': self.equity_curve[-1] if self.equity_curve else self.initial_capital
        }
