"""
交易策略信号系统 - Web 界面 v11 (整合版)
- 📡 信号中心
- 📊 K 线图 (TradingView)
- 💰 资金流向排行榜
- 📈 策略回测
- ⚙️ 设置
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz

# 北京时间时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader
from money_flow import MoneyFlowMonitor, format_money_value

st.set_page_config(
    page_title="📡 交易信号系统",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 1.3em; }
    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #ff4444, #cc0000);
        color: white;
        padding: 6px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85em;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=180)  # 3 分钟缓存
def get_money_flow_data():
    """获取资金流向数据（3 分钟缓存）"""
    monitor = MoneyFlowMonitor()
    return monitor.get_money_flow_ranking(top_n=50)


# 侧边栏导航
st.sidebar.title("🎛️ 导航")
page = st.sidebar.radio(
    "页面",
    ["📡 信号中心", "📊 K 线图", "💰 资金流向", "⚙️ 设置"],
    index=0,
    key="nav_radio"
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 系统状态")
st.sidebar.info("""
✅ 信号扫描：每小时  
✅ 资金流向：每 5 分钟  
✅ 飞书推送：已启用  
✅ AI 评分：已配置  
""")

# 主界面
if page == "📡 信号中心":
    st.title("📡 交易信号中心")
    st.markdown("---")
    
    # 加载信号
    signals_dir = Path('signals')
    signal_files = sorted(signals_dir.glob('signal_*.json'), reverse=True)
    
    if signal_files:
        signals = []
        for file in signal_files[:50]:  # 最近 50 个
            try:
                with open(file) as f:
                    signals.append(json.load(f))
            except:
                continue
        
        # 统计
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 总信号", len(signals))
        with col2:
            buy_count = len([s for s in signals if s.get('action') == 'BUY'])
            st.metric("🟢 买入", buy_count)
        with col3:
            sell_count = len([s for s in signals if s.get('action') == 'SELL'])
            st.metric("🔴 卖出", sell_count)
        with col4:
            high_priority = len([s for s in signals if s.get('priority') == 'HIGH'])
            st.metric("🔴 高优先级", high_priority)
        
        st.markdown("---")
        
        # 显示信号卡片
        for signal in signals[:20]:  # 只显示最新 20 个
            action = signal.get('action', 'BUY')
            priority = signal.get('priority', 'MEDIUM')
            strategy = signal.get('strategy_name', 'Unknown')
            symbol = signal.get('symbol', 'N/A')
            price = signal.get('current_price', 0)
            confidence = signal.get('confidence', 0)
            timestamp = signal.get('timestamp', '')[:16].replace('T', ' ')
            reason = signal.get('reason', 'N/A')
            stop_loss = signal.get('stop_loss_price', 0)
            take_profit = signal.get('take_profit_price', 0)
            rr = signal.get('risk_reward_ratio', 0)
            
            action_emoji = "🟢" if action == "BUY" else "🔴"
            priority_text = "高" if priority == "HIGH" else "中" if priority == "MEDIUM" else "低"
            
            with st.container():
                st.markdown(f"### {action_emoji}【{strategy}】{symbol}")
                
                if priority == "HIGH":
                    st.error(f"**优先级：{priority_text}** | **操作：{action}**")
                elif priority == "MEDIUM":
                    st.warning(f"**优先级：{priority_text}** | **操作：{action}**")
                else:
                    st.info(f"**优先级：{priority_text}** | **操作：{action}**")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("💰 价格", f"${price:,.2f}")
                with col2:
                    st.metric("📈 置信度", f"{confidence:.0f}%")
                with col3:
                    st.metric("📅 时间", timestamp[:10])
                
                st.markdown("**💡 信号理由**")
                st.info(reason)
                
                st.markdown("**📐 风险管理**")
                risk_col1, risk_col2, risk_col3 = st.columns(3)
                with risk_col1:
                    st.error(f"🛑 止损\n${stop_loss:,.2f}")
                with risk_col2:
                    st.success(f"🎯 止盈\n${take_profit:,.2f}")
                with risk_col3:
                    st.metric("📊 盈亏比", f"{rr}:1")
                
                # AI 评分
                ai_score = signal.get('ai_score')
                if ai_score:
                    score_color = "🟢" if ai_score >= 80 else "🟡" if ai_score >= 70 else "🔴"
                    st.markdown(f"**🤖 AI 评分:** {score_color} **{ai_score}/100**")
                
                st.divider()
    
    else:
        st.warning("暂无信号，等待下次扫描...")
        st.info("下次扫描时间：下一个整点")

elif page == "📊 K 线图":
    st.title("📊 K 线图 - TradingView")
    st.markdown("---")
    
    st.markdown('<span class="live-badge">🔴 实时行情</span>', unsafe_allow_html=True)
    
    symbol = st.selectbox("交易标的", ["BTC-USD", "ETH-USD"], index=0)
    
    # TradingView Widget
    tv_symbol = {
        "BTC-USD": "COINBASE:BTCUSD",
        "ETH-USD": "COINBASE:ETHUSD"
    }.get(symbol, f"COINBASE:{symbol.replace('-', '')}")
    
    tv_widget_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; }}
        #tv_chart {{ width: 100%; height: 700px; }}
    </style>
</head>
<body>
    <div id="tv_chart"></div>
    <script type="text/javascript">
    new TradingView.widget({{
        "width": "100%",
        "height": 700,
        "symbol": "{tv_symbol}",
        "interval": "D",
        "timezone": "Asia/Shanghai",
        "theme": "dark",
        "style": "1",
        "locale": "zh_CN",
        "toolbar_bg": "#1e1e1e",
        "enable_publishing": false,
        "hide_top_toolbar": false,
        "save_image": true,
        "container_id": "tv_chart",
        "studies": ["Volume@tv-basicstudies"],
        "allow_symbol_change": true,
        "overrides": {{
            "mainSeriesProperties.candleStyle.upColor": "#00ff88",
            "mainSeriesProperties.candleStyle.downColor": "#ff4444"
        }}
    }});
    </script>
</body>
</html>
"""
    
    st.components.v1.html(tv_widget_html, height=730, scrolling=False)
    
    st.markdown("""
    **🎨 TradingView 功能:**
    - ⏱️ 时间周期切换（点击顶部 D）
    - ✏️ 划线工具（点击左侧工具栏）
    - 📈 技术指标（点击 fx）
    - 🔍 缩放平移
    """)

elif page == "💰 资金流向":
    st.title("💰 全市场资金流向排行榜")
    st.caption(f"数据更新：{get_beijing_time()} | 数据源：Binance 24h 行情")
    
    st.markdown("---")
    
    # 获取数据
    with st.spinner("💰 加载资金流向数据..."):
        ranking = get_money_flow_data()
    
    if not ranking['inflow_top20']:
        st.error("❌ 获取数据失败，请稍后刷新")
        st.stop()
    
    # 选项卡
    tab1, tab2, tab3, tab4 = st.tabs(["🟢 净流入 Top20", "🔴 净流出 Top20", "📈 涨幅 Top20", "📉 跌幅 Top20"])
    
    with tab1:
        st.subheader("🟢 资金净流入 Top20")
        
        df_inflow = pd.DataFrame(ranking['inflow_top20'])
        
        display_df = df_inflow.copy()
        display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
        display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
        display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(
            display_df[['symbol_short', '净流量', '24h 成交量', '24h 涨跌', 'price']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol_short": "合约",
                "净流量": st.column_config.TextColumn("净流量"),
                "24h 成交量": st.column_config.TextColumn("24h 成交量"),
                "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
                "price": st.column_config.NumberColumn("价格", format="$%.4f")
            }
        )
    
    with tab2:
        st.subheader("🔴 资金净流出 Top20")
        
        df_outflow = pd.DataFrame(ranking['outflow_top20'])
        
        display_df = df_outflow.copy()
        display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
        display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
        display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(
            display_df[['symbol_short', '净流量', '24h 成交量', '24h 涨跌', 'price']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol_short": "合约",
                "净流量": st.column_config.TextColumn("净流量"),
                "24h 成交量": st.column_config.TextColumn("24h 成交量"),
                "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
                "price": st.column_config.NumberColumn("价格", format="$%.4f")
            }
        )
    
    with tab3:
        st.subheader("📈 24h 涨幅 Top20")
        
        df_pct_in = pd.DataFrame(ranking['pct_inflow_top20'])
        
        display_df = df_pct_in.copy()
        display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
        display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
        display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(
            display_df[['symbol_short', '24h 涨跌', '净流量', '24h 成交量', 'price']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol_short": "合约",
                "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
                "净流量": st.column_config.TextColumn("净流量"),
                "24h 成交量": st.column_config.TextColumn("24h 成交量"),
                "price": st.column_config.NumberColumn("价格", format="$%.4f")
            }
        )
    
    with tab4:
        st.subheader("📉 24h 跌幅 Top20")
        
        df_pct_out = pd.DataFrame(ranking['pct_outflow_top20'])
        
        display_df = df_pct_out.copy()
        display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
        display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
        display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
        
        st.dataframe(
            display_df[['symbol_short', '24h 涨跌', '净流量', '24h 成交量', 'price']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "symbol_short": "合约",
                "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
                "净流量": st.column_config.TextColumn("净流量"),
                "24h 成交量": st.column_config.TextColumn("24h 成交量"),
                "price": st.column_config.NumberColumn("价格", format="$%.4f")
            }
        )
    
    # 底部统计
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 扫描币种", len(ranking['all_data']))
    with col2:
        total_inflow = sum(item['net_flow'] for item in ranking['inflow_top20'])
        st.metric("🟢 净流入总额", format_money_value(total_inflow))
    with col3:
        total_outflow = abs(sum(item['net_flow'] for item in ranking['outflow_top20']))
        st.metric("🔴 净流出总额", format_money_value(total_outflow))

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    
    # AI 配置
    st.subheader("🤖 AI 大模型配置")
    
    from ai_scorer import AIScorer
    scorer = AIScorer()
    
    with st.form("ai_config_form"):
        ai_enabled = st.checkbox("启用 AI 评分", value=scorer.enabled)
        ai_api_url = st.text_input("API 地址", value=scorer.config.get('api_url', ''))
        ai_api_key = st.text_input("API Key", value=scorer.config.get('api_key', ''), type="password")
        ai_model = st.selectbox("模型", ["qwen3.5-plus", "qwen3.5-turbo", "qwen-plus"], index=0)
        ai_temp = st.slider("温度参数", 0.0, 1.0, scorer.config.get('temperature', 0.3), 0.1)
        
        submit_ai = st.form_submit_button("💾 保存 AI 配置")
        
        if submit_ai:
            new_config = {
                "enabled": ai_enabled,
                "api_url": ai_api_url,
                "api_key": ai_api_key,
                "model": ai_model,
                "temperature": ai_temp,
                "max_tokens": 1000
            }
            scorer.save_config(new_config)
            st.success("✅ AI 配置已保存！")
    
    # 飞书推送
    st.markdown("---")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")
    
    # 定时任务
    st.markdown("---")
    st.subheader("⏰ 定时任务")
    st.info("""
    **扫描频率:**
    - 信号扫描：每小时整点
    - 资金流向：每 5 分钟
    - 扫描标的：基础币种 + 流入 Top20 + 流出 Top20
    
    **查看日志:**
    - 扫描日志：`tail -f /tmp/signals_scan.log`
    - 资金流向：`tail -f /tmp/money_flow.log`
    """)

# 底部
st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议")
