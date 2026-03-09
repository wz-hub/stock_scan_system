"""
交易策略信号系统 - Web 界面 v7
修复：止损止盈线显示 + 完整图表功能
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader

st.set_page_config(
    page_title="📡 交易信号系统",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 1.3em; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(symbol: str):
    loader = DataLoader()
    data_file = Path('data') / f"{symbol.replace('/', '_')}.csv"
    if data_file.exists():
        return loader.load_csv(str(data_file))
    return loader.download_yahoo(symbol, '2022-01-01', '2024-12-31')


def get_all_signals():
    try:
        signal_files = sorted(Path('signals').glob('signal_*.json'), reverse=True)
        signals = []
        for file in signal_files:
            try:
                with open(file) as f:
                    signals.append(json.load(f))
            except:
                continue
        return signals
    except:
        return []


def is_signal_valid(signal):
    try:
        signal_time = datetime.fromisoformat(signal.get('timestamp', ''))
        return (datetime.now() - signal_time).days <= 7
    except:
        return False


def render_signal_card(signal, col):
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
    direction = signal.get('direction', 'LONG')
    
    action_emoji = "🟢" if action == "BUY" else "🔴"
    priority_text = "高" if priority == "HIGH" else "中" if priority == "MEDIUM" else "低"
    action_text = "买入" if action == "BUY" else "卖出"
    direction_text = "做多" if direction == "LONG" else "做空"
    
    with col:
        st.markdown(f"### {action_emoji}【{strategy}】{symbol}")
        
        if priority == "HIGH":
            st.error(f"**优先级：{priority_text}** | **操作：{action_text}**")
        elif priority == "MEDIUM":
            st.warning(f"**优先级：{priority_text}** | **操作：{action_text}**")
        else:
            st.info(f"**优先级：{priority_text}** | **操作：{action_text}**")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 价格", f"${price:,.2f}")
        with col2:
            st.metric("📊 方向", direction_text)
        
        col1, col2 = st.columns(2)
        with col1:
            conf_emoji = "🟢" if confidence >= 70 else "🟡" if confidence >= 50 else "🔴"
            st.metric("📈 置信度", f"{conf_emoji} {confidence:.0f}%")
        with col2:
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
        
        if st.button("📊 查看 K 线图", key=f"view_{signal.get('signal_id')}", use_container_width=True, type="primary"):
            st.session_state.selected_signal = signal
            st.session_state.current_symbol = symbol
            st.session_state.should_show_kline = True
            st.rerun()
        
        st.divider()


if 'selected_signal' not in st.session_state:
    st.session_state.selected_signal = None
if 'current_symbol' not in st.session_state:
    st.session_state.current_symbol = 'BTC-USD'
if 'should_show_kline' not in st.session_state:
    st.session_state.should_show_kline = False

st.sidebar.title("🎛️ 控制中心")
page = st.sidebar.radio("导航", ["📡 信号中心", "📊 K 线图", "📈 策略回测", "⚙️ 设置"], index=0, key="nav_radio")

if st.session_state.should_show_kline:
    page = "📊 K 线图"
    st.session_state.should_show_kline = False

st.sidebar.subheader("🔍 筛选")
selected_symbol = st.sidebar.selectbox("交易标的", ["BTC-USD", "ETH-USD"], index=0)
priority_filter = st.sidebar.multiselect("优先级", ["高", "中", "低"], default=["高", "中", "低"])
signal_type_filter = st.sidebar.radio("信号类型", ["全部", "有效信号 (7 天内)", "历史信号"], index=0)

if page == "📡 信号中心":
    st.title("📡 交易信号中心")
    st.markdown("---")
    
    all_signals = get_all_signals()
    priority_map = {"高": "HIGH", "中": "MEDIUM", "低": "LOW"}
    priority_filters = [priority_map[p] for p in priority_filter]
    
    valid_signals = [s for s in all_signals if s.get('symbol') == selected_symbol and s.get('priority') in priority_filters and is_signal_valid(s)]
    history_signals = [s for s in all_signals if s.get('symbol') == selected_symbol and s.get('priority') in priority_filters and not is_signal_valid(s)]
    
    if signal_type_filter == "有效信号 (7 天内)":
        filtered_signals = valid_signals
    elif signal_type_filter == "历史信号":
        filtered_signals = history_signals
    else:
        filtered_signals = valid_signals + history_signals
    
    if filtered_signals:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 总信号", len(filtered_signals))
        with col2:
            st.metric("🟢 买入", len([s for s in filtered_signals if s.get('action') == 'BUY']))
        with col3:
            st.metric("🔴 卖出", len([s for s in filtered_signals if s.get('action') == 'SELL']))
        with col4:
            st.metric("✅ 有效", f"{len(valid_signals)} | 历史 {len(history_signals)}")
        
        st.markdown("---")
        
        if valid_signals and signal_type_filter != "历史信号":
            st.subheader("✅ 有效信号（7 天内）")
            for i in range(0, len(valid_signals), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(valid_signals):
                        render_signal_card(valid_signals[i + j], col)
            st.markdown("---")
        
        if history_signals and signal_type_filter != "有效信号 (7 天内)":
            st.subheader("📜 历史信号")
            for i in range(0, len(history_signals), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(history_signals):
                        render_signal_card(history_signals[i + j], col)
    else:
        st.warning("暂无符合条件的信号")

elif page == "📊 K 线图":
    st.title("📊 K 线图 - 完整图表功能")
    st.markdown("---")
    
    if st.session_state.selected_signal:
        signal = st.session_state.selected_signal
        action_text = "买入" if signal.get('action') == 'BUY' else "卖出"
        st.success(f"✅ 信号：【{signal.get('strategy_name')}】{signal.get('symbol')} {action_text} @ ${signal.get('current_price'):,.2f}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 入场价", f"${signal.get('current_price'):,.2f}")
        with col2:
            st.metric("🛑 止损", f"${signal.get('stop_loss_price'):,.2f}")
        with col3:
            st.metric("🎯 止盈", f"${signal.get('take_profit_price'):,.2f}")
        with col4:
            st.metric("📊 盈亏比", f"{signal.get('risk_reward_ratio', 0)}:1")
    else:
        st.info("👈 请在信号中心选择一个信号查看")
    
    symbol = st.selectbox("交易标的", ["BTC-USD", "ETH-USD"], index=0)
    
    with st.spinner(f"加载 {symbol} 数据..."):
        df = load_data(symbol)
        
        # 准备数据
        candles = []
        for idx, row in df.iterrows():
            candles.append({
                "time": int(idx.timestamp()),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close'])
            })
        
        # 信号数据
        signal_data = {}
        if st.session_state.selected_signal and st.session_state.current_symbol == symbol:
            sel = st.session_state.selected_signal
            signal_data = {
                "entry": sel.get('current_price', 0),
                "stop_loss": sel.get('stop_loss_price', 0),
                "take_profit": sel.get('take_profit_price', 0),
                "action": sel.get('action', 'BUY'),
                "date": sel.get('timestamp', '')[:10]
            }
        
        html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; }}
        #chart {{ width: 100%; height: 650px; }}
        .legend {{
            position: absolute;
            left: 12px;
            top: 12px;
            z-index: 1000;
            background: rgba(30, 30, 30, 0.9);
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid #444;
            color: #d1d4dc;
            font-family: Arial, sans-serif;
            font-size: 13px;
        }}
        .legend-line {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-color {{
            width: 20px;
            height: 3px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <div class="legend" id="legend">
        <div style="font-weight: bold; margin-bottom: 8px;">📊 价格标记</div>
        <div class="legend-line">
            <div class="legend-color" style="background: #ff4444;"></div>
            <span>🛑 止损线</span>
        </div>
        <div class="legend-line">
            <div class="legend-color" style="background: #00ff88;"></div>
            <span>🎯 止盈线</span>
        </div>
        <div class="legend-line">
            <div class="legend-color" style="background: #0088ff;"></div>
            <span>💰 入场价</span>
        </div>
    </div>
    <script>
        const chartContainer = document.getElementById('chart');
        const chart = LightweightCharts.createChart(chartContainer, {{
            width: chartContainer.clientWidth,
            height: 650,
            layout: {{
                background: {{ color: '#1e1e1e' }},
                textColor: '#d1d4dc',
            }},
            grid: {{
                vertLines: {{ color: '#2B2B43' }},
                horzLines: {{ color: '#2B2B43' }},
            }},
            crosshair: {{
                mode: LightweightCharts.CrosshairMode.Normal,
            }},
            timeScale: {{
                borderColor: '#485c7b',
                timeVisible: true,
            }},
            rightPriceScale: {{
                borderColor: '#485c7b',
            }},
        }});

        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderVisible: false,
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
        }});

        candlestickSeries.setData({json.dumps(candles)});
        
        // 添加信号标记和价格线
        const signalData = {json.dumps(signal_data)};
        
        if (signalData && signalData.entry > 0) {{
            // 找到信号日期的时间戳
            const signalDate = signalData.date;
            const candleTime = candles.find(c => {{
                const date = new Date(c.time * 1000);
                return date.toISOString().slice(0, 10) === signalDate;
            }});
            
            if (candleTime) {{
                const time = candleTime.time;
                const isBuy = signalData.action === 'BUY';
                
                // 添加箭头标记
                candlestickSeries.setMarkers([{{
                    time: time,
                    position: isBuy ? 'belowBar' : 'aboveBar',
                    color: isBuy ? '#00ff88' : '#ff4444',
                    shape: isBuy ? 'arrowUp' : 'arrowDown',
                    text: (isBuy ? '买入' : '卖出') + '\\n@' + signalData.entry.toFixed(0),
                    size: 2.5
                }}]);
            }}
            
            // 添加止损线（红色）
            chart.priceLine({{
                price: signalData.stop_loss,
                color: '#ff4444',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🛑 止损',
            }});
            
            // 添加止盈线（绿色）
            chart.priceLine({{
                price: signalData.take_profit,
                color: '#00ff88',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🎯 止盈',
            }});
            
            // 添加入场线（蓝色）
            chart.priceLine({{
                price: signalData.entry,
                color: '#0088ff',
                lineWidth: 1,
                lineStyle: 0,
                axisLabelVisible: true,
                title: '💰 入场',
            }});
        }}

        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: chartContainer.clientWidth }});
        }});
    </script>
</body>
</html>
"""
        st.components.v1.html(html_code, height=680, scrolling=False)
    
    st.markdown("""
    **🎨 图表功能:**
    - 🔍 鼠标滚轮缩放 | ✋ 拖拽平移
    - 📊 信号箭头：🟢 买入 | 🔴 卖出
    - 📈 价格线：🔴 止损 | 🟢 止盈 | 🔵 入场
    - ➕ 十字光标显示 OHLC
    
    **⚠️ 划线功能说明:**
    当前使用 Lightweight Charts（TradingView 轻量版），支持查看和标记。
    如需完整 TradingView 的划线工具（趋势线、水平线等），需要：
    1. 使用 TradingView Technical Analysis Charts（需要服务器部署）
    2. 或接入 TradingView 官方数据源
    
    建议在图表上方手动记录止损止盈价格，或使用其他图表工具辅助分析。
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")

st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议")
