"""
飞书消息推送模块
"""
import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SignalMessage:
    """信号消息"""
    signal_id: str
    strategy_name: str
    symbol: str
    action: str  # BUY/SELL
    direction: str  # LONG/SHORT
    price: float
    timestamp: str
    confidence: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    reason: str
    
    def to_feishu_card(self) -> Dict:
        """转换为飞书卡片消息"""
        # 颜色和 emoji
        if self.action == "BUY":
            color = "#00ff88"
            action_text = "买入"
            action_emoji = "🟢"
            direction_emoji = "📈"
        else:
            color = "#ff4444"
            action_text = "卖出"
            action_emoji = "🔴"
            direction_emoji = "📉"
        
        # 优先级颜色
        if self.confidence >= 75:
            priority_color = "#ff4444"
            priority_text = "高"
        elif self.confidence >= 60:
            priority_color = "#ffaa00"
            priority_text = "中"
        else:
            priority_color = "#00ff88"
            priority_text = "低"
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "green" if self.action == "BUY" else "red",
                "title": {
                    "tag": "plain_text",
                    "content": f"{action_emoji}【{self.strategy_name}】{self.symbol} {action_text}"
                }
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📅 时间**\n{self.timestamp[:16].replace('T', ' ')}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💰 价格**\n${self.price:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📊 方向**\n{self.direction} {direction_emoji}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**🎯 类型**\n开仓"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💡 信号理由**\n{self.reason}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📐 风险管理**"
                    }
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**止损**\n${self.stop_loss:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**止盈**\n${self.take_profit:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**盈亏比**\n{self.risk_reward_ratio}:1"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**置信度**\n<font color=\"{priority_color}\">{self.confidence:.0f}%</font>"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"ID: {self.signal_id} | 策略仅供参考，不构成投资建议"
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "📊 查看 K 线"
                            },
                            "url": "http://192.168.2.79:8501",
                            "type": "default"
                        },
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "📋 信号详情"
                            },
                            "url": f"http://192.168.2.79:8501/?signal_id={self.signal_id}",
                            "type": "primary"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def to_text(self) -> str:
        """转换为纯文本消息"""
        action_emoji = "🟢" if self.action == "BUY" else "🔴"
        direction_emoji = "📈" if self.direction == "LONG" else "📉"
        
        text = f"""
{action_emoji}【{self.strategy_name}】{self.symbol} {self.action}

📅 时间：{self.timestamp[:16].replace('T', ' ')}
💰 价格：${self.price:,.2f}
📊 方向：{self.direction} {direction_emoji}

💡 信号理由:
{self.reason}

📐 风险管理:
├ 止损：${self.stop_loss:,.2f}
├ 止盈：${self.take_profit:,.2f}
└ 盈亏比：{self.risk_reward_ratio}:1

📈 置信度：{self.confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━━━
ID: {self.signal_id}
"""
        return text.strip()


class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = requests.Session()
    
    def send_card(self, signal: SignalMessage) -> Dict:
        """发送卡片消息"""
        card = signal.to_feishu_card()
        
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            result = response.json()
            
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                return {"success": True, "message_id": result.get('message_id')}
            else:
                return {"success": False, "error": result}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_text(self, signal: SignalMessage) -> Dict:
        """发送文本消息"""
        text = signal.to_text()
        
        payload = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            result = response.json()
            
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                return {"success": True, "message_id": result.get('message_id')}
            else:
                return {"success": False, "error": result}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_connection(self) -> bool:
        """测试连接"""
        test_signal = SignalMessage(
            signal_id="TEST-001",
            strategy_name="系统测试",
            symbol="BTC-USD",
            action="BUY",
            direction="LONG",
            price=50000.0,
            timestamp=datetime.now().isoformat(),
            confidence=80.0,
            stop_loss=48000.0,
            take_profit=55000.0,
            risk_reward_ratio=2.5,
            reason="系统连接测试"
        )
        
        result = self.send_text(test_signal)
        return result.get('success', False)


def send_signal(
    webhook_url: str,
    signal_data: Dict,
    use_card: bool = True
) -> Dict:
    """便捷函数：发送信号"""
    notifier = FeishuNotifier(webhook_url)
    
    signal = SignalMessage(
        signal_id=signal_data.get('signal_id', 'UNKNOWN'),
        strategy_name=signal_data.get('strategy_name', 'Unknown'),
        symbol=signal_data.get('symbol', 'UNKNOWN'),
        action=signal_data.get('action', 'BUY'),
        direction=signal_data.get('direction', 'LONG'),
        price=signal_data.get('current_price', 0),
        timestamp=signal_data.get('timestamp', datetime.now().isoformat()),
        confidence=signal_data.get('confidence', 50),
        stop_loss=signal_data.get('stop_loss_price', 0),
        take_profit=signal_data.get('take_profit_price', 0),
        risk_reward_ratio=signal_data.get('risk_reward_ratio', 0),
        reason=signal_data.get('reason', '')
    )
    
    if use_card:
        return notifier.send_card(signal)
    else:
        return notifier.send_text(signal)


# 使用示例
if __name__ == "__main__":
    # 配置你的飞书 webhook
    WEBHOOK_URL = "https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL"
    
    # 测试连接
    notifier = FeishuNotifier(WEBHOOK_URL)
    if notifier.test_connection():
        print("✅ 飞书推送连接成功！")
    else:
        print("❌ 飞书推送连接失败，请检查 webhook URL")
    
    # 发送信号示例
    signal_data = {
        "signal_id": "SIG-20240308-BTC-MA-001",
        "strategy_name": "均线交叉",
        "symbol": "BTC-USD",
        "action": "BUY",
        "direction": "LONG",
        "current_price": 24375.96,
        "timestamp": datetime.now().isoformat(),
        "confidence": 78.5,
        "stop_loss_price": 22500.00,
        "take_profit_price": 26500.00,
        "risk_reward_ratio": 2.3,
        "reason": "12 日 EMA 上穿 26 日 EMA，价格站稳 200 日均线上方"
    }
    
    result = send_signal(WEBHOOK_URL, signal_data, use_card=True)
    print(f"发送结果：{result}")
