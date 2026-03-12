#!/usr/bin/env python3
"""
飞书信号卡片模板
支持 AI 评分展示
"""
from datetime import datetime


def create_signal_card(signal: dict) -> dict:
    """
    创建飞书信号卡片（分区展示版，包含 AI 评分）
    """
    symbol = signal.get('symbol', 'UNKNOWN')
    direction = signal.get('direction', 'LONG')
    action = signal.get('action', 'BUY')
    timeframe = signal.get('timeframe', '4H')
    strategy_name = signal.get('strategy_name', 'Unknown Strategy')
    
    # 确保数值类型正确
    entry_price = float(signal.get('entry_price', 0) or 0)
    stop_loss = float(signal.get('stop_loss_price', 0) or 0)
    take_profit = float(signal.get('take_profit_price', 0) or 0)
    confidence = float(signal.get('confidence', 0) or 0)
    reason = signal.get('reason', '')
    
    # AI 评分信息
    ai_score = signal.get('ai_score', None)
    ai_direction = signal.get('ai_direction', '')
    ai_reason = signal.get('ai_reason', '')
    
    # 方向 emoji 和颜色
    if direction == 'LONG':
        direction_emoji = "📈"
        header_template = "green"
        action_text = "做多"
    else:
        direction_emoji = "📉"
        header_template = "red"
        action_text = "做空"
    
    # 时间周期 emoji
    timeframe_emoji = "📊" if timeframe == '1D' else "⏱️"
    timeframe_label = "日线" if timeframe == '1D' else "4 小时"
    
    # 置信度等级
    if confidence >= 90:
        conf_badge = "🔥极高"
    elif confidence >= 80:
        conf_badge = "⭐高"
    elif confidence >= 70:
        conf_badge = "💪中"
    else:
        conf_badge = "👁️低"
    
    # 确保数值类型正确并格式化
    # 加密货币价格需要保留足够小数位（特别是低价币种）
    try:
        entry_price_val = float(entry_price) if entry_price else 0
        stop_loss_val = float(stop_loss) if stop_loss else 0
        take_profit_val = float(take_profit) if take_profit else 0
        
        # 根据价格大小决定小数位数
        if entry_price_val < 0.01:
            # 超低价币种（如 0.00027）保留 6 位小数
            entry_price_fmt = f"{entry_price_val:.6f}".rstrip('0').rstrip('.')
            stop_loss_fmt = f"{stop_loss_val:.6f}".rstrip('0').rstrip('.')
            take_profit_fmt = f"{take_profit_val:.6f}".rstrip('0').rstrip('.')
        elif entry_price_val < 1:
            # 低价币种（如 0.2063）保留 4 位小数
            entry_price_fmt = f"{entry_price_val:.4f}".rstrip('0').rstrip('.')
            stop_loss_fmt = f"{stop_loss_val:.4f}".rstrip('0').rstrip('.')
            take_profit_fmt = f"{take_profit_val:.4f}".rstrip('0').rstrip('.')
        else:
            # 正常价格保留 2 位小数
            entry_price_fmt = f"{entry_price_val:,.2f}"
            stop_loss_fmt = f"{stop_loss_val:,.2f}"
            take_profit_fmt = f"{take_profit_val:,.2f}"
        
        confidence_fmt = f"{float(confidence):.0f}" if confidence else "0"
    except (ValueError, TypeError):
        entry_price_fmt = "0.00"
        stop_loss_fmt = "0.00"
        take_profit_fmt = "0.00"
        confidence_fmt = "0"
    
    # 构建卡片内容
    elements = [
        {
            "tag": "markdown",
            "content": f"**🏷️ {strategy_name}**  |  **⏱️ {timeframe_label}**  |  **{conf_badge}**\n🕐 {datetime.now().strftime('%m-%d %H:%M')}"
        },
        {
            "tag": "hr"
        },
        {
            "tag": "div",
            "fields": [
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**💰 入场**\n{entry_price_fmt}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**🛑 止损**\n{stop_loss_fmt}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**🎯 止盈**\n{take_profit_fmt}"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**📊 盈亏比**\n3.0:1"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**💪 置信度**\n{confidence_fmt}%"}},
                {"is_short": True, "text": {"tag": "lark_md", "content": f"**💰 仓位**\n{signal.get('position_label', '标准')}"}},
            ]
        }
    ]
    
    # 如果有 AI 评分，添加 AI 评分区域
    if ai_score is not None:
        ai_direction_emoji = "📈" if ai_direction == 'LONG' else ("📉" if ai_direction == 'SHORT' else "⏸️")
        ai_confidence_emoji = "🔥" if ai_score >= 80 else ("⭐" if ai_score >= 60 else "💪")
        
        elements.append({
            "tag": "hr"
        })
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🤖 AI 评分**: {ai_confidence_emoji}{ai_score}% {ai_direction_emoji}{ai_direction}\n💡 {ai_reason}"
            }
        })
    
    # 添加信号理由
    elements.append({
        "tag": "hr"
    })
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**💡 信号理由**: {reason}"
        }
    })
    
    # 构建卡片
    card = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "template": header_template,
                "title": {
                    "tag": "plain_text",
                    "content": f"{timeframe_emoji} {direction_emoji} {symbol} {action_text}"
                }
            },
            "elements": elements
        }
    }
    
    return card
