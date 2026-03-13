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
    ["📡 信号中心", "📈 准确率统计", "📊 K 线图", "💰 资金流向", "⚙️ 设置"],
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
                
                # 格式化并选择要显示的列
                display_df = pd.DataFrame()
                display_df['时间'] = df_signals['created_at'].apply(lambda x: str(x)[:10] if pd.notna(x) else '')
                display_df['币种'] = df_signals['symbol']
                display_df['策略'] = df_signals['strategy_name']
                display_df['方向'] = df_signals['direction']
                display_df['价格'] = df_signals['entry_price'].apply(lambda x: f"${x:,.4f}" if x < 1 else f"${x:,.2f}")
                display_df['置信度'] = df_signals['confidence'].apply(lambda x: f"{x:.0f}%")
                
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
                
                display_df['AI 判断'] = df_signals.apply(get_ai_label, axis=1)
                
                # 显示表格
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
        
        with tab2:
            st.subheader(f"📋 信号卡片详情 ({len(filtered_signals)} 个)")
            
            # 显示信号卡片
            if not filtered_signals:
                st.info("暂无信号数据")
            else:
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

elif page == "📈 准确率统计":
    st.title("📈 准确率统计 - 策略 vs AI")
    st.caption(f"数据更新：{get_beijing_time()}")
    st.markdown("---")
    
    # 导入统计模块
    try:
        from scripts.signal_stats import SignalStats
        stats = SignalStats()
        
        # 时间选择
        days = st.sidebar.selectbox("统计周期", [7, 14, 30, 60, 90], index=2)
        
        # 选项卡
        tab1, tab2, tab3 = st.tabs(["📊 策略统计", "🤖 AI 统计", "⚖️ 对比分析"])
        
        with tab1:
            st.subheader(f"📊 策略表现统计 (最近 {days} 天)")
            
            strategy_stats = stats.calculate_strategy_stats(days)
            
            if strategy_stats:
                # 转换为 DataFrame
                df_stats = pd.DataFrame([
                    {
                        '策略': name,
                        '总信号数': s['total'],
                        '盈利': s['win'],
                        '亏损': s['loss'],
                        '胜率': f"{s['win_rate']:.1f}%",
                        '平均盈亏': f"{s['avg_pnl']:+.2f}%",
                        '总盈亏': f"{s['total_pnl']:+.2f}%"
                    }
                    for name, s in strategy_stats.items()
                ])
                
                # 按胜率排序
                df_stats = df_stats.sort_values('胜率', ascending=False)
                
                # 显示表格
                st.dataframe(
                    df_stats,
                    use_container_width=True,
                    hide_index=True,
                    height=400
                )
                
                # 最佳策略
                if not df_stats.empty:
                    best = df_stats.iloc[0]
                    st.success(f"🏆 最佳策略：**{best['策略']}** - 胜率 {best['胜率']}, 总盈亏 {best['总盈亏']}")
            else:
                st.warning("⚠️ 暂无已平仓信号数据")
                st.info("""
                **💡 说明**: 
                
                准确率统计需要信号平仓后才会计算。
                
                **当前状态**:
                - 所有信号都是 OPEN（活跃）状态
                - 等待信号触发止盈止损
                
                **如何生成数据**:
                1. 等待信号自然平仓（推荐）
                2. 信号跟踪模块会自动检查止盈止损
                3. 一般几小时到几天内会有平仓信号
                """)
        
        with tab2:
            st.subheader(f"🤖 AI 表现统计 (最近 {days} 天)")
            
            ai_stats = stats.calculate_ai_stats(days)
            
            if ai_stats and 'overall' in ai_stats:
                overall = ai_stats['overall']
                
                # 总体统计卡片
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("总判断数", overall['total'])
                with col2:
                    st.metric("正确", overall['correct'])
                with col3:
                    st.metric("错误", overall['wrong'])
                with col4:
                    st.metric("准确率", f"{overall['accuracy']:.1f}%")
                
                st.metric("平均置信度", f"{overall['avg_confidence']:.1f}%")
                
                st.markdown("---")
                
                # 按方向统计
                if 'by_direction' in ai_stats and ai_stats['by_direction']:
                    st.subheader("按方向统计")
                    
                    for direction, dir_stats in ai_stats['by_direction'].items():
                        emoji = "🟢" if direction == "LONG" else "🔴" if direction == "SHORT" else "⏸️"
                        st.markdown(f"### {emoji} {direction}")
                        
                        dir_col1, dir_col2, dir_col3 = st.columns(3)
                        with dir_col1:
                            st.metric("判断数", dir_stats['total'])
                        with dir_col2:
                            st.metric("正确", dir_stats['correct'])
                        with dir_col3:
                            st.metric("准确率", f"{dir_stats['accuracy']:.1f}%")
                        
                        st.markdown(f"平均置信度：{dir_stats['avg_confidence']:.1f}%")
                        st.divider()
            else:
                st.info("暂无 AI 评分数据")
        
        with tab3:
            st.subheader("⚖️ 策略 vs AI 对比分析")
            
            comp_stats = stats.get_comparison_stats(days)
            
            if comp_stats and 'agreement' in comp_stats:
                agree = comp_stats['agreement']
                
                # 一致性统计
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总信号数", agree['total'])
                with col2:
                    st.metric("策略&AI 一致", agree['agree'])
                with col3:
                    st.metric("策略&AI 分歧", agree['disagree'])
                
                st.markdown("---")
                
                # 胜率对比
                st.subheader("胜率对比")
                
                agree_col, disagree_col = st.columns(2)
                with agree_col:
                    st.success(f"✅ 一致时胜率：**{agree['agree_win_rate']:.1f}%**")
                    st.caption(f"基于 {agree['agree']} 个信号")
                with disagree_col:
                    st.error(f"❌ 分歧时胜率：**{agree['disagree_win_rate']:.1f}%**")
                    st.caption(f"基于 {agree['disagree']} 个信号")
                
                # 结论
                st.markdown("---")
                st.subheader("📊 分析结论")
                
                if agree['agree_win_rate'] > agree['disagree_win_rate']:
                    st.info("""
                    **💡 建议**: 当策略和 AI 判断一致时，胜率更高！
                    
                    可以考虑：
                    - 只在策略和 AI 一致时交易
                    - 一致时增加仓位
                    - 分歧时减少仓位或观望
                    """)
                else:
                    st.info("""
                    **💡 观察**: 分歧时胜率反而更高，值得深入研究！
                    
                    可能原因：
                    - AI 看到了策略没看到的因素
                    - 策略参数需要优化
                    - 样本量不足
                    """)
            else:
                st.info("暂无对比数据")
    
    except Exception as e:
        st.error(f"加载统计失败：{e}")
        st.info("提示：需要有一定数量的已平仓信号才能生成统计")

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
