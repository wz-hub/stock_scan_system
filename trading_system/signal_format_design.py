"""
完整的交易信号格式设计
"""

# 当前格式 vs 完整格式对比

print("="*80)
print("当前格式缺少的关键信息")
print("="*80)

missing_info = """
❌ 缺失的信息:

1. 信号元数据
   - 策略版本/参数配置
   - 时间框架 (1H/4H/1D)
   - 信号 ID (用于追踪)
   - 前一个信号 (判断开仓/平仓)

2. 风险管理
   - 建议仓位大小 (%)
   - 止损价格 (具体数值)
   - 止盈价格 (目标位)
   - 风险收益比 (R:R)
   - 最大可承受亏损

3. 市场背景
   - 当前趋势方向
   - 波动率状态 (高/中/低)
   - 成交量状态
   - 市场情绪指标

4. 信号质量
   - 置信度评分 (0-100%)
   - 信号强度
   - 历史胜率参考
   - 最近表现

5. 执行细节
   - 订单类型建议 (市价/限价)
   - 有效期 (GTC/当日有效)
   - 滑点预估
   - 手续费预估

6. 上下文信息
   - 持仓状态 (已有仓位？)
   - 累计盈亏
   - 连续亏损次数
   - 是否违背其他策略信号
"""

print(missing_info)

print("\n" + "="*80)
print("推荐的完整信号格式")
print("="*80)

complete_format = {
    "signal_id": "SIG-20240315-BTC-MA-001",
    "timestamp": "2024-03-15T08:00:00Z",
    "exchange": "Binance",
    
    "market": {
        "symbol": "BTC-USD",
        "timeframe": "1D",
        "price": 24375.96,
        "price_change_24h": 2.5,
        "volume_24h": 15000000000,
        "market_cap_rank": 1
    },
    
    "strategy": {
        "name": "均线交叉",
        "version": "1.2.0",
        "parameters": {
            "fast_period": 12,
            "slow_period": 26,
            "filter_ma": 200
        },
        "category": "trend_following"
    },
    
    "signal": {
        "action": "BUY",  # BUY/SELL/CLOSE_LONG/CLOSE_SHORT
        "type": "OPEN",  # OPEN/CLOSE/REVERSE
        "direction": "LONG",
        "priority": "HIGH",  # HIGH/MEDIUM/LOW
        "confidence": 78.5,  # 0-100
        "strength": "STRONG",  # WEAK/MEDIUM/STRONG
        "reason": "12 日 EMA 上穿 26 日 EMA，价格位于 200 日均线上方",
        "pattern": "golden_cross",
        "previous_signal": {
            "action": "HOLD",
            "timestamp": "2024-03-14T08:00:00Z",
            "price": 23890.50
        }
    },
    
    "entry": {
        "type": "MARKET",  # MARKET/LIMIT/STOP
        "price": 24375.96,
        "limit_price": None,
        "stop_price": None,
        "valid_until": "2024-03-16T08:00:00Z",
        "urgency": "NORMAL"  # IMMEDIATE/NORMAL/PATIENT
    },
    
    "position": {
        "size_percent": 20.0,  # 占总资金百分比
        "size_usd": 20000.00,
        "leverage": 1,
        "max_position": 25.0  # 最大允许仓位
    },
    
    "risk": {
        "stop_loss": {
            "price": 22500.00,
            "type": "HARD",  # HARD/TRAILING/TIME
            "percent": -7.7,
            "atr_multiple": 2.0,
            "reason": "低于 200 日均线"
        },
        "take_profit": [
            {
                "level": 1,
                "price": 26500.00,
                "percent": 8.7,
                "size_percent": 50
            },
            {
                "level": 2,
                "price": 28000.00,
                "percent": 14.9,
                "size_percent": 50
            }
        ],
        "risk_reward_ratio": 2.3,  # R:R
        "risk_amount": 1540.00,  # 可能亏损金额
        "max_drawdown": -7.7,
        "expected_value": 0.15  # 期望值
    },
    
    "market_context": {
        "trend": {
            "short_term": "BULLISH",
            "medium_term": "NEUTRAL",
            "long_term": "BULLISH"
        },
        "volatility": {
            "level": "MEDIUM",
            "atr": 1250.50,
            "atr_percent": 5.1,
            "bb_width": 0.08
        },
        "momentum": {
            "rsi": 58.5,
            "macd": "BULLISH",
            "stochastic": 65.2
        },
        "volume": {
            "level": "HIGH",
            "ratio": 1.8,  # 相对均量
            "trend": "INCREASING"
        },
        "support_resistance": {
            "nearest_support": 23500.00,
            "nearest_resistance": 25000.00,
            "key_levels": [22000, 23500, 25000, 26500, 28000]
        }
    },
    
    "strategy_performance": {
        "win_rate": 52.5,
        "profit_factor": 1.85,
        "avg_win": 8.5,
        "avg_loss": 4.2,
        "consecutive_wins": 3,
        "consecutive_losses": 0,
        "last_10_trades": "+12.5%",
        "ytd_return": 18.3,
        "max_drawdown": -15.2,
        "sharpe_ratio": 1.15,
        "total_trades": 156
    },
    
    "portfolio_context": {
        "current_positions": [
            {
                "symbol": "ETH-USD",
                "direction": "LONG",
                "size_percent": 15,
                "pnl_percent": 5.2
            }
        ],
        "total_exposure": 35.0,  # 总仓位
        "available_margin": 65.0,
        "daily_pnl": 2.3,
        "monthly_pnl": 8.5
    },
    
    "compliance": {
        "max_risk_check": "PASS",  # 未超过单笔风险限制
        "correlation_check": "PASS",  # 与其他持仓相关性
        "news_check": "CLEAR",  # 无重大新闻
        "blackout_period": False,
        "warnings": []
    },
    
    "execution_notes": {
        "best_time": "开盘后 1 小时内",
        "liquidity": "HIGH",
        "estimated_slippage": 0.05,
        "estimated_commission": 0.02,
        "avoid_times": ["重大新闻发布前后"]
    },
    
    "metadata": {
        "generated_at": "2024-03-15T07:55:00Z",
        "expires_at": "2024-03-16T08:00:00Z",
        "model_version": "v2.1.0",
        "data_quality": "GOOD",
        "backtest_confidence": "HIGH"
    }
}

import json
print("\n完整 JSON 格式示例:")
print("-"*80)
print(json.dumps(complete_format, indent=2, ensure_ascii=False)[:3000] + "...")

print("\n\n" + "="*80)
print("简化版推送格式 (适合即时通知)")
print("="*80)

simplified_template = """
🔔 【{strategy_name}】{symbol} {action}

📅 时间：{timestamp}
💰 价格：${price:,.2f}
📊 方向：{direction}
🎯 类型：{signal_type}

💡 信号理由:
{reason}

📐 仓位建议:
├ 仓位：{position_size}% (${position_usd:,.0f})
├ 止损：${stop_loss:,.2f} (-{stop_pct}%)
├ 目标：${take_profit:,.2f} (+{take_profit_pct}%)
└ 盈亏比：{rr_ratio}:1

📈 信号质量:
├ 置信度：{confidence}%
├ 优先级：{priority}
└ 策略胜率：{win_rate}%

🌍 市场环境:
├ 趋势：{trend}
├ 波动率：{volatility}
└ 成交量：{volume_status}

📊 策略表现 (近 10 笔): {last_10_perf}
⚠️ 风险：单笔最大亏损 ${risk_amount:,.0f}

ID: {signal_id} | 有效期至：{valid_until}
"""

print(simplified_template.format(
    strategy_name="均线交叉",
    symbol="BTC-USD",
    action="做多",
    timestamp="2024-03-15 08:00",
    price=24375.96,
    direction="LONG 📈",
    signal_type="开仓",
    reason="12 日 EMA 上穿 26 日 EMA，价格站稳 200 日均线上方，成交量放大 80%",
    position_size=20,
    position_usd=20000,
    stop_loss=22500.00,
    stop_pct=7.7,
    take_profit=26500.00,
    take_profit_pct=8.7,
    rr_ratio=2.3,
    confidence=78.5,
    priority="高 🔴",
    win_rate=52.5,
    trend="多头",
    volatility="中等",
    volume_status="放量 📊",
    last_10_perf="+12.5% ✅",
    risk_amount=1540,
    signal_id="SIG-20240315-BTC-MA-001",
    valid_until="2024-03-16 08:00"
))
