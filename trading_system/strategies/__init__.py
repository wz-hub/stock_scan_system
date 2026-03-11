"""策略模块 - 精简版（5 个高质量策略）"""
from .base import BaseStrategy
from .multi_timeframe import MultiTimeframeStrategy
from .volatility_squeeze import VolatilitySqueezeStrategy
from .money_flow import MoneyFlowStrategy
from .liquidity_hunt import LiquidityHuntStrategy
from .flag_pattern import FlagPatternStrategy, get_flag_strategy, generate_flag_signal

__all__ = [
    'BaseStrategy',
    'MultiTimeframeStrategy',
    'VolatilitySqueezeStrategy',
    'MoneyFlowStrategy',
    'LiquidityHuntStrategy',
    'FlagPatternStrategy',
    'get_flag_strategy',
    'generate_flag_signal'
]
