"""
配置管理类
支持 YAML 配置文件和环境变量覆盖
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class Settings:
    """
    配置管理类
    
    特性:
    - 从 config.yaml 读取配置
    - 支持环境变量覆盖 (格式：TRADING_<SECTION>_<KEY>)
    - 支持默认值
    - 支持嵌套配置访问
    
    使用示例:
        config = Settings()
        api_key = config.get('ai.api_key')
        webhook = config.get('notification.feishu.webhook_url')
        
        # 带默认值
        timeout = config.get('scan.scan_settings.timeout', default=30)
        
        # 类型转换
        model = config.get('ai.model', default='qwen3.5-plus')
        temperature = config.get_float('ai.temperature', default=0.3)
        enabled = config.get_bool('ai.enabled', default=True)
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，默认使用 config/config.yaml
        """
        if config_path is None:
            # 默认从当前脚本所在目录的 config 子目录读取
            config_path = Path(__file__).parent / 'config.yaml'
        
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在：{self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f) or {}
        
        # 应用环境变量覆盖
        self._apply_env_overrides()
    
    def _apply_env_overrides(self) -> None:
        """
        应用环境变量覆盖
        格式：TRADING_<SECTION>_<KEY>
        例如：TRADING_AI_API_KEY, TRADING_NOTIFICATION_FEISHU_WEBHOOK_URL
        """
        self._config = self._process_dict(self._config)
    
    def _process_dict(self, d: Dict, prefix: str = '') -> Dict:
        """递归处理字典，应用环境变量覆盖"""
        result = {}
        for key, value in d.items():
            env_key = f"TRADING_{prefix}_{key}".upper().replace('.', '_')
            
            if isinstance(value, dict):
                # 递归处理嵌套字典
                result[key] = self._process_dict(value, f"{prefix}_{key}" if prefix else key)
            else:
                # 检查环境变量
                env_value = os.environ.get(env_key)
                if env_value is not None:
                    # 尝试类型转换
                    result[key] = self._convert_value(env_value, value)
                else:
                    # 检查值中是否包含环境变量占位符 ${VAR:default}
                    if isinstance(value, str):
                        result[key] = self._resolve_env_placeholder(value)
                    else:
                        result[key] = value
        
        return result
    
    def _resolve_env_placeholder(self, value: str) -> str:
        """
        解析环境变量占位符 ${VAR:default}
        例如：${DASHSCOPE_API_KEY:sk-sp-xxx}
        """
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replacer(match):
            env_var = match.group(1)
            default = match.group(2) if match.group(2) is not None else ''
            return os.environ.get(env_var, default)
        
        return re.sub(pattern, replacer, value)
    
    def _convert_value(self, env_value: str, original_value: Any) -> Any:
        """
        根据原始值类型转换环境变量值
        
        Args:
            env_value: 环境变量字符串值
            original_value: 原始配置值（用于推断类型）
        
        Returns:
            转换后的值
        """
        if isinstance(original_value, bool):
            return env_value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(original_value, int):
            try:
                return int(env_value)
            except ValueError:
                return env_value
        elif isinstance(original_value, float):
            try:
                return float(env_value)
            except ValueError:
                return env_value
        elif isinstance(original_value, list):
            # 列表类型：支持逗号分隔或 JSON 格式
            if env_value.startswith('['):
                try:
                    import json
                    return json.loads(env_value)
                except:
                    return env_value.split(',')
            else:
                return env_value.split(',')
        else:
            return env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔 (如 'ai.api_key')
            default: 默认值
        
        Returns:
            配置值或默认值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔值配置"""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)
    
    def get_int(self, key: str, default: int = 0) -> int:
        """获取整数配置"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """获取浮点数配置"""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_dict(self, key: str, default: Optional[Dict] = None) -> Dict:
        """获取字典配置"""
        value = self.get(key, default)
        return value if isinstance(value, dict) else (default or {})
    
    def get_list(self, key: str, default: Optional[list] = None) -> list:
        """获取列表配置"""
        value = self.get(key, default)
        return value if isinstance(value, list) else (default or [])
    
    def has(self, key: str) -> bool:
        """检查配置键是否存在"""
        return self.get(key, default=object()) is not object()
    
    def all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
    
    def reload(self) -> None:
        """重新加载配置"""
        self._config = {}
        self._load_config()


# 全局配置实例
_config_instance: Optional[Settings] = None


def get_config(config_path: Optional[Path] = None) -> Settings:
    """
    获取全局配置实例
    
    Args:
        config_path: 配置文件路径（可选，首次调用时使用）
    
    Returns:
        Settings 实例
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Settings(config_path)
    return _config_instance
