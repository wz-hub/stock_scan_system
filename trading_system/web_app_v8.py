"""
交易策略信号系统 - Web 界面 v8
- 集成实时 K 线数据（Binance）
- 支持加密货币实时价格
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from realtime_data import get_realtime_data, get_realtime_price, RealtimeData
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
    .live-badge {
        display: inline-block;
        background: #ff4444;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.6; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)  # 60 秒缓存
def load_realtime_kline(symbol: str, days: int = 500):
    """加载实时 K 线（带缓存）"""
    rt = RealtimeData()
    
    # 转换符号
    binance_symbol = symbol.replace("-", "").replace(".USD", "USDT")
    if not binance_symbol.endswith("USDT"):
        binance_symbol = binance_symbol + "USDT"
    
    # 根据时间范围选择周期
    if days <= 5:
        interval = "5m"
        limit = min(days * 24 * 12, 1000)  # 5 分钟 K 线
    elif days <= 30:
        interval = "1h"
        limit = min(days * 24, 1000)
    else:
        interval = "1d"
        limit = min(days, 1000)
    
    df = rt.get_binance_klines(binance_symbol, interval, limit)
    
    if df.empty:
        # 回退到本地数据
        loader = DataLoader()
        data_file = Path('data') / f"{symbol.replace('/', '_')}.csv"
        if data_file.exists():
            df = loader.load_csv(str(data_file))
            st.warning("⚠️ 实时数据不可用，使用本地历史数据")
    
    return df


@st.cache_data(ttl=30)  # 30 秒缓存
def get_live_price(symbol: str):
    """获取实时价格"""
    return get_realtime_price(symbol)


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

# 实时价格显示
if selected_symbol:
    live_price = get_live_price(selected_symbol)
    if live_price:
        st.sidebar.success(f"""
        💰 **{selected_symbol} 实时价格**
        
        ${live_price.get('price', 0):,.2f}
        
        24h: {live_price.get('change_24h', 0):+.2f}%
        """)

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
    st.title("📊 K 线图 - 实时数据")
    st.markdown("---")
    
    # 显示实时价格标签
    st.markdown('<span class="live-badge">🔴 实时数据</span>', unsafe_allow_html=True)
    
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
    
    # 显示当前价格
    live_price = get_live_price(symbol)
    if live_price:
        st.metric(
            "💰 实时价格", 
            f"${live_price.get('price', 0):,.2f}",
            delta=f"{live_price.get('change_24h', 0):+.2f}%"
        )
    
    with st.spinner(f"加载 {symbol} 实时 K 线..."):
        df = load_realtime_kline(symbol, days=500)
        
        if df.empty:
            st.error("❌ 无法加载 K 线数据，请检查网络连接")
        else:
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
    </style>
</head>
<body>
    <div id="chart"></div>
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
        }});

        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderVisible: false,
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
        }});

        candlestickSeries.setData({json.dumps(candles)});
        
        const signalData = {json.dumps(signal_data)};
        
        if (signalData && signalData.entry > 0) {{
            const signalDate = signalData.date;
            const candleTime = candles.find(c => {{
                const date = new Date(c.time * 1000);
                return date.toISOString().slice(0, 10) === signalDate;
            }});
            
            if (candleTime) {{
                const time = candleTime.time;
                const isBuy = signalData.action === 'BUY';
                
                candlestickSeries.setMarkers([{{
                    time: time,
                    position: isBuy ? 'belowBar' : 'aboveBar',
                    color: isBuy ? '#00ff88' : '#ff4444',
                    shape: isBuy ? 'arrowUp' : 'arrowDown',
                    text: (isBuy ? '买入' : '卖出') + '\\n@' + signalData.entry.toFixed(0),
                    size: 2.5
                }}]);
            }}
            
            chart.priceLine({{
                price: signalData.stop_loss,
                color: '#ff4444',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🛑 止损',
            }});
            
            chart.priceLine({{
                price: signalData.take_profit,
                color: '#00ff88',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🎯 止盈',
            }});
            
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
    **📊 实时数据说明:**
    - 数据来源：Binance API
    - 更新频率：每 60 秒自动刷新
    - 支持：BTC/USD, ETH/USD 等加密货币
    - K 线周期：根据时间范围自动选择（5 分钟/1 小时/1 天）
    
    **🔄 刷新数据:**
    点击侧边栏的筛选条件或刷新页面获取最新数据。
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")

st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议 | 实时数据由 Binance 提供")
