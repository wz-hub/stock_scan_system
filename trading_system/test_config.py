#!/usr/bin/env python3
"""
测试配置系统
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import Settings, get_config

def test_config():
    """测试配置读取"""
    print("=" * 60)
    print("测试配置系统")
    print("=" * 60)
    
    # 测试 1: 直接实例化
    print("\n1. 测试直接实例化 Settings:")
    config = Settings()
    
    # AI 配置
    print(f"   AI 启用：{config.get_bool('ai.enabled')}")
    print(f"   AI 模型：{config.get('ai.model')}")
    print(f"   AI 温度：{config.get_float('ai.temperature')}")
    print(f"   API URL: {config.get('ai.api_url')}")
    
    # 通知配置
    print(f"\n   飞书 Webhook: {config.get('notification.feishu.webhook_url')}")
    print(f"   飞书启用：{config.get_bool('notification.feishu.enabled')}")
    print(f"   发送卡片：{config.get_bool('notification.feishu.send_card')}")
    print(f"   最小置信度：{config.get_int('notification.filters.min_confidence')}")
    
    # 扫描配置
    print(f"\n   扫描模式：{config.get('scan.scan_symbols.mode')}")
    print(f"   交易量 Top N: {config.get_int('scan.scan_symbols.volume_top_n')}")
    print(f"   基础币种：{config.get_list('scan.scan_symbols.base_symbols')}")
    print(f"   工作日间隔：{config.get_int('scan.scan_settings.weekdays_interval_hours')}h")
    print(f"   资金流推送阈值：${config.get_int('scan.money_flow_settings.push_threshold_usd')}")
    
    # 测试 2: 全局配置实例
    print("\n2. 测试全局配置实例 get_config():")
    config2 = get_config()
    print(f"   AI 模型：{config2.get('ai.model')}")
    print(f"   两次获取是否相同：{config is config2}")
    
    # 测试 3: 默认值
    print("\n3. 测试默认值:")
    print(f"   不存在的键：{config.get('nonexistent.key', default='默认值')}")
    print(f"   布尔默认值：{config.get_bool('nonexistent.bool', default=True)}")
    
    print("\n" + "=" * 60)
    print("✅ 配置测试完成!")
    print("=" * 60)

if __name__ == '__main__':
    test_config()
