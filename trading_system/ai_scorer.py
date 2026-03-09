"""
AI 信号评分模块
使用大模型分析信号质量
"""
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class AIScorer:
    """AI 信号评分器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._load_config()
        self.api_url = self.config.get('api_url', '')
        self.api_key = self.config.get('api_key', '')
        self.model = self.config.get('model', 'qwen-plus')
        self.enabled = self.config.get('enabled', False)
    
    def _load_config(self) -> Dict:
        """加载配置"""
        config_file = Path('config/ai_config.json')
        if config_file.exists():
            with open(config_file) as f:
                return json.load(f)
        
        # 默认配置 - 通义千问
        return {
            "enabled": False,
            "provider": "dashscope",  # dashscope/deepseek/openai
            "api_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            "api_key": "",
            "model": "qwen-plus",
            "max_tokens": 1000,
            "temperature": 0.3
        }
    
    def save_config(self, config: Dict):
        """保存配置"""
        config_file = Path('config/ai_config.json')
        config_file.parent.mkdir(exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self.config = config
        self.api_key = config.get('api_key', '')
        self.enabled = config.get('enabled', False)
    
    def build_prompt(self, signal_data: Dict) -> str:
        """构建 AI 分析 prompt"""
        prompt = f"""你是一个专业的加密货币交易分析师。请分析以下交易信号并给出评分和建议。

## 信号信息

**基础信息:**
- 策略：{signal_data.get('strategy_name', 'Unknown')}
- 标的：{signal_data.get('symbol', 'N/A')}
- 操作：{signal_data.get('action', 'BUY')}
- 方向：{signal_data.get('direction', 'LONG')}
- 当前价格：${signal_data.get('current_price', 0):,.2f}
- 信号时间：{signal_data.get('timestamp', '')}

**风险管理:**
- 入场价：${signal_data.get('entry_price', 0):,.2f}
- 止损价：${signal_data.get('stop_loss_price', 0):,.2f} ({signal_data.get('stop_loss_pct', 0):.2f}%)
- 止盈价：${signal_data.get('take_profit_price', 0):,.2f} ({signal_data.get('take_profit_pct', 0):.2f}%)
- 盈亏比：{signal_data.get('risk_reward_ratio', 0)}:1
- 建议仓位：{signal_data.get('position_size_pct', 0)}%

**技术指标:**
{self._format_indicators(signal_data.get('indicators', {}))}

**多时间周期分析:**
{self._format_timeframes(signal_data.get('timeframe_analysis', {}))}

**支撑阻力位:**
{self._format_levels(signal_data.get('support_resistance', {}))}

**成交量分析:**
{signal_data.get('volume_analysis', '无数据')}

**历史表现:**
- 策略胜率：{signal_data.get('strategy_win_rate', 0):.1f}%
- 近 10 笔表现：{signal_data.get('strategy_last_10', 'N/A')}
- 夏普比率：{signal_data.get('strategy_sharpe', 0):.2f}

**市场环境:**
- 短期趋势：{signal_data.get('trend_short', 'N/A')}
- 中期趋势：{signal_data.get('trend_medium', 'N/A')}
- 波动率：{signal_data.get('volatility', 'N/A')}

---

## 请分析并给出

1. **信号评分** (0-100 分)
   - 90-100: 极强信号，重仓机会
   - 80-89: 强信号，正常仓位
   - 70-79: 中等信号，轻仓
   - 60-69: 弱信号，观望
   - <60: 无效信号，放弃

2. **评分理由** (3-5 条关键点)

3. **建议仓位** (0-25%)

4. **风险警告** (如有)

5. **最终建议** (强烈推荐/推荐/观望/放弃)

---

请以 JSON 格式回复：
{{
    "score": 85,
    "reasons": ["理由 1", "理由 2", "理由 3"],
    "suggested_position": 15.0,
    "risks": ["风险 1", "风险 2"],
    "recommendation": "推荐"
}}
"""
        return prompt
    
    def _format_indicators(self, indicators: Dict) -> str:
        """格式化技术指标"""
        if not indicators:
            return "- 无数据"
        
        lines = []
        for key, value in indicators.items():
            if isinstance(value, dict):
                value_str = ', '.join(f"{k}: {v}" for k, v in value.items())
            else:
                value_str = str(value)
            lines.append(f"- {key}: {value_str}")
        return '\n'.join(lines)
    
    def _format_timeframes(self, timeframes: Dict) -> str:
        """格式化时间周期分析"""
        if not timeframes:
            return "- 无数据"
        
        lines = []
        for tf, data in timeframes.items():
            if isinstance(data, dict):
                trend = data.get('trend', 'N/A')
                lines.append(f"- {tf}: {trend}")
            else:
                lines.append(f"- {tf}: {data}")
        return '\n'.join(lines)
    
    def _format_levels(self, levels: Dict) -> str:
        """格式化支撑阻力位"""
        if not levels:
            return "- 无数据"
        
        lines = []
        if 'supports' in levels:
            lines.append(f"- 支撑位：{', '.join(str(s) for s in levels['supports'])}")
        if 'resistances' in levels:
            lines.append(f"- 阻力位：{', '.join(str(r) for r in levels['resistances'])}")
        return '\n'.join(lines) if lines else "- 无数据"
    
    def analyze(self, signal_data: Dict) -> Optional[Dict]:
        """分析信号"""
        if not self.enabled or not self.api_key:
            return None
        
        try:
            prompt = self.build_prompt(signal_data)
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的加密货币交易分析师，擅长技术分析、风险管理和量化交易。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": self.config.get('temperature', 0.3),
                "max_tokens": self.config.get('max_tokens', 1000)
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=120  # 增加到 120 秒
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # 解析 JSON 回复
                try:
                    # 尝试提取 JSON
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        ai_result = json.loads(json_match.group())
                        return ai_result
                    else:
                        return {"error": "无法解析 AI 回复", "raw": content}
                except json.JSONDecodeError:
                    return {"error": "JSON 解析失败", "raw": content}
            else:
                return {"error": f"API 错误：{response.status_code}", "details": response.text}
        
        except Exception as e:
            return {"error": f"分析失败：{str(e)}"}
    
    def test_connection(self) -> Dict:
        """测试连接"""
        test_signal = {
            "strategy_name": "测试策略",
            "symbol": "BTC-USD",
            "action": "BUY",
            "direction": "LONG",
            "current_price": 50000.0,
            "entry_price": 50000.0,
            "stop_loss_price": 48000.0,
            "stop_loss_pct": 4.0,
            "take_profit_price": 55000.0,
            "take_profit_pct": 10.0,
            "risk_reward_ratio": 2.5,
            "position_size_pct": 10.0,
            "timestamp": datetime.now().isoformat(),
            "indicators": {"RSI": 65, "MACD": "金叉"},
            "timeframe_analysis": {"1H": "上涨", "4H": "上涨", "1D": "上涨"},
            "support_resistance": {"supports": [48000, 45000], "resistances": [52000, 55000]},
            "volume_analysis": "放量 1.5 倍",
            "strategy_win_rate": 55.0,
            "strategy_last_10": "+8.5%",
            "strategy_sharpe": 0.8,
            "trend_short": "BULLISH",
            "trend_medium": "BULLISH",
            "volatility": "MEDIUM"
        }
        
        return self.analyze(test_signal)


# 便捷函数
def get_ai_scorer() -> AIScorer:
    """获取 AI 评分器实例"""
    return AIScorer()


def analyze_signal(signal_data: Dict) -> Optional[Dict]:
    """分析信号（便捷函数）"""
    scorer = get_ai_scorer()
    return scorer.analyze(signal_data)


# 测试
if __name__ == "__main__":
    scorer = AIScorer()
    
    print("🤖 AI 信号评分器测试")
    print(f"状态：{'✅ 已启用' if scorer.enabled else '❌ 未启用'}")
    print(f"API: {scorer.api_url[:50]}...")
    print(f"模型：{scorer.model}")
    
    if scorer.enabled and scorer.api_key:
        print("\n📝 测试连接...")
        result = scorer.test_connection()
        if 'error' in result:
            print(f"❌ 错误：{result['error']}")
        else:
            print(f"✅ 评分：{result.get('score', 'N/A')}")
            print(f"📊 建议：{result.get('recommendation', 'N/A')}")
    else:
        print("\n⚠️ 请先在 Web 页面配置 AI 参数")
