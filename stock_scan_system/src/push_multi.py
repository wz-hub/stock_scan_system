# -*- coding: utf-8 -*-
"""
多渠道推送模块

支持：
- 飞书
- 企业微信
- Telegram
- 邮件
- Discord
- 钉钉
"""

import requests
import smtplib
import json
import logging
from typing import List, Dict, Optional, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


class MultiChannelPusher:
    """多渠道推送器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化推送器
        
        Args:
            config: 配置字典
                {
                    'feishu_webhook': 'https://...',
                    'wechat_webhook': 'https://...',
                    'telegram_bot_token': '...',
                    'telegram_chat_id': '...',
                    'email_smtp': 'smtp.qq.com',
                    'email_user': 'xxx@qq.com',
                    'email_pass': 'xxx',
                    'email_receivers': ['xxx@qq.com'],
                    'discord_webhook': 'https://...',
                    'dingtalk_webhook': 'https://...',
                }
        """
        self.config = config
        self.channels = []
        
        # 检查哪些渠道可用
        if config.get('feishu_webhook'):
            self.channels.append('feishu')
        if config.get('wechat_webhook'):
            self.channels.append('wechat')
        if config.get('telegram_bot_token') and config.get('telegram_chat_id'):
            self.channels.append('telegram')
        if config.get('email_user') and config.get('email_pass'):
            self.channels.append('email')
        if config.get('discord_webhook'):
            self.channels.append('discord')
        if config.get('dingtalk_webhook'):
            self.channels.append('dingtalk')
        
        logger.info(f"Enabled channels: {self.channels}")
    
    def push(self, message: str, title: str = "股票扫描通知", channels: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        推送消息
        
        Args:
            message: 消息内容
            title: 标题
            channels: 指定渠道（不传则推送到所有）
            
        Returns:
            各渠道推送结果
        """
        if channels is None:
            channels = self.channels
        
        results = {}
        
        for channel in channels:
            try:
                if channel == 'feishu':
                    results['feishu'] = self._push_feishu(message, title)
                elif channel == 'wechat':
                    results['wechat'] = self._push_wechat(message, title)
                elif channel == 'telegram':
                    results['telegram'] = self._push_telegram(message, title)
                elif channel == 'email':
                    results['email'] = self._push_email(message, title)
                elif channel == 'discord':
                    results['discord'] = self._push_discord(message, title)
                elif channel == 'dingtalk':
                    results['dingtalk'] = self._push_dingtalk(message, title)
            except Exception as e:
                logger.error(f"Push to {channel} failed: {e}")
                results[channel] = False
        
        return results
    
    def _push_feishu(self, message: str, title: str) -> bool:
        """推送到飞书"""
        webhook = self.config.get('feishu_webhook')
        if not webhook:
            return False
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": message
                    }
                ]
            }
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        return response.status_code == 200
    
    def _push_wechat(self, message: str, title: str) -> bool:
        """推送到企业微信"""
        webhook = self.config.get('wechat_webhook')
        if not webhook:
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": f"### {title}\n\n{message}"
            }
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        return response.status_code == 200
    
    def _push_telegram(self, message: str, title: str) -> bool:
        """推送到 Telegram"""
        token = self.config.get('telegram_bot_token')
        chat_id = self.config.get('telegram_chat_id')
        
        if not token or not chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": f"*{title}*\n\n{message}",
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    
    def _push_email(self, message: str, title: str) -> bool:
        """推送到邮件"""
        smtp_server = self.config.get('email_smtp', 'smtp.qq.com')
        smtp_port = self.config.get('email_smtp_port', 587)
        user = self.config.get('email_user')
        password = self.config.get('email_pass')
        receivers = self.config.get('email_receivers', [user])
        
        if not user or not password:
            return False
        
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = user
        msg['To'] = ', '.join(receivers)
        msg['Subject'] = title
        
        # 添加正文
        msg.attach(MIMEText(message, 'plain', 'utf-8'))
        
        try:
            # 发送邮件
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(user, password)
            server.sendmail(user, receivers, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _push_discord(self, message: str, title: str) -> bool:
        """推送到 Discord"""
        webhook = self.config.get('discord_webhook')
        if not webhook:
            return False
        
        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": 5814783  # 蓝色
                }
            ]
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        return response.status_code in [200, 204]
    
    def _push_dingtalk(self, message: str, title: str) -> bool:
        """推送到钉钉"""
        webhook = self.config.get('dingtalk_webhook')
        if not webhook:
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": f"## {title}\n\n{message}"
            }
        }
        
        response = requests.post(webhook, json=payload, timeout=10)
        return response.status_code == 200
    
    def push_scan_result(self, signals: List[Dict]) -> Dict[str, bool]:
        """
        推送扫描结果
        
        Args:
            signals: 信号列表
        """
        if not signals:
            return {}
        
        # 格式化消息
        message = []
        for signal in signals:
            emoji = "🟢" if signal.get('signal') == 'buy' else "🔴"
            message.append(
                f"{emoji} **{signal.get('symbol', 'N/A')}**\n"
                f"信号：{signal.get('type', 'N/A')}\n"
                f"价格：¥{signal.get('entry_price', 0):.2f}\n"
                f"目标：¥{signal.get('target_price', 0):.2f}\n"
                f"止损：¥{signal.get('stop_loss', 0):.2f}\n"
                f"策略：{signal.get('strategy', 'N/A')}\n"
            )
        
        message_text = "\n".join(message)
        return self.push(message_text, title="📊 股票扫描结果")


if __name__ == '__main__':
    # 测试
    logging.basicConfig(level=logging.INFO)
    
    config = {
        'feishu_webhook': 'https://open.feishu.cn/open-apis/bot/v2/hook/xxx',
        'wechat_webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx',
    }
    
    pusher = MultiChannelPusher(config)
    
    # 测试推送
    test_signals = [
        {
            'symbol': '601138',
            'signal': 'buy',
            'type': '买入信号',
            'entry_price': 28.50,
            'target_price': 31.00,
            'stop_loss': 27.00,
            'strategy': 'btc_ma_cross',
        }
    ]
    
    results = pusher.push_scan_result(test_signals)
    print(f"Push results: {results}")
