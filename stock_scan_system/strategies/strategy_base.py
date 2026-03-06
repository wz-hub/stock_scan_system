# -*- coding: utf-8 -*-
"""
策略基类

所有加密货币策略的父类
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
import pandas as pd


class BaseStrategy(ABC):
    """策略基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """策略描述"""
        pass
    
    @abstractmethod
    def scan(self, history: pd.DataFrame, current: Dict) -> Optional[Dict[str, Any]]:
        """
        扫描交易信号
        
        Args:
            history: 历史数据
            current: 当前数据
            
        Returns:
            信号字典或 None
        """
        pass
    
    def get_params(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {}
    
    def set_params(self, params: Dict[str, Any]):
        """设置策略参数"""
        pass
