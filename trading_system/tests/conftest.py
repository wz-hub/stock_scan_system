"""
Pytest 配置文件
提供共享的 fixtures 和配置
"""
import pytest
import sys
from pathlib import Path
import tempfile
import os

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope='session')
def test_data_dir():
    """创建测试数据目录"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_kline_data():
    """提供示例 K 线数据"""
    import pandas as pd
    import numpy as np
    
    np.random.seed(42)
    rows = 500
    
    returns = np.random.randn(rows) * 0.02
    prices = 50000 * np.cumprod(1 + returns)
    
    return pd.DataFrame({
        'open': prices * (1 + np.random.randn(rows) * 0.005),
        'high': prices * (1 + np.abs(np.random.randn(rows) * 0.01)),
        'low': prices * (1 - np.abs(np.random.randn(rows) * 0.01)),
        'close': prices,
        'volume': np.random.randint(1000, 10000, rows)
    })


@pytest.fixture
def sample_signal_data():
    """提供示例信号数据"""
    return {
        'signal_id': 'test_signal_001',
        'symbol': 'BTC-USD',
        'strategy_name': 'Multi-Timeframe Resonance',
        'action': 'BUY',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'stop_loss_price': 49000.0,
        'take_profit_price': 52000.0,
        'confidence': 75.0,
        'timestamp': '2026-03-10T00:00:00'
    }


@pytest.fixture(autouse=True)
def setup_test_environment(tmp_path):
    """为每个测试设置环境"""
    # 设置测试缓存目录
    original_cwd = os.getcwd()
    os.chdir(tmp_path)
    
    yield
    
    os.chdir(original_cwd)


def pytest_configure(config):
    """Pytest 配置"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
