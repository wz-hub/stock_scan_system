"""
交易策略信号系统 - Web 界面 v5
使用 Streamlit 原生组件渲染信号卡片
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader
from signal_generator import SignalGenerator

# 页面配置
st.set_page_config(
    page_title="📡 交易信号系统",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    div[data-testid="stMetricValue"] {
        font-size: 1.5em;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(symbol: str):
    """加载数据"""
    loader = DataLoader()
    data_file = Path('data') / f"{symbol.replace('/', '_')}.csv"
    
    if data_file.exists():
        return loader.load_csv(str(data_file))
    else:
        return loader.download_yahoo(symbol, '2022-01-01', '2024-12-31')


def get_all_signals():
    """获取所有信号"""
    try:
        signal_files = sorted(Path('signals').glob('signal_*.json'), reverse=True)
        signals = []
        
        for file in signal_files:
            try:
                with open(file) as f:
                    signal = json.load(f)
                    signals.append(signal)
            except:
                continue
        
        return signals
    except:
        return []


def render_signal_card(signal, index):
    """渲染信号卡片 - 使用 Streamlit 原生组件"""
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
    pnl_pct = signal.get('price_change_24h', 0)
    
    action_emoji = "🟢" if action == "BUY" else "🔴"
    priority_icon = "🔴" if priority == "HIGH" else "🟡" if priority == "MEDIUM" else "⚪"
    
    # 卡片容器
    card_container = st.container()
    
    with card_container:
        # 标题栏
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"### {action_emoji}【{strategy}】{symbol}")
            st.caption(f"📅 {timestamp}")
        
        with col2:
            st.metric("优先级", priority)
        
        with col3:
            st.metric("操作", action, delta=None)
        
        # 分隔线
        st.divider()
        
        # 主要信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💰 价格", f"${price:,.2f}")
        
        with col2:
            st.metric("📊 方向", direction)
        
        with col3:
            conf_color = "🟢" if confidence >= 70 else "🟡" if confidence >= 50 else "🔴"
            st.metric("📈 置信度", f"{conf_color} {confidence:.0f}%")
        
        with col4:
            pnl_color = "🟢" if pnl_pct >= 0 else "🔴"
            st.metric("📉 24h", f"{pnl_color} {pnl_pct:+.2f}%")
        
        # 信号理由
        st.markdown("**💡 信号理由**")
        st.info(reason)
        
        # 风险管理
        st.markdown("**📐 风险管理**")
        
        risk_col1, risk_col2, risk_col3 = st.columns(3)
        
        with risk_col1:
            st.error(f"🛑 止损：${stop_loss:,.2f}")
        
        with risk_col2:
            st.success(f"🎯 止盈：${take_profit:,.2f}")
        
        with risk_col3:
            st.metric("📊 盈亏比", f"{rr}:1")
        
        # 查看 K 线按钮
        st.markdown("")  # 间距
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            view_chart_key = f"view_chart_{signal.get('signal_id')}_{index}"
            if st.button(
                f"📊 查看 {symbol} K 线图（显示止损止盈）",
                key=view_chart_key,
                use_container_width=True,
                type="primary"
            ):
                st.session_state.selected_signal = signal
                st.session_state.current_symbol = symbol
                # 使用 URL 参数触发页面切换
                st.query_params["page"] = "kline"
                st.rerun()
        
        # 大分隔线
        st.markdown("---")


# 初始化 session state
if 'selected_signal' not in st.session_state:
    st.session_state.selected_signal = None
if 'current_symbol' not in st.session_state:
    st.session_state.current_symbol = 'BTC-USD'
if 'page' not in st.session_state:
    st.session_state.page = "📡 信号中心"


# 侧边栏
st.sidebar.title("🎛️ 控制中心")

# 检查 URL 参数
query_params = st.query_params
if query_params.get("page") == "kline":
    st.session_state.page = "📊 K 线图"
    # 清除参数
    st.query_params["page"] = ""
elif 'page' not in st.session_state:
    st.session_state.page = "📡 信号中心"

# 导航
page_options = ["📡 信号中心", "📊 K 线图", "📈 策略回测", "⚙️ 设置"]

# 同步当前页面
current_page_idx = page_options.index(st.session_state.page) if st.session_state.page in page_options else 0

page = st.sidebar.radio(
    "导航",
    page_options,
    index=current_page_idx,
    key="nav_radio"
)

# 更新 session state
st.session_state.page = page

# 信号筛选
st.sidebar.subheader("🔍 筛选")
selected_symbol = st.sidebar.selectbox(
    "标的",
    ["BTC-USD", "ETH-USD"],
    index=0
)

priority_filter = st.sidebar.multiselect(
    "优先级",
    ["HIGH", "MEDIUM", "LOW"],
    default=["HIGH", "MEDIUM", "LOW"]
)

strategy_filter = st.sidebar.multiselect(
    "策略",
    ["均线交叉", "RSI", "形态交易", "趋势跟踪", "123/2B 反转", "布林带", "波动率突破", "突破策略", "支撑阻力"],
    default=["均线交叉", "RSI", "形态交易", "趋势跟踪", "123/2B 反转", "布林带", "波动率突破", "突破策略", "支撑阻力"]
)

# 主界面
if page == "📡 信号中心":
    st.title("📡 交易信号中心")
    st.markdown("### 点击「查看 K 线图」按钮显示止损止盈标记")
    st.markdown("---")
    
    # 获取所有信号
    all_signals = get_all_signals()
    
    # 筛选
    filtered_signals = []
    for signal in all_signals:
        if signal.get('symbol') != selected_symbol:
            continue
        if signal.get('priority') not in priority_filter:
            continue
        if signal.get('strategy_name') not in strategy_filter:
            continue
        filtered_signals.append(signal)
    
    if filtered_signals:
        # 统计
        col1, col2, col3, col4, col5 = st.columns(5)
        
        buy_count = len([s for s in filtered_signals if s.get('action') == 'BUY'])
        sell_count = len([s for s in filtered_signals if s.get('action') == 'SELL'])
        high_priority = len([s for s in filtered_signals if s.get('priority') == 'HIGH'])
        avg_confidence = sum([s.get('confidence', 0) for s in filtered_signals]) / len(filtered_signals)
        
        with col1:
            st.metric("📊 总信号", len(filtered_signals))
        with col2:
            st.metric("🟢 买入", buy_count)
        with col3:
            st.metric("🔴 卖出", sell_count)
        with col4:
            st.metric("🔴 高优先级", high_priority)
        with col5:
            st.metric("📈 平均置信度", f"{avg_confidence:.1f}%")
        
        st.markdown("---")
        
        # 渲染信号卡片
        for idx, signal in enumerate(filtered_signals):
            render_signal_card(signal, idx)
    
    else:
        st.warning("暂无符合条件的信号")
        
        if st.button("🔄 生成新信号", type="primary"):
            with st.spinner("正在扫描市场..."):
                df = load_data(selected_symbol)
                generator = SignalGenerator(capital=100000, enable_notification=True)
                signals = generator.scan_all_strategies(df, selected_symbol, scan_last_days=30)
                
                signals_dir = Path('signals')
                signals_dir.mkdir(exist_ok=True)
                
                for signal in signals:
                    signal_file = signals_dir / f"signal_{signal.signal_id}.json"
                    with open(signal_file, 'w') as f:
                        json.dump(signal.to_dict(), f, indent=2, ensure_ascii=False)
                
                st.success(f"生成 {len(signals)} 个信号！")
                st.rerun()

elif page == "📊 K 线图":
    st.title("📊 K 线图 - TradingView")
    st.markdown("---")
    
    if st.session_state.selected_signal:
        signal = st.session_state.selected_signal
        st.success(f"✅ 显示信号：**{signal.get('signal_id')}** | {signal.get('strategy_name')} | {signal.get('action')} @ ${signal.get('current_price'):,.2f}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 入场价", f"${signal.get('current_price'):,.2f}")
        with col2:
            st.metric("🛑 止损", f"${signal.get('stop_loss_price'):,.2f}")
        with col3:
            st.metric("🎯 止盈", f"${signal.get('take_profit_price'):,.2f}")
        with col4:
            st.metric("📊 盈亏比", f"{signal.get('risk_reward_ratio', 0)}:1")
        
        st.info("🔴 红色虚线 = 止损 | 🟢 绿色虚线 = 止盈 | 🔵 蓝色实线 = 入场")
    
    symbol = st.selectbox(
        "选择标的",
        ["BTC-USD", "ETH-USD"],
        index=0 if st.session_state.current_symbol == 'BTC-USD' else 1
    )
    
    with st.spinner(f"加载 {symbol} 数据..."):
        df = load_data(symbol)
        
        # 准备 K 线数据
        candle_data = []
        for idx, row in df.iterrows():
            timestamp = int(idx.timestamp() * 1000)
            candle_data.append({
                "time": timestamp,
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close'])
            })
        
        # 准备信号标记
        markers = []
        price_lines_js = ""
        
        if st.session_state.selected_signal:
            sel_signal = st.session_state.selected_signal
            signal_date = sel_signal.get('timestamp', '')[:10]
            signal_price = sel_signal.get('current_price', 0)
            stop_loss = sel_signal.get('stop_loss_price', 0)
            take_profit = sel_signal.get('take_profit_price', 0)
            action = sel_signal.get('action', 'BUY')
            
            for idx, row in df.iterrows():
                if idx.strftime('%Y-%m-%d') == signal_date:
                    timestamp = int(idx.timestamp() * 1000)
                    
                    if action == 'BUY':
                        markers.append({
                            "time": timestamp,
                            "position": "belowBar",
                            "color": "#00ff88",
                            "shape": "arrowUp",
                            "text": f"BUY\n@{signal_price:.0f}",
                            "size": 2
                        })
                    else:
                        markers.append({
                            "time": timestamp,
                            "position": "aboveBar",
                            "color": "#ff4444",
                            "shape": "arrowDown",
                            "text": f"SELL\n@{signal_price:.0f}",
                            "size": 2
                        })
                    
                    price_lines_js = f"""
                    chart.priceLine({{
                        price: {stop_loss},
                        color: '#ff4444',
                        lineWidth: 2,
                        lineStyle: 2,
                        axisLabelVisible: true,
                        title: '止损',
                    }});
                    chart.priceLine({{
                        price: {take_profit},
                        color: '#00ff88',
                        lineWidth: 2,
                        lineStyle: 2,
                        axisLabelVisible: true,
                        title: '止盈',
                    }});
                    chart.priceLine({{
                        price: {signal_price},
                        color: '#0088ff',
                        lineWidth: 1,
                        lineStyle: 0,
                        axisLabelVisible: true,
                        title: '入场',
                    }});
                    """
                    break
        
        # HTML 代码
        import json as json_lib
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

        candlestickSeries.setData({json_lib.dumps(candle_data)});
        
        {f"candlestickSeries.setMarkers({json_lib.dumps(markers)});" if markers else ""}
        
        {price_lines_js}

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
    - 📈 价格线：止损/止盈/入场自动标记
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")

# 底部
st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议")
