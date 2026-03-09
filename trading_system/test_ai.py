"""
快速测试 AI 评分功能
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from ai_scorer import AIScorer
from technical_analyzer import TechnicalAnalyzer
from backtest.data_loader import DataLoader

# 测试 AI 配置
print("🤖 AI 评分器测试")
scorer = AIScorer()
print(f"状态：{'✅ 已启用' if scorer.enabled else '❌ 未启用'}")
print(f"模型：{scorer.model}")
print(f"API: {scorer.api_url[:50] if scorer.api_url else '未配置'}...")

# 测试技术分析
print("\n📊 技术分析测试")
loader = DataLoader()
df = loader.load_csv('data/BTC-USD.csv')

analyzer = TechnicalAnalyzer(df)
analysis = analyzer.get_full_analysis('BTC-USD')

print("\n技术指标:")
for key, value in analysis.get('indicators', {}).items():
    print(f"  {key}: {value}")

print("\n支撑阻力:")
sr = analysis.get('support_resistance', {})
print(f"  支撑：{sr.get('supports', [])}")
print(f"  阻力：{sr.get('resistances', [])}")

# 测试 AI 评分
if scorer.enabled and scorer.api_key:
    print("\n🧪 AI 评分测试...")
    
    test_signal = {
        "strategy_name": "均线交叉",
        "symbol": "BTC-USD",
        "action": "BUY",
        "direction": "LONG",
        "current_price": df.iloc[-1]['close'],
        "entry_price": df.iloc[-1]['close'],
        "stop_loss_price": df.iloc[-1]['close'] * 0.95,
        "stop_loss_pct": 5.0,
        "take_profit_price": df.iloc[-1]['close'] * 1.10,
        "take_profit_pct": 10.0,
        "risk_reward_ratio": 2.0,
        "position_size_pct": 15.0,
        "timestamp": "2024-03-08T15:00:00",
        "indicators": analysis.get('indicators', {}),
        "timeframe_analysis": analysis.get('timeframe_analysis', {}),
        "support_resistance": analysis.get('support_resistance', {}),
        "volume_analysis": analysis.get('volume_analysis', {}),
        "strategy_win_rate": 52.0,
        "strategy_last_10": "+5.2%",
        "strategy_sharpe": 0.83,
        "trend_short": "BULLISH",
        "trend_medium": "BULLISH",
        "volatility": "MEDIUM"
    }
    
    result = scorer.analyze(test_signal)
    
    if result and 'error' not in result:
        print(f"\n✅ AI 评分：{result.get('score')}/100")
        print(f"📊 建议：{result.get('recommendation')}")
        print(f"💡 理由:")
        for reason in result.get('reasons', []):
            print(f"  - {reason}")
    else:
        print(f"\n❌ AI 分析失败：{result}")
else:
    print("\n⚠️ AI 未启用，请先在 Web 页面配置 API Key")
