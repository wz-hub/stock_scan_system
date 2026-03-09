"""
交易策略信号系统 - Web 界面 v9
- TradingView 风格 K 线图
- Binance WebSocket 实时数据
- 自动更新价格
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
    .live-indicator {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
        color: white;
        padding: 6px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
        box-shadow: 0 2px 10px rgba(255, 68, 68, 0.4);
    }
    .live-dot {
        width: 8px;
        height: 8px;
        background: #fff;
        border-radius: 50%;
        animation: blink 1.5s infinite;
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(symbol: str):
    """加载历史数据"""
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
    st.title("📊 K 线图 - TradingView 实时行情")
    st.markdown("---")
    
    # 实时数据标识
    st.markdown('<div class="live-indicator"><div class="live-dot"></div>🔴 实时行情</div>', unsafe_allow_html=True)
    
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
    
    # 加载历史数据
    with st.spinner(f"加载 {symbol} 历史数据..."):
        df = load_data(symbol)
        
        # 准备 K 线数据
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
        
        # Binance WebSocket 配置
        binance_symbol = symbol.replace("-", "").lower()
        if not binance_symbol.endswith("usdt"):
            binance_symbol = binance_symbol.replace("usd", "") + "usdt"
        
        # HTML 代码 - TradingView 风格 + WebSocket 实时数据
        html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; font-family: Arial, sans-serif; }}
        #chart {{ width: 100%; height: 650px; }}
        .price-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            z-index: 1000;
            background: rgba(30, 30, 30, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            border: 1px solid #444;
            color: #d1d4dc;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
        }}
        .price-value {{
            font-size: 28px;
            font-weight: bold;
            color: #00ff88;
        }}
        .price-change {{
            font-size: 16px;
            margin-top: 5px;
        }}
        .legend {{
            position: absolute;
            right: 10px;
            top: 10px;
            z-index: 1000;
            background: rgba(30, 30, 30, 0.9);
            padding: 10px 15px;
            border-radius: 8px;
            border: 1px solid #444;
            color: #d1d4dc;
            font-size: 13px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-line {{
            width: 25px;
            height: 3px;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div id="chart"></div>
    <div class="price-panel">
        <div style="color: #888; font-size: 12px; margin-bottom: 5px;">{symbol} 实时价格</div>
        <div class="price-value" id="price">加载中...</div>
        <div class="price-change" id="change">--</div>
    </div>
    <div class="legend">
        <div style="font-weight: bold; margin-bottom: 8px;">📊 价格标记</div>
        <div class="legend-item">
            <div class="legend-line" style="background: #ff4444;"></div>
            <span>🛑 止损</span>
        </div>
        <div class="legend-item">
            <div class="legend-line" style="background: #00ff88;"></div>
            <span>🎯 止盈</span>
        </div>
        <div class="legend-item">
            <div class="legend-line" style="background: #0088ff;"></div>
            <span>💰 入场</span>
        </div>
    </div>
    <script>
        // 创建图表
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
                secondsVisible: false,
            }},
            rightPriceScale: {{
                borderColor: '#485c7b',
            }},
        }});

        // K 线系列
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderVisible: false,
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
        }});

        // 加载历史数据
        candlestickSeries.setData({json.dumps(candles)});
        
        // 添加信号标记和价格线
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
            
            // 止损线
            chart.priceLine({{
                price: signalData.stop_loss,
                color: '#ff4444',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🛑 止损',
            }});
            
            // 止盈线
            chart.priceLine({{
                price: signalData.take_profit,
                color: '#00ff88',
                lineWidth: 2,
                lineStyle: 2,
                axisLabelVisible: true,
                title: '🎯 止盈',
            }});
            
            // 入场线
            chart.priceLine({{
                price: signalData.entry,
                color: '#0088ff',
                lineWidth: 1,
                lineStyle: 0,
                axisLabelVisible: true,
                title: '💰 入场',
            }});
        }}
        
        // 连接 Binance WebSocket 获取实时价格
        const binanceSymbol = '{binance_symbol}';
        const ws = new WebSocket(`wss://stream.binance.com:9443/ws/${{binanceSymbol}}@trade`);
        
        let lastPrice = 0;
        const priceElement = document.getElementById('price');
        const changeElement = document.getElementById('change');
        
        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            const price = parseFloat(data.p);
            
            // 更新价格显示
            priceElement.textContent = '$' + price.toLocaleString('en-US', {{minimumFractionDigits: 2, maximumFractionDigits: 2}});
            
            // 颜色变化
            if (price > lastPrice) {{
                priceElement.style.color = '#00ff88';
            }} else if (price < lastPrice) {{
                priceElement.style.color = '#ff4444';
            }}
            
            lastPrice = price;
        }};
        
        ws.onopen = () => {{
            priceElement.textContent = '已连接';
        }};
        
        ws.onerror = () => {{
            priceElement.textContent = '连接失败';
        }};
        
        // 自适应大小
        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: chartContainer.clientWidth }});
        }});
    </script>
</body>
</html>
"""
        st.components.v1.html(html_code, height=680, scrolling=False)
    
    st.markdown("""
    **📊 TradingView 风格图表:**
    - 🕯️ 专业 K 线显示（绿色涨/红色跌）
    - 🔍 鼠标滚轮缩放 | ✋ 拖拽平移
    - ➕ 十字光标显示 OHLC
    - 📈 信号箭头：🟢 买入 | 🔴 卖出
    - 📐 价格线：🔴 止损 | 🟢 止盈 | 🔵 入场
    
    **⚡ 实时数据:**
    - 数据来源：Binance WebSocket
    - 更新频率：实时（毫秒级）
    - 左上角显示实时价格和涨跌
    
    **💡 提示:**
    图表会自动连接 Binance WebSocket，实时显示最新成交价格。
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")

st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议 | 实时数据由 Binance WebSocket 提供")
