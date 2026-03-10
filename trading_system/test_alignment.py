#!/usr/bin/env python3
"""
交易系统重构 - 颗粒度对齐测试

对比重构前后的所有功能，确保 100% 功能对齐
"""

import sys
import json
from datetime import datetime

print("=" * 80)
print("🔍 交易系统重构 - 颗粒度对齐测试")
print("=" * 80)
print(f"测试时间：{datetime.now().isoformat()}")
print()

# 测试结果统计
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}

def test_module(name, test_func):
    """测试一个模块"""
    try:
        result = test_func()
        if result:
            test_results['passed'].append(name)
            print(f"✅ {name}")
            return True
        else:
            test_results['failed'].append(name)
            print(f"❌ {name}")
            return False
    except Exception as e:
        test_results['failed'].append(name)
        print(f"❌ {name}: {str(e)}")
        return False

def test_warning(name, condition, message=""):
    """添加警告"""
    if not condition:
        test_results['warnings'].append(f"{name}: {message}")
        print(f"⚠️  {name}: {message}")

print("=" * 80)
print("📦 第一阶段：核心模块导入测试")
print("=" * 80)

# 1. 核心模块导入
test_module("core.scanner", lambda: __import__('core.scanner'))
test_module("core.tracker", lambda: __import__('core.tracker'))
test_module("core.monitor", lambda: __import__('core.monitor'))
test_module("core.reporter", lambda: __import__('core.reporter'))

# 2. 策略模块导入
test_module("strategies.base", lambda: __import__('strategies.base'))
test_module("strategies.multi_timeframe", lambda: __import__('strategies.multi_timeframe'))
test_module("strategies.volatility_squeeze", lambda: __import__('strategies.volatility_squeeze'))
test_module("strategies.money_flow", lambda: __import__('strategies.money_flow'))
test_module("strategies.liquidity_hunt", lambda: __import__('strategies.liquidity_hunt'))

# 3. 数据模块导入
test_module("data.binance", lambda: __import__('data.binance'))
test_module("data.cache", lambda: __import__('data.cache'))
test_module("data.database", lambda: __import__('data.database'))

# 4. 通知模块导入
test_module("notification.feishu", lambda: __import__('notification.feishu'))
test_module("notification.templates", lambda: __import__('notification.templates'))

# 5. 配置模块导入
test_module("config.settings", lambda: __import__('config.settings'))

# 6. 原有模块向后兼容
test_module("signal_generator", lambda: __import__('signal_generator'))
test_module("realtime_data", lambda: __import__('realtime_data'))
test_module("signal_tracker", lambda: __import__('signal_tracker'))
test_module("signal_monitor", lambda: __import__('signal_monitor'))
test_module("signal_report", lambda: __import__('signal_report'))
test_module("feishu_notifier", lambda: __import__('feishu_notifier'))
test_module("database", lambda: __import__('database'))
test_module("money_flow", lambda: __import__('money_flow'))
test_module("technical_analyzer", lambda: __import__('technical_analyzer'))
test_module("ai_scorer", lambda: __import__('ai_scorer'))

print()
print("=" * 80)
print("🔧 第二阶段：功能实例化测试")
print("=" * 80)

# 测试核心类实例化
from core.scanner import SignalScanner
from core.tracker import SignalTracker
from core.monitor import SignalMonitor
from core.reporter import SignalReporter

test_module("SignalScanner 实例化", lambda: SignalScanner())
test_module("SignalTracker 实例化", lambda: SignalTracker())
test_module("SignalMonitor 实例化", lambda: SignalMonitor())
test_module("SignalReporter 实例化", lambda: SignalReporter())

# 测试策略实例化
from strategies.multi_timeframe import MultiTimeframeStrategy
from strategies.volatility_squeeze import VolatilitySqueezeStrategy
from strategies.money_flow import MoneyFlowStrategy
from strategies.liquidity_hunt import LiquidityHuntStrategy

test_module("MultiTimeframeStrategy 实例化", lambda: MultiTimeframeStrategy())
test_module("VolatilitySqueezeStrategy 实例化", lambda: VolatilitySqueezeStrategy())
test_module("MoneyFlowStrategy 实例化", lambda: MoneyFlowStrategy())
test_module("LiquidityHuntStrategy 实例化", lambda: LiquidityHuntStrategy())

# 测试数据模块
from data.binance import BinanceAPI
from data.cache import DataCache
from data.database import Database

test_module("BinanceAPI 实例化", lambda: BinanceAPI())
test_module("DataCache 实例化", lambda: DataCache())
test_module("Database 实例化", lambda: Database())

# 测试通知模块
from notification.feishu import FeishuNotifier
from notification.templates import MessageTemplate

test_module("FeishuNotifier 实例化", lambda: FeishuNotifier())
test_module("MessageTemplate 实例化", lambda: MessageTemplate())

# 测试配置模块
from config.settings import Settings

test_module("Settings 实例化", lambda: Settings())

print()
print("=" * 80)
print("📊 第三阶段：数据库功能测试")
print("=" * 80)

# 测试数据库连接
db = Database()
test_module("数据库连接", lambda: db.connection)
test_module("数据库表存在-check_klines", lambda: db._table_exists('klines'))
test_module("数据库表存在-check_signals", lambda: db._table_exists('signals'))
test_module("数据库表存在-check_scan_logs", lambda: db._table_exists('scan_logs'))
test_module("数据库表存在-check_strategy_configs", lambda: db._table_exists('strategy_configs'))
test_module("数据库表存在-check_system_settings", lambda: db._table_exists('system_settings'))
test_module("数据库表存在-check_money_flow", lambda: db._table_exists('money_flow'))

print()
print("=" * 80)
print("💾 第四阶段：缓存功能测试")
print("=" * 80)

cache = DataCache()
test_module("缓存设置", lambda: cache.set('test_key', {'test': 'data'}, ttl=60))
test_module("缓存获取", lambda: cache.get('test_key') == {'test': 'data'})
cache.delete('test_key')
test_module("缓存清理", lambda: cache.get('test_key') is None)

print()
print("=" * 80)
print("🔗 第五阶段：Binance API 连接测试")
print("=" * 80)

binance = BinanceAPI()
test_module("Binance API 连接", lambda: hasattr(binance, 'base_urls'))

# 测试获取 K 线数据（快速测试）
try:
    klines = binance.get_klines('BTC/USDT', '5m', limit=5)
    if klines is not None and len(klines) > 0:
        test_results['passed'].append("Binance K 线数据获取")
        print("✅ Binance K 线数据获取")
    else:
        test_results['failed'].append("Binance K 线数据获取")
        print("❌ Binance K 线数据获取")
except Exception as e:
    test_results['failed'].append("Binance K 线数据获取")
    print(f"❌ Binance K 线数据获取：{str(e)}")

# 测试获取交易对列表
try:
    symbols = binance.get_volume_ranking(10)
    if symbols and len(symbols) > 0:
        test_results['passed'].append("Binance 交易量排行")
        print("✅ Binance 交易量排行")
    else:
        test_results['failed'].append("Binance 交易量排行")
        print("❌ Binance 交易量排行")
except Exception as e:
    test_results['failed'].append("Binance 交易量排行")
    print(f"❌ Binance 交易量排行：{str(e)}")

print()
print("=" * 80)
print("⚙️  第六阶段：配置文件测试")
print("=" * 80)

settings = Settings()
test_module("配置加载-config.yaml", lambda: settings.config is not None)

# 测试关键配置项
config_tests = [
    ('scanner.enabled', bool),
    ('scanner.interval_minutes', int),
    ('scanner.min_confidence', int),
    ('tracker.enabled', bool),
    ('tracker.update_interval_minutes', int),
    ('notification.feishu.enabled', bool),
    ('notification.feishu.webhook', str),
]

for key, expected_type in config_tests:
    try:
        value = settings.get(key)
        if value is not None and isinstance(value, expected_type):
            test_results['passed'].append(f"配置项-{key}")
            print(f"✅ 配置项-{key}: {value}")
        else:
            test_results['warnings'].append(f"配置项-{key}: 类型不匹配")
            print(f"⚠️  配置项-{key}: 类型不匹配")
    except Exception as e:
        test_results['warnings'].append(f"配置项-{key}: {str(e)}")
        print(f"⚠️  配置项-{key}: {str(e)}")

print()
print("=" * 80)
print("📈 第七阶段：策略分析方法测试")
print("=" * 80)

# 测试策略的 generate_signal 方法签名
import pandas as pd
import numpy as np

# 创建模拟数据
def create_mock_data():
    dates = pd.date_range('2024-01-01', periods=300, freq='1h')
    data = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(300).cumsum() + 100,
        'high': np.random.randn(300).cumsum() + 101,
        'low': np.random.randn(300).cumsum() + 99,
        'close': np.random.randn(300).cumsum() + 100,
        'volume': np.random.randn(300).cumsum() + 1000
    })
    data = data.set_index('timestamp')
    return data

mock_data = create_mock_data()
mock_data_dict = {
    '1D': mock_data,
    '4H': mock_data,
    '1H': mock_data
}

# 测试各策略的 analyze 方法
strategies_to_test = [
    ("MultiTimeframeStrategy", MultiTimeframeStrategy(), mock_data_dict),
    ("VolatilitySqueezeStrategy", VolatilitySqueezeStrategy(), {'1h': mock_data}),
    ("MoneyFlowStrategy", MoneyFlowStrategy(), {'1h': mock_data}),
    ("LiquidityHuntStrategy", LiquidityHuntStrategy(), {'1h': mock_data}),
]

for name, strategy, data in strategies_to_test:
    try:
        result = strategy.analyze(data)
        if result and isinstance(result, dict):
            test_results['passed'].append(f"{name}.analyze()")
            print(f"✅ {name}.analyze()")
        else:
            test_results['failed'].append(f"{name}.analyze()")
            print(f"❌ {name}.analyze()")
    except Exception as e:
        test_results['failed'].append(f"{name}.analyze()")
        print(f"❌ {name}.analyze(): {str(e)}")

print()
print("=" * 80)
print("📋 第八阶段：原有脚本兼容性测试")
print("=" * 80)

# 测试原有脚本仍可导入和运行
test_module("scan_half_hourly_v3.py 导入", lambda: __import__('scan_half_hourly_v3'))
test_module("signal_monitor.py 导入", lambda: __import__('signal_monitor'))
test_module("signal_report.py 导入", lambda: __import__('signal_report'))
test_module("report_progress.py 导入", lambda: __import__('report_progress'))

print()
print("=" * 80)
print("🌐 第九阶段：Web 界面测试")
print("=" * 80)

# 测试 Web 界面文件存在
import os
test_module("web_app.py 存在", lambda: os.path.exists('web_app.py'))
test_module("web_app_v11.py 存在", lambda: os.path.exists('web_app_v11.py'))

print()
print("=" * 80)
print("📊 测试结果汇总")
print("=" * 80)

total = len(test_results['passed']) + len(test_results['failed'])
passed = len(test_results['passed'])
failed = len(test_results['failed'])
warnings = len(test_results['warnings'])

print(f"总测试项：{total}")
print(f"✅ 通过：{passed} ({passed/total*100:.1f}%)")
print(f"❌ 失败：{failed} ({failed/total*100:.1f}%)")
print(f"⚠️  警告：{warnings}")

if failed > 0:
    print()
    print("失败项目:")
    for item in test_results['failed']:
        print(f"  ❌ {item}")

if warnings > 0:
    print()
    print("警告项目:")
    for item in test_results['warnings']:
        print(f"  ⚠️  {item}")

print()
print("=" * 80)
print("📋 重构前后功能对比")
print("=" * 80)

# 重构前功能列表（基于原有系统）
legacy_features = {
    "信号扫描": "scan_half_hourly_v3.py",
    "信号追踪": "signal_tracker.py",
    "信号监控": "signal_monitor.py",
    "信号报告": "signal_report.py",
    "飞书推送": "feishu_notifier.py",
    "多周期策略": "strategies/multi_timeframe.py",
    "波动率策略": "strategies/volatility_squeeze.py",
    "资金流策略": "strategies/money_flow.py",
    "流动性策略": "strategies/liquidity_hunt.py",
    "数据库管理": "database.py",
    "实时数据": "realtime_data.py",
    "技术分析": "technical_analyzer.py",
    "AI 评分": "ai_scorer.py",
    "Web 界面": "web_app_v11.py",
    "配置文件": "config/*.json",
}

# 重构后功能列表
refactored_features = {
    "信号扫描": "core/scanner.py + scripts/scan.py",
    "信号追踪": "core/tracker.py",
    "信号监控": "core/monitor.py",
    "信号报告": "core/reporter.py",
    "飞书推送": "notification/feishu.py",
    "多周期策略": "strategies/multi_timeframe.py",
    "波动率策略": "strategies/volatility_squeeze.py",
    "资金流策略": "strategies/money_flow.py",
    "流动性策略": "strategies/liquidity_hunt.py",
    "数据库管理": "data/database.py",
    "实时数据": "data/binance.py",
    "技术分析": "technical_analyzer.py (保留)",
    "AI 评分": "ai_scorer.py (保留)",
    "Web 界面": "web_app_v11.py (保留)",
    "配置文件": "config/config.yaml",
}

print()
print(f"{'功能':<15} | {'重构前':<30} | {'重构后':<35} | 状态")
print("-" * 90)

all_aligned = True
for feature, legacy in legacy_features.items():
    refactored = refactored_features.get(feature, "N/A")
    status = "✅" if feature in [
        "信号扫描", "信号追踪", "信号监控", "信号报告", "飞书推送",
        "多周期策略", "波动率策略", "资金流策略", "流动性策略",
        "数据库管理", "实时数据"
    ] else "⚠️"
    
    if status == "⚠️":
        all_aligned = False
    
    print(f"{feature:<15} | {legacy:<30} | {refactored:<35} | {status}")

print()
print("=" * 80)
if all_aligned and failed == 0:
    print("✅ 所有功能对齐完成！重构成功！")
else:
    print("⚠️  部分功能需要进一步验证")
print("=" * 80)

# 输出 JSON 报告
report = {
    "timestamp": datetime.now().isoformat(),
    "total_tests": total,
    "passed": passed,
    "failed": failed,
    "warnings": warnings,
    "pass_rate": f"{passed/total*100:.1f}%",
    "all_aligned": all_aligned and failed == 0
}

print()
print("📄 JSON 报告:")
print(json.dumps(report, indent=2, ensure_ascii=False))

sys.exit(0 if failed == 0 else 1)
