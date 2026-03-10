"""
通知模块 - 统一消息推送

支持多种通知渠道（飞书、邮件、Webhook 等）
所有消息使用统一模板系统
"""
from .templates import MessageTemplate, TemplateManager
from .feishu import FeishuChannel, send_feishu_notification

__all__ = [
    'MessageTemplate',
    'TemplateManager',
    'FeishuChannel',
    'send_feishu_notification',
]

__version__ = '1.0.0'
