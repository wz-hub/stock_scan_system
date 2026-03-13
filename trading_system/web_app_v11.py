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
    st.caption(f"数据更新：{get_beijing_time()}")
    st.markdown("---")
    
    # 从数据库加载信号
    @st.cache_data(ttl=60)
    def load_signals_from_db(limit=100):
        db_path = Path('cache/trading.db')
        if not db_path.exists():
            return []
        
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            query = f'''
                SELECT signal_id, symbol, timeframe, strategy_name, action, direction,
                       entry_price, stop_loss_price, take_profit_price, confidence,
                       reason, position_pct, status, ai_score, ai_direction, ai_reason,
                       timestamp, created_at
                FROM signals
                ORDER BY created_at DESC
                LIMIT {limit}
            '''
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.to_dict('records')
        except:
            return []
    
    signals = load_signals_from_db(100)
    
    if signals:
        # 统计
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("📊 总信号", len(signals))
        with col2:
            long_count = len([s for s in signals if s.get('direction') == 'LONG'])
            st.metric("🟢 做多", long_count)
        with col3:
            short_count = len([s for s in signals if s.get('direction') == 'SHORT'])
            st.metric("🔴 做空", short_count)
        with col4:
            agree_count = len([s for s in signals if s.get('ai_direction') == s.get('direction')])
            st.metric("🤝 AI 一致", agree_count)
        with col5:
            disagree_count = len([s for s in signals if s.get('ai_direction') not in [s.get('direction'), 'WAIT', None]])
            st.metric("⚠️ AI 分歧", disagree_count)
        
        st.markdown("---")
        
        # 筛选器
        with st.expander("🔍 筛选条件", expanded=False):
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            with filter_col1:
                all_symbols = list(set(s['symbol'] for s in signals))
                selected_symbol = st.selectbox("币种", ["全部"] + all_symbols)
            with filter_col2:
                all_strategies = list(set(s['strategy_name'] for s in signals))
                selected_strategy = st.selectbox("策略", ["全部"] + all_strategies)
            with filter_col3:
                ai_filter = st.selectbox("AI 判断", ["全部", "一致", "分歧", "AI 观望"])
        
        # 应用筛选
        filtered_signals = signals
        if selected_symbol != "全部":
            filtered_signals = [s for s in filtered_signals if s.get('symbol') == selected_symbol]
        if selected_strategy != "全部":
            filtered_signals = [s for s in filtered_signals if s.get('strategy_name') == selected_strategy]
        if ai_filter == "一致":
            filtered_signals = [s for s in filtered_signals if s.get('ai_direction') == s.get('direction')]
        elif ai_filter == "分歧":
            filtered_signals = [s for s in filtered_signals if s.get('ai_direction') not in [s.get('direction'), 'WAIT', None]]
        elif ai_filter == "AI 观望":
            filtered_signals = [s for s in filtered_signals if s.get('ai_direction') == 'WAIT']
        
        # 选项卡：表格清单 | 信号卡片
        tab1, tab2 = st.tabs(["📊 表格清单", "📋 信号卡片"])
        
        with tab1:
            st.subheader(f"📊 信号数据表格 ({len(filtered_signals)} 个)")
            
            if filtered_signals:
                # 转换为 DataFrame
                df_signals = pd.DataFrame(filtered_signals)
                
                # 格式化显示列
                display_df = df_signals.copy()
                display_df['价格'] = display_df['entry_price'].apply(lambda x: f"${x:,.4f}" if x < 1 else f"${x:,.2f}")
                display_df['置信度'] = display_df['confidence'].apply(lambda x: f"{x:.0f}%")
                display_df['时间'] = display_df['created_at'].apply(lambda x: str(x)[:10] if pd.notna(x) else '')
                
                # AI 判断列
                def get_ai_label(row):
                    ai_dir = row.get('ai_direction')
                    direction = row.get('direction')
                    score = row.get('ai_score', 0)
                    
                    if pd.isna(ai_dir) or ai_dir is None:
                        return "⚪ 未评分"
                    elif ai_dir == 'WAIT':
                        return f"⏸️ 观望 ({score}%)"
                    elif ai_dir == direction:
                        return f"✅ {ai_dir} ({score}%)"
                    else:
                        return f"❌ {ai_dir} ({score}%)"
                
                display_df['AI 判断'] = display_df.apply(get_ai_label, axis=1)
                
                # 选择显示的列
                show_cols = ['时间', 'symbol', 'strategy_name', 'direction', '价格', '置信度', 'AI 判断']
                
                # 重命名
                rename_map = {
                    'symbol': '币种',
                    'strategy_name': '策略',
                    'direction': '方向',
                    'entry_price': '价格',
                    'confidence': '置信度',
                    'created_at': '时间'
                }
                display_df = display_df.rename(columns=rename_map)
                
                # 显示表格
                st.dataframe(
                    display_df[[rename_map.get(col, col) for col in show_cols if rename_map.get(col, col) in display_df.columns]],
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
        
        with tab2:
            st.subheader(f"📋 信号卡片详情 ({len(filtered_signals)} 个)")
            
            # 显示信号卡片
            for signal in filtered_signals[:20]:  # 只显示最新 20 个
                action = signal.get('action', 'BUY')
                priority = signal.get('priority', 'MEDIUM')
                strategy = signal.get('strategy_name', 'Unknown')
                symbol = signal.get('symbol', 'N/A')
                price = signal.get('entry_price', 0)
                confidence = signal.get('confidence', 0)
                timestamp = signal.get('created_at', '')[:16].replace('T', ' ')
                reason = signal.get('reason', 'N/A')
                stop_loss = signal.get('stop_loss_price', 0)
                take_profit = signal.get('take_profit_price', 0)
                rr = signal.get('risk_reward_ratio', 0)
            
            action_emoji = "🟢" if action == "BUY" else "🔴"
            direction = signal.get('direction', 'LONG')
            ai_score = signal.get('ai_score')
            ai_direction = signal.get('ai_direction')
            ai_reason = signal.get('ai_reason', '')
            
            # 判断 AI 一致性
            ai_status = "unknown"
            if ai_direction:
                if ai_direction == 'WAIT':
                    ai_status = "wait"
                elif ai_direction == direction:
                    ai_status = "agree"
                else:
                    ai_status = "disagree"
            
            with st.container():
                st.markdown(f"### {action_emoji}【{strategy}】{symbol} {direction}")
                
                # AI 状态标识
                if ai_status == "agree":
                    st.markdown('<span style="background: linear-gradient(135deg, #1b5e20, #2e7d32); padding: 5px 10px; border-radius: 5px; display: inline-block; font-weight: bold; margin-bottom: 10px;">✅ AI 同意</span>', unsafe_allow_html=True)
                elif ai_status == "disagree":
                    st.markdown(f'<span style="background: linear-gradient(135deg, #b71c1c, #c62828); padding: 5px 10px; border-radius: 5px; display: inline-block; font-weight: bold; margin-bottom: 10px;">❌ AI 反对 ({ai_direction})</span>', unsafe_allow_html=True)
                elif ai_status == "wait":
                    st.markdown('<span style="background: linear-gradient(135deg, #f57f17, #f9a825); padding: 5px 10px; border-radius: 5px; display: inline-block; font-weight: bold; margin-bottom: 10px;">⏸️ AI 观望</span>', unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("💰 价格", f"${price:,.4f}" if price < 1 else f"${price:,.2f}")
                with col2:
                    st.metric("📈 置信度", f"{confidence:.0f}%")
                with col3:
                    st.metric("📅 时间", timestamp[:10])
                with col4:
                    if ai_score:
                        st.metric("🤖 AI 评分", f"{ai_score}%")
                    else:
                        st.metric("🤖 AI 评分", "未评分")
                
                # 信号理由
                with st.expander("💡 信号理由", expanded=False):
                    st.write(reason)
                
                # AI 理由
                if ai_reason:
                    with st.expander("🤖 AI 分析", expanded=False):
                        st.write(ai_reason)
                
                st.markdown("**📐 风险管理**")
                risk_col1, risk_col2, risk_col3 = st.columns(3)
                with risk_col1:
                    st.error(f"🛑 止损\n${stop_loss:,.4f}" if stop_loss < 1 else f"🛑 止损\n${stop_loss:,.2f}")
                with risk_col2:
                    st.success(f"🎯 止盈\n${take_profit:,.4f}" if take_profit < 1 else f"🎯 止盈\n${take_profit:,.2f}")
                with risk_col3:
                    st.metric("📊 盈亏比", f"{rr}:1")
                
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
