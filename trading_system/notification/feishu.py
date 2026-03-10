"""
飞书推送渠道

实现飞书 webhook 消息发送功能
支持卡片消息和文本消息
"""
import requests
import json
from typing import Dict, Optional, Any
from pathlib import Path


class FeishuChannel:
    """飞书通知渠道
    
    负责通过飞书 webhook 发送消息
    支持卡片消息和文本消息两种格式
    """
    
    def __init__(self, webhook_url: str, timeout: int = 10):
        """初始化飞书渠道
        
        Args:
            webhook_url: 飞书机器人 webhook URL
            timeout: 请求超时时间（秒）
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
    
    def send_card(self, card: Dict[str, Any]) -> Dict[str, Any]:
        """发送卡片消息
        
        Args:
            card: 飞书卡片消息字典
        
        Returns:
            发送结果：{"success": bool, "message_id": str, "error": str}
        """
        payload = {
            "msg_type": "interactive",
            "card": card
        }
        
        try:
            response = self.session.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            result = response.json()
            
            # 飞书 API 返回格式可能有两种
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                return {
                    "success": True,
                    "message_id": result.get('message_id', result.get('data', {}).get('message_id'))
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {result}"
                }
        
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_text(self, text: str) -> Dict[str, Any]:
        """发送文本消息
        
        Args:
            text: 文本消息内容
        
        Returns:
            发送结果：{"success": bool, "message_id": str, "error": str}
        """
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
                timeout=self.timeout
            )
            result = response.json()
            
            if result.get('StatusCode') == 0 or result.get('code') == 0:
                return {
                    "success": True,
                    "message_id": result.get('message_id', result.get('data', {}).get('message_id'))
                }
            else:
                return {
                    "success": False,
                    "error": f"API Error: {result}"
                }
        
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Request timeout"}
        except requests.exceptions.ConnectionError as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send(self, content: Any, format: str = "card") -> Dict[str, Any]:
        """通用发送接口
        
        Args:
            content: 消息内容（卡片字典或文本字符串）
            format: 消息格式 (card, text)
        
        Returns:
            发送结果
        """
        if format == "card":
            return self.send_card(content)
        elif format == "text":
            return self.send_text(content)
        else:
            return {"success": False, "error": f"Unknown format: {format}"}
    
    def test_connection(self) -> bool:
        """测试连接
        
        Returns:
            连接是否成功
        """
        test_text = "🦐 交易系统通知测试 - 飞书推送功能验证"
        result = self.send_text(test_text)
        return result.get("success", False)
    
    @classmethod
    def from_config(cls, config_path: str) -> "FeishuChannel":
        """从配置文件创建实例
        
        Args:
            config_path: 配置文件路径（JSON 格式）
        
        Returns:
            FeishuChannel 实例
        """
        with open(config_path) as f:
            config = json.load(f)
        
        webhook_url = config.get("feishu", {}).get("webhook_url")
        if not webhook_url:
            raise ValueError("webhook_url not found in config")
        
        timeout = config.get("feishu", {}).get("timeout", 10)
        return cls(webhook_url, timeout)


def send_feishu_notification(
    webhook_url: str,
    content: Any,
    format: str = "card",
    timeout: int = 10
) -> Dict[str, Any]:
    """便捷函数：发送飞书通知
    
    Args:
        webhook_url: 飞书 webhook URL
        content: 消息内容
        format: 消息格式 (card, text)
        timeout: 超时时间
    
    Returns:
        发送结果
    """
    channel = FeishuChannel(webhook_url, timeout)
    return channel.send(content, format)


def send_signal_notification(
    webhook_url: str,
    signal_data: Dict[str, Any],
    use_card: bool = True
) -> Dict[str, Any]:
    """便捷函数：发送信号通知
    
    自动使用模板渲染信号消息并发送
    
    Args:
        webhook_url: 飞书 webhook URL
        signal_data: 信号数据字典
        use_card: 是否使用卡片消息
    
    Returns:
        发送结果
    """
    from .templates import render_signal
    
    format = "card" if use_card else "text"
    content = render_signal(signal_data, format)
    
    return send_feishu_notification(webhook_url, content, format)


def send_close_position_notification(
    webhook_url: str,
    position_data: Dict[str, Any],
    use_card: bool = True
) -> Dict[str, Any]:
    """便捷函数：发送平仓通知
    
    Args:
        webhook_url: 飞书 webhook URL
        position_data: 平仓数据字典
        use_card: 是否使用卡片消息
    
    Returns:
        发送结果
    """
    from .templates import render_close_position
    
    format = "card" if use_card else "text"
    content = render_close_position(position_data, format)
    
    return send_feishu_notification(webhook_url, content, format)


def send_daily_report_notification(
    webhook_url: str,
    report_data: Dict[str, Any],
    use_card: bool = True
) -> Dict[str, Any]:
    """便捷函数：发送日报/周报
    
    Args:
        webhook_url: 飞书 webhook URL
        report_data: 报告数据字典
        use_card: 是否使用卡片消息
    
    Returns:
        发送结果
    """
    from .templates import render_daily_report
    
    format = "card" if use_card else "text"
    content = render_daily_report(report_data, format)
    
    return send_feishu_notification(webhook_url, content, format)


# 兼容性封装：保持与旧版 feishu_notifier.py 的接口兼容
class FeishuNotifier:
    """飞书通知器（兼容旧版接口）
    
    内部使用新的 FeishuChannel 实现
    """
    
    def __init__(self, webhook_url: str):
        self.channel = FeishuChannel(webhook_url)
    
    def send_card(self, signal) -> Dict[str, Any]:
        """发送卡片消息（兼容旧版 SignalMessage）"""
        if hasattr(signal, 'to_feishu_card'):
            # 旧版 SignalMessage 对象
            card = signal.to_feishu_card()
        elif isinstance(signal, dict):
            # 已经是卡片字典
            card = signal
        else:
            # 尝试使用新模板系统
            from .templates import render_signal
            card = render_signal(signal.__dict__ if hasattr(signal, '__dict__') else signal, "card")
        
        return self.channel.send_card(card)
    
    def send_text(self, signal) -> Dict[str, Any]:
        """发送文本消息（兼容旧版 SignalMessage）"""
        if hasattr(signal, 'to_text'):
            # 旧版 SignalMessage 对象
            text = signal.to_text()
        elif isinstance(signal, str):
            # 已经是文本
            text = signal
        else:
            # 尝试使用新模板系统
            from .templates import render_signal
            text = render_signal(signal.__dict__ if hasattr(signal, '__dict__') else signal, "text")
        
        return self.channel.send_text(text)
    
    def test_connection(self) -> bool:
        """测试连接"""
        return self.channel.test_connection()
