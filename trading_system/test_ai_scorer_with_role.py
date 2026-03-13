#!/usr/bin/env python3
"""
AI 评分模块测试（带角色设定）

测试新的角色设定 + 优化后的 Prompt 格式
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ai_scorer import AIScorer
from datetime import datetime


def test_ai_scorer_with_role():
    """测试带角色设定的 AI 评分"""
    
    print("=" * 80)
    print("🤖 AI 评分测试 - 带角色设定")
    print("=" * 80)
    
    # 测试信号
    test_signal = {
        'symbol': 'TURBOUSDT',
        'entry_price': 0.001221,
        'timeframe': '4H'
    }
    
    # 测试市场数据（简化的测试数据）
    from datetime import timedelta
    base_date = datetime(2026, 2, 15)
    
    test_market_data = {
        'klines_1d': [
            {'timestamp': int((base_date + timedelta(days=i)).timestamp() * 1000), 
             'open': 0.00115 + i * 0.00001, 'high': 0.00118 + i * 0.00001,
             'low': 0.00114 + i * 0.00001, 'close': 0.00117 + i * 0.00001,
             'volume': 120000000 + i * 10000000}
            for i in range(30)
        ],
        'klines_4h': [
            {'timestamp': int((base_date + timedelta(hours=h*4)).timestamp() * 1000),
             'open': 0.00118 + h * 0.000005, 'high': 0.001195 + h * 0.000005,
             'low': 0.001175 + h * 0.000005, 'close': 0.00119 + h * 0.000005,
             'volume': 15000000 + h * 1000000}
            for h in range(50)
        ],
        'klines_1h': [
            {'timestamp': int((base_date + timedelta(hours=h)).timestamp() * 1000),
             'open': 0.00119 + h * 0.000002, 'high': 0.001205 + h * 0.000002,
             'low': 0.001185 + h * 0.000002, 'close': 0.0012 + h * 0.000002,
             'volume': 18000000 + h * 500000}
            for h in range(100)
        ],
        'adx': 25.0,
        'rsi': 60.0,
        'macd_status': '金叉',
        'macd_histogram': 0.000125,
        'atr': 0.00005,
        'bb_position': 0.95,
        'volume_ratio': 1.5,
        'oi_change_pct': 0.0
    }
    
    scorer = AIScorer()
    
    print(f"\n📊 测试信号:")
    print(f"   Symbol: {test_signal['symbol']}")
    print(f"   Price: {test_signal['entry_price']}")
    print(f"   Timeframe: {test_signal['timeframe']}")
    
    print(f"\n📈 市场数据:")
    print(f"   1D K 线：{len(test_market_data['klines_1d'])} 根")
    print(f"   4H K 线：{len(test_market_data['klines_4h'])} 根")
    print(f"   1H K 线：{len(test_market_data['klines_1h'])} 根")
    print(f"   ADX: {test_market_data['adx']}")
    print(f"   RSI: {test_market_data['rsi']}")
    print(f"   MACD: {test_market_data['macd_status']}")
    
    print(f"\n🤖 调用 AI 评分...")
    print("=" * 80)
    
    # 实际调用 AI
    result = scorer.score(test_signal, test_market_data)
    
    if result:
        print(f"\n✅ AI 评分成功!")
        print(f"   方向：{result['direction']}")
        print(f"   把握：{result['confidence']}%")
        print(f"   理由：{result['reason']}")
    else:
        print(f"\n❌ AI 评分失败或返回空")
    
    print("=" * 80)
    
    # 估算 Token
    prompt = scorer._build_prompt(test_signal, test_market_data)
    estimated_tokens = len(prompt) // 4  # 粗略估算
    
    print(f"\n📊 Token 估算:")
    print(f"   Prompt 字符数：{len(prompt):,}")
    print(f"   估算 Token 数：~{estimated_tokens:,}")
    print(f"   单次成本：${estimated_tokens * 0.14 / 1_000_000:.6f}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成!")
    print("=" * 80)
    
    return result


if __name__ == '__main__':
    test_ai_scorer_with_role()
