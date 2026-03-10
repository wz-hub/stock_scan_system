"""
消息模板系统

提供统一的消息模板配置和渲染功能
支持多种消息类型：新信号、平仓通知、日报/周报
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class SignalData:
    """信号数据"""
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


@dataclass
class ClosePositionData:
    """平仓数据"""
    signal_id: str
    strategy_name: str
    symbol: str
    action: str  # BUY/SELL
    direction: str  # LONG/SHORT
    entry_price: float
    exit_price: float
    close_timestamp: str
    pnl: float
    pnl_percent: float
    holding_period: str
    exit_reason: str


class MessageTemplate:
    """消息模板基类"""
    
    def __init__(self, template_config: Optional[Dict] = None):
        self.config = template_config or self._default_config()
    
    def _default_config(self) -> Dict:
        """默认模板配置"""
        return {}
    
    def render(self, data: Dict[str, Any]) -> Dict:
        """渲染消息"""
        raise NotImplementedError
    
    def render_text(self, data: Dict[str, Any]) -> str:
        """渲染纯文本消息"""
        raise NotImplementedError


class SignalTemplate(MessageTemplate):
    """新信号模板"""
    
    def _default_config(self) -> Dict:
        return {
            "title_emoji": {
                "BUY": "🟢",
                "SELL": "🔴"
            },
            "direction_emoji": {
                "LONG": "📈",
                "SHORT": "📉"
            },
            "action_text": {
                "BUY": "买入",
                "SELL": "卖出"
            },
            "confidence_thresholds": {
                "high": 75,
                "medium": 60
            },
            "confidence_colors": {
                "high": "#ff4444",
                "medium": "#ffaa00",
                "low": "#00ff88"
            },
            "card_wide_screen": True,
            "include_buttons": True,
            "dashboard_url": "http://192.168.2.79:8501"
        }
    
    def render(self, data: Dict[str, Any]) -> Dict:
        """渲染飞书卡片消息"""
        signal = SignalData(**data)
        
        # 颜色和 emoji
        action_emoji = self.config["title_emoji"].get(signal.action, "🔵")
        action_text = self.config["action_text"].get(signal.action, signal.action)
        direction_emoji = self.config["direction_emoji"].get(signal.direction, "📊")
        
        # 优先级
        confidence = signal.confidence
        high_thresh = self.config["confidence_thresholds"]["high"]
        medium_thresh = self.config["confidence_thresholds"]["medium"]
        
        if confidence >= high_thresh:
            priority_color = self.config["confidence_colors"]["high"]
            priority_text = "高"
        elif confidence >= medium_thresh:
            priority_color = self.config["confidence_colors"]["medium"]
            priority_text = "中"
        else:
            priority_color = self.config["confidence_colors"]["low"]
            priority_text = "低"
        
        card = {
            "config": {
                "wide_screen_mode": self.config.get("card_wide_screen", True)
            },
            "header": {
                "template": "green" if signal.action == "BUY" else "red",
                "title": {
                    "tag": "plain_text",
                    "content": f"{action_emoji}【{signal.strategy_name}】{signal.symbol} {action_text}"
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
                                "content": f"**📅 时间**\n{signal.timestamp[:16].replace('T', ' ')}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💰 价格**\n${signal.price:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📊 方向**\n{signal.direction} {direction_emoji}"
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
                        "content": f"**💡 信号理由**\n{signal.reason}"
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
                                "content": f"**止损**\n${signal.stop_loss:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**止盈**\n${signal.take_profit:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**盈亏比**\n{signal.risk_reward_ratio}:1"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**置信度**\n<font color=\"{priority_color}\">{priority_text} ({confidence:.0f}%)</font>"
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
                            "content": f"ID: {signal.signal_id} | 策略仅供参考，不构成投资建议"
                        }
                    ]
                }
            ]
        }
        
        # 添加按钮
        if self.config.get("include_buttons", True):
            dashboard_url = self.config.get("dashboard_url", "http://192.168.2.79:8501")
            card["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📊 查看 K 线"
                        },
                        "url": dashboard_url,
                        "type": "default"
                    },
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "📋 信号详情"
                        },
                        "url": f"{dashboard_url}?signal_id={signal.signal_id}",
                        "type": "primary"
                    }
                ]
            })
        
        return card
    
    def render_text(self, data: Dict[str, Any]) -> str:
        """渲染纯文本消息"""
        signal = SignalData(**data)
        
        action_emoji = self.config["title_emoji"].get(signal.action, "🔵")
        direction_emoji = self.config["direction_emoji"].get(signal.direction, "📊")
        
        text = f"""
{action_emoji}【{signal.strategy_name}】{signal.symbol} {signal.action}

📅 时间：{signal.timestamp[:16].replace('T', ' ')}
💰 价格：${signal.price:,.2f}
📊 方向：{signal.direction} {direction_emoji}

💡 信号理由:
{signal.reason}

📐 风险管理:
├ 止损：${signal.stop_loss:,.2f}
├ 止盈：${signal.take_profit:,.2f}
└ 盈亏比：{signal.risk_reward_ratio}:1

📈 置信度：{signal.confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━━━
ID: {signal.signal_id}
"""
        return text.strip()


class ClosePositionTemplate(MessageTemplate):
    """平仓通知模板"""
    
    def _default_config(self) -> Dict:
        return {
            "pnl_emoji": {
                "positive": "✅",
                "negative": "❌",
                "neutral": "➖"
            },
            "pnl_colors": {
                "positive": "#00ff88",
                "negative": "#ff4444",
                "neutral": "#888888"
            }
        }
    
    def render(self, data: Dict[str, Any]) -> Dict:
        """渲染飞书卡片消息"""
        pos = ClosePositionData(**data)
        
        # 盈亏颜色和 emoji
        if pos.pnl > 0:
            pnl_color = self.config["pnl_colors"]["positive"]
            pnl_emoji = self.config["pnl_emoji"]["positive"]
            pnl_sign = "+"
        elif pos.pnl < 0:
            pnl_color = self.config["pnl_colors"]["negative"]
            pnl_emoji = self.config["pnl_emoji"]["negative"]
            pnl_sign = ""
        else:
            pnl_color = self.config["pnl_colors"]["neutral"]
            pnl_emoji = self.config["pnl_emoji"]["neutral"]
            pnl_sign = ""
        
        action_emoji = "🟢" if pos.action == "BUY" else "🔴"
        direction_emoji = "📈" if pos.direction == "LONG" else "📉"
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "green" if pos.pnl > 0 else "red" if pos.pnl < 0 else "grey",
                "title": {
                    "tag": "plain_text",
                    "content": f"{pnl_emoji}【{pos.strategy_name}】{pos.symbol} 平仓"
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
                                "content": f"**📅 平仓时间**\n{pos.close_timestamp[:16].replace('T', ' ')}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💰 平仓价**\n${pos.exit_price:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📊 方向**\n{pos.direction} {direction_emoji}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**⏱️ 持仓**\n{pos.holding_period}"
                            }
                        }
                    ]
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💵 入场价**\n${pos.entry_price:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💰 出场价**\n${pos.exit_price:,.2f}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📈 盈亏**\n<font color=\"{pnl_color}\">{pnl_sign}${pos.pnl:,.2f}</font>"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📊 收益率**\n<font color=\"{pnl_color}\">{pnl_sign}{pos.pnl_percent:.2f}%</font>"
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
                        "content": f"**📝 平仓原因**\n{pos.exit_reason}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"ID: {pos.signal_id}"
                        }
                    ]
                }
            ]
        }
        
        return card
    
    def render_text(self, data: Dict[str, Any]) -> str:
        """渲染纯文本消息"""
        pos = ClosePositionData(**data)
        
        pnl_emoji = "✅" if pos.pnl > 0 else "❌" if pos.pnl < 0 else "➖"
        pnl_sign = "+" if pos.pnl > 0 else ""
        direction_emoji = "📈" if pos.direction == "LONG" else "📉"
        
        text = f"""
{pnl_emoji}【{pos.strategy_name}】{pos.symbol} 平仓

📅 平仓时间：{pos.close_timestamp[:16].replace('T', ' ')}
💰 平仓价格：${pos.exit_price:,.2f}
📊 方向：{pos.direction} {direction_emoji}
⏱️ 持仓时间：{pos.holding_period}

💵 交易详情:
├ 入场价：${pos.entry_price:,.2f}
├ 出场价：${pos.exit_price:,.2f}
├ 盈亏：{pnl_sign}${pos.pnl:,.2f}
└ 收益率：{pnl_sign}{pos.pnl_percent:.2f}%

📝 平仓原因:
{pos.exit_reason}

━━━━━━━━━━━━━━━━━━━━━━
ID: {pos.signal_id}
"""
        return text.strip()


class DailyReportTemplate(MessageTemplate):
    """日报/周报模板"""
    
    def _default_config(self) -> Dict:
        return {
            "report_types": {
                "daily": "日报",
                "weekly": "周报"
            }
        }
    
    def render(self, data: Dict[str, Any]) -> Dict:
        """渲染飞书卡片消息"""
        report_type = data.get("report_type", "daily")
        report_title = self.config["report_types"].get(report_type, "报告")
        
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        total_signals = data.get("total_signals", 0)
        closed_positions = data.get("closed_positions", 0)
        total_pnl = data.get("total_pnl", 0.0)
        total_pnl_percent = data.get("total_pnl_percent", 0.0)
        win_rate = data.get("win_rate", 0.0)
        best_trade = data.get("best_trade", {})
        worst_trade = data.get("worst_trade", {})
        
        pnl_color = "#00ff88" if total_pnl >= 0 else "#ff4444"
        pnl_emoji = "✅" if total_pnl >= 0 else "❌"
        pnl_sign = "+" if total_pnl > 0 else ""
        
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "template": "green" if total_pnl >= 0 else "red",
                "title": {
                    "tag": "plain_text",
                    "content": f"{pnl_emoji} 交易系统{report_title} - {date_str}"
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
                                "content": f"**📊 总信号数**\n{total_signals}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**✅ 已平仓**\n{closed_positions}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**📈 胜率**\n{win_rate:.1f}%"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**💰 总盈亏**\n<font color=\"{pnl_color}\">{pnl_sign}${total_pnl:,.2f} ({pnl_sign}{total_pnl_percent:.2f}%)</font>"
                            }
                        }
                    ]
                }
            ]
        }
        
        # 添加最佳和最差交易
        if best_trade or worst_trade:
            card["elements"].append({"tag": "hr"})
            fields = []
            
            if best_trade:
                fields.append({
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**🏆 最佳交易**\n{best_trade.get('symbol', 'N/A')}\n<font color=\"#00ff88\">+${best_trade.get('pnl', 0):,.2f}</font>"
                    }
                })
            
            if worst_trade:
                fields.append({
                    "is_short": True,
                    "text": {
                        "tag": "lark_md",
                        "content": f"**📉 最差交易**\n{worst_trade.get('symbol', 'N/A')}\n<font color=\"#ff4444\">${worst_trade.get('pnl', 0):,.2f}</font>"
                    }
                })
            
            if fields:
                card["elements"].append({
                    "tag": "div",
                    "fields": fields
                })
        
        card["elements"].append({
            "tag": "hr"
        })
        card["elements"].append({
            "tag": "note",
            "elements": [
                {
                    "tag": "plain_text",
                    "content": "策略仅供参考，不构成投资建议"
                }
            ]
        })
        
        return card
    
    def render_text(self, data: Dict[str, Any]) -> str:
        """渲染纯文本消息"""
        report_type = data.get("report_type", "daily")
        report_title = self.config["report_types"].get(report_type, "报告")
        
        date_str = data.get("date", datetime.now().strftime("%Y-%m-%d"))
        total_pnl = data.get("total_pnl", 0.0)
        total_pnl_percent = data.get("total_pnl_percent", 0.0)
        
        pnl_emoji = "✅" if total_pnl >= 0 else "❌"
        pnl_sign = "+" if total_pnl > 0 else ""
        
        text = f"""
{pnl_emoji} 交易系统{report_title} - {date_str}

📊 交易概览:
├ 总信号数：{data.get('total_signals', 0)}
├ 已平仓：{data.get('closed_positions', 0)}
├ 胜率：{data.get('win_rate', 0):.1f}%
└ 总盈亏：{pnl_sign}${total_pnl:,.2f} ({pnl_sign}{total_pnl_percent:.2f}%)

━━━━━━━━━━━━━━━━━━━━━━
策略仅供参考，不构成投资建议
"""
        return text.strip()


class TemplateManager:
    """模板管理器
    
    集中管理所有模板，支持动态加载和配置
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.templates: Dict[str, MessageTemplate] = {}
        self.config_path = config_path
        self.config = self._load_config()
        self._init_templates()
    
    def _load_config(self) -> Dict:
        """加载模板配置"""
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path) as f:
                return json.load(f)
        return {}
    
    def _init_templates(self):
        """初始化所有模板"""
        self.templates["signal"] = SignalTemplate(self.config.get("signal", {}))
        self.templates["close_position"] = ClosePositionTemplate(self.config.get("close_position", {}))
        self.templates["daily_report"] = DailyReportTemplate(self.config.get("daily_report", {}))
    
    def get_template(self, template_type: str) -> MessageTemplate:
        """获取模板"""
        if template_type not in self.templates:
            raise ValueError(f"Unknown template type: {template_type}")
        return self.templates[template_type]
    
    def render(self, template_type: str, data: Dict[str, Any], format: str = "card") -> Any:
        """渲染消息
        
        Args:
            template_type: 模板类型 (signal, close_position, daily_report)
            data: 数据字典
            format: 输出格式 (card, text)
        
        Returns:
            渲染后的消息（卡片字典或文本字符串）
        """
        template = self.get_template(template_type)
        
        if format == "card":
            return template.render(data)
        elif format == "text":
            return template.render_text(data)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def update_config(self, template_type: str, config: Dict):
        """更新模板配置"""
        if template_type in self.templates:
            self.templates[template_type].config.update(config)
    
    def save_config(self, path: Optional[str] = None):
        """保存配置到文件"""
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No config path specified")
        
        config_data = {
            "signal": self.templates["signal"].config,
            "close_position": self.templates["close_position"].config,
            "daily_report": self.templates["daily_report"].config
        }
        
        with open(save_path, 'w') as f:
            json.dump(config_data, f, indent=2)


# 便捷函数
def render_signal(data: Dict[str, Any], format: str = "card") -> Any:
    """渲染信号消息"""
    manager = TemplateManager()
    return manager.render("signal", data, format)


def render_close_position(data: Dict[str, Any], format: str = "card") -> Any:
    """渲染平仓消息"""
    manager = TemplateManager()
    return manager.render("close_position", data, format)


def render_daily_report(data: Dict[str, Any], format: str = "card") -> Any:
    """渲染日报/周报"""
    manager = TemplateManager()
    return manager.render("daily_report", data, format)
