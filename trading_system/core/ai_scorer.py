"""
AI 评分模块
负责调用 DeepSeek AI API 对交易信号进行独立评分

使用 DeepSeek AI:
- URL: https://api.deepseek.com/v1
- Model: deepseek-chat
- API Key: sk-c5e3db4cd95f43478464c85374cbb252
"""
import json
import requests
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path


class AIScorer:
    """AI 评分器
    
    职责：
    1. 只负责评分，不参与决策
    2. 在去重后、推送前调用
    3. 只对置信度≥80% 的信号评分
    
    使用 DeepSeek AI:
    - URL: https://api.deepseek.com/v1
    - Model: deepseek-chat
    - API Key: sk-c5e3db4cd95f43478464c85374cbb252
    """
    
    def __init__(self, api_key: str = None, model: str = None, base_url: str = None):
        """
        初始化 AI 评分器
        
        Args:
            api_key: API 密钥 (可选，默认从配置读取)
            model: 使用的模型 (默认 deepseek-chat)
            base_url: API 端点 (默认 DeepSeek API)
        """
        # 默认配置（DeepSeek AI）
        self.model = model or "deepseek-chat"
        self.base_url = base_url or "https://api.deepseek.com/v1"
        
        # 从配置文件读取
        if not api_key:
            try:
                config_file = Path(__file__).parent.parent / 'config' / 'ai_config.json'
                if config_file.exists():
                    with open(config_file) as f:
                        config = json.load(f)
                        ai_config = config.get('ai', {})
                        api_key = ai_config.get('api_key', '')
                        if ai_config.get('model'):
                            self.model = ai_config['model']
                        if ai_config.get('base_url'):
                            self.base_url = ai_config['base_url']
            except Exception as e:
                print(f"⚠️ 读取配置失败：{e}")
                api_key = ''
        
        self.api_key = api_key
    
    def score(self, signal: Dict, market_data: Dict) -> Optional[Dict]:
        """
        对信号进行 AI 评分（仅供参考，不参与决策）
        
        调用时机：
        1. 去重完成后
        2. 置信度过滤后 (≥80%)
        3. 推送前最后一刻
        
        Args:
            signal: 信号字典
            market_data: 市场数据字典
        
        Returns:
            AI 评分结果 {
                'direction': 'LONG' | 'SHORT' | 'WAIT',
                'confidence': 85,  # AI 的把握程度 (0-100)
                'reason': '一句话理由'
            }
        """
        # 1. 构建 Prompt
        prompt = self._build_prompt(signal, market_data)
        
        # 2. 调用 AI API
        response = self._call_ai(prompt)
        
        # 3. 解析返回
        if response:
            return self._parse_response(response)
        
        return None
    
    def _build_prompt(self, signal: Dict, market_data: Dict) -> str:
        """
        构建 AI Prompt
        
        Args:
            signal: 信号字典
            market_data: 市场数据字典
        
        Returns:
            Prompt 文本
        """
        # 读取 Prompt 模板
        template_path = Path(__file__).parent.parent / 'templates' / 'ai_score_prompt.md'
        
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            template = self._get_default_template()
        
        # 填充数据（确保数值类型正确并格式化）
        entry_price = signal.get('entry_price', 0)
        if isinstance(entry_price, str):
            try:
                entry_price = float(entry_price)
            except:
                entry_price = 0
        
        # 根据价格大小决定格式化方式
        if entry_price < 0.01:
            current_price_fmt = f"{entry_price:.6f}".rstrip('0').rstrip('.')
        elif entry_price < 1:
            current_price_fmt = f"{entry_price:.4f}".rstrip('0').rstrip('.')
        else:
            current_price_fmt = f"{entry_price:,.2f}"
        
        # 格式化 oi_change
        oi_change_val = market_data.get('oi_change_pct', 0)
        if isinstance(oi_change_val, str):
            try:
                oi_change_val = float(oi_change_val)
            except:
                oi_change_val = 0
        oi_change_fmt = f"{oi_change_val:+.2f}"
        
        prompt = template.format(
            symbol=signal.get('symbol', 'BTCUSDT'),
            current_price=current_price_fmt,
            timeframe=signal.get('timeframe', '4H'),
            
            # K 线数据
            klines_1d=self._format_klines(market_data.get('klines_1d', []), label='1D'),
            klines_4h=self._format_klines(market_data.get('klines_4h', []), label='4H'),
            klines_1h=self._format_klines(market_data.get('klines_1h', []), label='1H'),
            
            # 技术指标
            adx=float(market_data.get('adx', 0) or 0),
            rsi=float(market_data.get('rsi', 0) or 0),
            macd=market_data.get('macd_status', ''),
            macd_histogram=float(market_data.get('macd_histogram', 0) or 0),
            volume_ratio=float(market_data.get('volume_ratio', 1.0) or 1.0),
            atr=float(market_data.get('atr', 0) or 0),
            bb_position=float(market_data.get('bb_position', 0.5) or 0.5),
            
            # 持仓量
            oi_change=oi_change_fmt,
            
            # 时间
            current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        )
        
        return prompt
    
    def _get_default_template(self) -> str:
        """获取默认 Prompt 模板"""
        return """## 角色设定

你是一位资深加密货币量化交易分析师，拥有 10 年传统金融市场 + 5 年加密货币市场经验。

### 专业能力
- **技术分析**: 精通 K 线形态、技术指标、多周期分析
- **趋势判断**: 擅长识别趋势方向、强度、转折点
- **风险管理**: 严格评估风险收益比、波动率、市场异常
- **量化思维**: 基于数据决策，避免情绪化判断

### 分析原则
1. **客观独立**: 不受任何预设立场影响，只看数据说话
2. **风险优先**: 先评估风险，再考虑收益
3. **概率思维**: 市场无绝对，只谈概率和把握度
4. **简洁明确**: 结论清晰，理由充分，不模棱两可

### 输出要求
- 方向判断必须有 K 线形态或指标支撑
- 把握度反映真实信心，不要为了"正确"而保守
- 理由一句话点明核心逻辑，不说废话
- 如果数据不足或市场混乱，果断选择 WAIT

---

请基于以下市场数据，给出你的专业分析：

---

# 交易信号分析

**时间**: {current_time}

## 当前市场

### {symbol} - {current_price} USDT
**周期**: {timeframe}

#### 1D K 线 (最近 30 根)
{klines_1d}

#### 4H K 线 (最近 50 根)
{klines_4h}

#### 1H K 线 (最近 100 根)
{klines_1h}

### 技术指标
- **ADX**: {adx}
- **RSI**: {rsi}
- **MACD**: {macd} ({macd_histogram:+.6f})
- **ATR**: {atr}
- **布林带**: {bb_position:.2f}
- **Vol**: {volume_ratio:.2f}x

### OI
- **变化**: {oi_change}%

---

## 输出：方向 (LONG/SHORT/WAIT)+ 把握 (0-100)+ 理由 → JSON
"""
    
    def _format_klines(self, klines: List[Dict], label: str = '') -> str:
        """
        格式化 K 线数据为表格
        
        Args:
            klines: K 线列表
            label: 时间周期标签 (1D/4H/1H)
        
        Returns:
            格式化的表格文本
        """
        if not klines:
            return "暂无数据"
        
        lines = []
        lines.append("时间 (UTC)      开盘      最高      最低      收盘      成交量")
        
        # 显示最近 N 根 (根据周期决定)
        display_count = 30 if label == '1D' else (50 if label == '4H' else 100)
        for k in klines[-display_count:]:
            # 支持 timestamp 和 time 两种字段名
            timestamp = k.get('timestamp', k.get('time', 0))
            time_str = datetime.fromtimestamp(timestamp/1000).strftime('%m-%d %H:%M')
            
            # 根据价格大小决定小数位（和飞书卡片一致）
            open_val = float(k.get('open', 0))
            high_val = float(k.get('high', 0))
            low_val = float(k.get('low', 0))
            close_val = float(k.get('close', 0))
            
            if close_val < 0.01:
                # 超低价币种保留 6 位
                open_fmt = f"{open_val:.6f}".rstrip('0').rstrip('.')
                high_fmt = f"{high_val:.6f}".rstrip('0').rstrip('.')
                low_fmt = f"{low_val:.6f}".rstrip('0').rstrip('.')
                close_fmt = f"{close_val:.6f}".rstrip('0').rstrip('.')
            elif close_val < 1:
                # 低价币种保留 4 位
                open_fmt = f"{open_val:.4f}".rstrip('0').rstrip('.')
                high_fmt = f"{high_val:.4f}".rstrip('0').rstrip('.')
                low_fmt = f"{low_val:.4f}".rstrip('0').rstrip('.')
                close_fmt = f"{close_val:.4f}".rstrip('0').rstrip('.')
            else:
                # 正常价格保留 2 位
                open_fmt = f"{open_val:.2f}"
                high_fmt = f"{high_val:.2f}"
                low_fmt = f"{low_val:.2f}"
                close_fmt = f"{close_val:.2f}"
            
            # ATR 也根据价格调整
            atr_val = float(k.get('atr', 0))
            if atr_val < 0.01:
                atr_fmt = f"{atr_val:.6f}".rstrip('0').rstrip('.')
            elif atr_val < 1:
                atr_fmt = f"{atr_val:.4f}".rstrip('0').rstrip('.')
            else:
                atr_fmt = f"{atr_val:.2f}"
            
            lines.append(
                f"{time_str}    {open_fmt:>10}  {high_fmt:>10}  "
                f"{low_fmt:>10}  {close_fmt:>10}  {k.get('volume', 0):>12.0f}"
            )
        
        return "\n".join(lines)
    
    def _call_ai(self, prompt: str) -> Optional[str]:
        """
        调用 DeepSeek AI API
        
        Args:
            prompt: Prompt 文本
        
        Returns:
            AI 返回的文本
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # DeepSeek 兼容格式
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 150  # 减少 token，加快响应
        }
        
        # 重试机制：最多重试 3 次
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                # DeepSeek API 端点
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30  # 30 秒超时
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('choices', [{}])[0].get('message', {}).get('content', '')
                else:
                    if attempt < max_retries:
                        print(f"⚠️  API 失败，重试 {attempt+1}/{max_retries}: {response.status_code}")
                        import time
                        time.sleep(2 ** attempt)  # 指数退避
                    else:
                        print(f"❌ AI API 调用失败：{response.status_code}")
                        print(response.text[:200])
                        return None
                        
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"⚠️  超时，重试 {attempt+1}/{max_retries}")
                    import time
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"❌ AI API 调用超时 ({max_retries}次重试后)")
                    return None
            except Exception as e:
                if attempt < max_retries:
                    print(f"⚠️  异常：{e}，重试 {attempt+1}/{max_retries}")
                    import time
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"❌ AI API 调用异常：{e}")
                    return None
        
        return None
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """
        解析 AI 返回
        
        Args:
            response_text: AI 返回的文本
        
        Returns:
            解析后的评分结果
        """
        try:
            # 尝试提取 JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                result = json.loads(json_str)
                
                # 验证必需字段
                if all(key in result for key in ['direction', 'confidence', 'reason']):
                    # 验证 direction 有效性
                    if result['direction'] in ['LONG', 'SHORT', 'WAIT']:
                        # 验证 confidence 范围
                        if 0 <= result['confidence'] <= 100:
                            return result
            
            print(f"⚠️ AI 返回格式不正确：{response_text[:200]}")
            return None
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析失败：{e}")
            print(f"原始返回：{response_text[:200]}")
            return None
        
        except Exception as e:
            print(f"❌ 解析异常：{e}")
            return None


# ========== 便捷函数 ==========

def get_ai_scorer() -> AIScorer:
    """获取 AI 评分器实例"""
    return AIScorer()


def score_signal(signal: Dict, market_data: Dict) -> Optional[Dict]:
    """
    便捷函数：对信号进行 AI 评分
    
    Args:
        signal: 信号字典
        market_data: 市场数据字典
    
    Returns:
        AI 评分结果
    """
    scorer = get_ai_scorer()
    return scorer.score(signal, market_data)


# ========== 测试 ==========

if __name__ == '__main__':
    # 测试数据
    test_signal = {
        'symbol': 'BTCUSDT',
        'entry_price': 70227.91,
        'direction': 'LONG',
        'timeframe': '4H'
    }
    
    test_market_data = {
        'klines_4h': [
            {'time': 1710172800000, 'open': 69500, 'high': 69600, 'low': 69400, 'close': 69550, 'volume': 15000},
            {'time': 1710187200000, 'open': 69550, 'high': 70000, 'low': 69500, 'close': 69900, 'volume': 18000},
            {'time': 1710201600000, 'open': 69900, 'high': 70300, 'low': 69850, 'close': 70227.91, 'volume': 20000},
        ],
        'klines_1d': [],
        'adx': 28.4,
        'rsi': 65.2,
        'macd_status': '金叉',
        'volume_ratio': 1.5,
        'oi_change_pct': 2.5
    }
    
    # 测试评分
    print("=" * 80)
    print("🤖 AI 评分测试 (DeepSeek)")
    print("=" * 80)
    
    scorer = AIScorer()
    print(f"Base URL: {scorer.base_url}")
    print(f"Model: {scorer.model}")
    print(f"API Key: {scorer.api_key[:20]}...")
    print("=" * 80)
    
    # 注意：需要配置真实的 API 密钥才能测试
    # result = scorer.score(test_signal, test_market_data)
    # print(f"AI 评分结果：{result}")
    
    print("\n⚠️  注意：需要配置 API 密钥才能进行真实测试")
    print("请在 config/ai_config.json 中配置 ai.api_key")
    print("=" * 80)
