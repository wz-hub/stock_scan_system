"""
交易策略信号系统 - Web 界面 v6
- 修复页面跳转
- 卡片式布局（一行两列）
- 区分历史信号和有效信号
- 全中文显示
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
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
    .signal-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 10px 0;
        border: 2px solid #333;
        transition: all 0.3s;
    }
    .signal-card.buy {
        border-color: #00ff88;
    }
    .signal-card.sell {
        border-color: #ff4444;
    }
    .signal-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(0, 255, 136, 0.15);
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.3em;
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


def is_signal_valid(signal):
    """判断信号是否有效（7 天内）"""
    try:
        signal_time = datetime.fromisoformat(signal.get('timestamp', ''))
        return (datetime.now() - signal_time).days <= 7
    except:
        return False


def render_signal_card(signal, col):
    """渲染信号卡片"""
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
        # 卡片容器
        card_class = "buy" if action == "BUY" else "sell"
        
        # 标题
        st.markdown(f"### {action_emoji}【{strategy}】{symbol}")
        
        # 优先级标签
        if priority == "HIGH":
            st.error(f"**优先级：{priority_text}** | **操作：{action_text}**")
        elif priority == "MEDIUM":
            st.warning(f"**优先级：{priority_text}** | **操作：{action_text}**")
        else:
            st.info(f"**优先级：{priority_text}** | **操作：{action_text}**")
        
        # 基本信息
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
        
        # 信号理由
        st.markdown("**💡 信号理由**")
        st.info(reason)
        
        # 风险管理
        st.markdown("**📐 风险管理**")
        
        risk_col1, risk_col2, risk_col3 = st.columns(3)
        with risk_col1:
            st.error(f"🛑 止损\n${stop_loss:,.2f}")
        with risk_col2:
            st.success(f"🎯 止盈\n${take_profit:,.2f}")
        with risk_col3:
            st.metric("📊 盈亏比", f"{rr}:1")
        
        # 查看 K 线按钮
        st.markdown("")
        if st.button(
            "📊 查看 K 线图",
            key=f"view_{signal.get('signal_id')}",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.selected_signal = signal
            st.session_state.current_symbol = symbol
            st.session_state.should_show_kline = True
            st.rerun()
        
        st.divider()


# 初始化 session state
if 'selected_signal' not in st.session_state:
    st.session_state.selected_signal = None
if 'current_symbol' not in st.session_state:
    st.session_state.current_symbol = 'BTC-USD'
if 'should_show_kline' not in st.session_state:
    st.session_state.should_show_kline = False


# 侧边栏
st.sidebar.title("🎛️ 控制中心")

# 导航
page = st.sidebar.radio(
    "导航",
    ["📡 信号中心", "📊 K 线图", "📈 策略回测", "⚙️ 设置"],
    index=0,
    key="nav_radio"
)

# 如果有信号被选中，自动切换到 K 线图
if st.session_state.should_show_kline:
    page = "📊 K 线图"
    st.session_state.should_show_kline = False

# 信号筛选
st.sidebar.subheader("🔍 筛选")
selected_symbol = st.sidebar.selectbox(
    "交易标的",
    ["BTC-USD", "ETH-USD"],
    index=0
)

priority_filter = st.sidebar.multiselect(
    "优先级",
    ["高", "中", "低"],
    default=["高", "中", "低"]
)

# 信号类型筛选
signal_type_filter = st.sidebar.radio(
    "信号类型",
    ["全部", "有效信号 (7 天内)", "历史信号"],
    index=0
)

# 主界面
if page == "📡 信号中心":
    st.title("📡 交易信号中心")
    st.markdown("### 点击「查看 K 线图」按钮显示止损止盈标记")
    st.markdown("---")
    
    # 获取所有信号
    all_signals = get_all_signals()
    
    # 优先级映射
    priority_map = {"高": "HIGH", "中": "MEDIUM", "低": "LOW"}
    priority_filters = [priority_map[p] for p in priority_filter]
    
    # 筛选
    filtered_signals = []
    valid_signals = []
    history_signals = []
    
    for signal in all_signals:
        if signal.get('symbol') != selected_symbol:
            continue
        if signal.get('priority') not in priority_filters:
            continue
        
        if is_signal_valid(signal):
            valid_signals.append(signal)
        else:
            history_signals.append(signal)
    
    # 根据类型筛选
    if signal_type_filter == "有效信号 (7 天内)":
        filtered_signals = valid_signals
    elif signal_type_filter == "历史信号":
        filtered_signals = history_signals
    else:
        filtered_signals = valid_signals + history_signals
    
    if filtered_signals:
        # 统计
        col1, col2, col3, col4 = st.columns(4)
        
        buy_count = len([s for s in filtered_signals if s.get('action') == 'BUY'])
        sell_count = len([s for s in filtered_signals if s.get('action') == 'SELL'])
        valid_count = len(valid_signals)
        history_count = len(history_signals)
        
        with col1:
            st.metric("📊 总信号", len(filtered_signals))
        with col2:
            st.metric("🟢 买入", buy_count)
        with col3:
            st.metric("🔴 卖出", sell_count)
        with col4:
            st.metric("✅ 有效", f"{valid_count} | 历史 {history_count}")
        
        st.markdown("---")
        
        # 显示有效信号
        if valid_signals and signal_type_filter != "历史信号":
            st.subheader("✅ 有效信号（7 天内）")
            
            # 一行两列
            for i in range(0, len(valid_signals), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(valid_signals):
                        render_signal_card(valid_signals[i + j], col)
            
            st.markdown("---")
        
        # 显示历史信号
        if history_signals and signal_type_filter != "有效信号 (7 天内)":
            st.subheader("📜 历史信号")
            
            # 一行两列
            for i in range(0, len(history_signals), 2):
                cols = st.columns(2)
                for j, col in enumerate(cols):
                    if i + j < len(history_signals):
                        render_signal_card(history_signals[i + j], col)
    
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
        action_text = "买入" if signal.get('action') == 'BUY' else "卖出"
        direction_text = "做多" if signal.get('direction') == 'LONG' else "做空"
        
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
        
        st.info("🔴 红色虚线 = 止损 | 🟢 绿色虚线 = 止盈 | 🔵 蓝色实线 = 入场")
    else:
        st.info("👈 请在信号中心选择一个信号查看")
    
    symbol = st.selectbox(
        "交易标的",
        ["BTC-USD", "ETH-USD"],
        index=0
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
        
        if st.session_state.selected_signal and st.session_state.current_symbol == symbol:
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
                            "text": f"买入\n@{signal_price:.0f}",
                            "size": 2
                        })
                    else:
                        markers.append({
                            "time": timestamp,
                            "position": "aboveBar",
                            "color": "#ff4444",
                            "shape": "arrowDown",
                            "text": f"卖出\n@{signal_price:.0f}",
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
