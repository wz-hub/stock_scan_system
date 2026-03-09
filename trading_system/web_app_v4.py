"""
交易策略信号系统 - Web 界面 v4
修复：点击信号显示 K 线 + 卡片式完整信息展示
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
    .signal-card {
        background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
        border-radius: 12px;
        padding: 25px;
        margin: 15px 0;
        border: 2px solid #333;
        transition: all 0.3s ease;
    }
    .signal-card.buy {
        border-color: #00ff88;
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.15);
    }
    .signal-card.sell {
        border-color: #ff4444;
        box-shadow: 0 4px 15px rgba(255, 68, 68, 0.15);
    }
    .signal-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 15px;
        border-bottom: 1px solid #333;
    }
    .signal-title {
        font-size: 1.3em;
        font-weight: bold;
        margin: 0;
    }
    .signal-badge {
        padding: 5px 15px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .badge-high { background: #ff4444; color: white; }
    .badge-medium { background: #ffaa00; color: black; }
    .badge-low { background: #888; color: white; }
    .signal-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }
    .signal-info {
        background: rgba(255,255,255,0.05);
        padding: 12px;
        border-radius: 8px;
    }
    .signal-info-label {
        color: #888;
        font-size: 0.85em;
        margin-bottom: 5px;
    }
    .signal-info-value {
        font-size: 1.1em;
        font-weight: bold;
        color: #fff;
    }
    .risk-box {
        background: rgba(255,255,255,0.03);
        border: 1px solid #444;
        border-radius: 8px;
        padding: 15px;
        margin-top: 15px;
    }
    .risk-title {
        color: #888;
        font-size: 0.9em;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .view-chart-btn {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
        color: #000;
        border: none;
        border-radius: 8px;
        padding: 12px 30px;
        font-weight: bold;
        font-size: 1em;
        cursor: pointer;
        transition: all 0.3s;
    }
    .view-chart-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 20px rgba(0, 255, 136, 0.4);
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


def create_tradingview_chart(symbol: str, df: pd.DataFrame, selected_signal=None):
    """创建 TradingView 图表"""
    
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
    
    if selected_signal:
        signal_date = selected_signal.get('timestamp', '')[:10]
        signal_price = selected_signal.get('current_price', 0)
        stop_loss = selected_signal.get('stop_loss_price', 0)
        take_profit = selected_signal.get('take_profit_price', 0)
        action = selected_signal.get('action', 'BUY')
        
        # 找到最接近的 K 线
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
                
                # 生成价格线 JS 代码
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
    html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; font-family: Arial, sans-serif; }}
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

        candlestickSeries.setData({json.dumps(candle_data)});
        
        {f"candlestickSeries.setMarkers({json.dumps(markers)});" if markers else ""}
        
        const chart_api = chart;
        {price_lines_js}

        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: chartContainer.clientWidth }});
        }});
    </script>
</body>
</html>
"""
    
    return html_code


def render_signal_card(signal, index):
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
    pnl_pct = signal.get('price_change_24h', 0)
    
    card_type = "buy" if action == "BUY" else "sell"
    badge_class = "badge-high" if priority == "HIGH" else "badge-medium" if priority == "MEDIUM" else "badge-low"
    action_emoji = "🟢" if action == "BUY" else "🔴"
    
    html = f"""
    <div class="signal-card {card_type}">
        <div class="signal-header">
            <div>
                <div class="signal-title">
                    {action_emoji} 【{strategy}】{symbol}
                </div>
                <div style="color: #888; margin-top: 5px; font-size: 0.9em;">
                    📅 {timestamp}
                </div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <span class="signal-badge {badge_class}">{priority}</span>
                <span style="font-size: 2em; font-weight: bold; color: {'#00ff88' if action == 'BUY' else '#ff4444'};">
                    {action}
                </span>
            </div>
        </div>
        
        <div class="signal-grid">
            <div class="signal-info">
                <div class="signal-info-label">💰 当前价格</div>
                <div class="signal-info-value">${price:,.2f}</div>
            </div>
            <div class="signal-info">
                <div class="signal-info-label">📊 方向</div>
                <div class="signal-info-value">{direction}</div>
            </div>
            <div class="signal-info">
                <div class="signal-info-label">📈 置信度</div>
                <div class="signal-info-value" style="color: {'#00ff88' if confidence >= 70 else '#ffaa00' if confidence >= 50 else '#ff4444'};">
                    {confidence:.0f}%
                </div>
            </div>
            <div class="signal-info">
                <div class="signal-info-label">📉 24h 涨跌</div>
                <div class="signal-info-value" style="color: {'#00ff88' if pnl_pct >= 0 else '#ff4444'};">
                    {pnl_pct:+.2f}%
                </div>
            </div>
        </div>
        
        <div class="signal-info" style="margin-bottom: 15px;">
            <div class="signal-info-label">💡 信号理由</div>
            <div class="signal-info-value" style="font-size: 1em; font-weight: normal;">
                {reason}
            </div>
        </div>
        
        <div class="risk-box">
            <div class="risk-title">📐 风险管理</div>
            <div class="signal-grid" style="margin: 0; gap: 10px;">
                <div class="signal-info">
                    <div class="signal-info-label">🛑 止损价格</div>
                    <div class="signal-info-value" style="color: #ff4444;">${stop_loss:,.2f}</div>
                </div>
                <div class="signal-info">
                    <div class="signal-info-label">🎯 止盈价格</div>
                    <div class="signal-info-value" style="color: #00ff88;">${take_profit:,.2f}</div>
                </div>
                <div class="signal-info">
                    <div class="signal-info-label">📊 盈亏比</div>
                    <div class="signal-info-value">{rr}:1</div>
                </div>
            </div>
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
    
    # 查看 K 线按钮
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            f"📊 查看 {symbol} K 线图（显示止损止盈）",
            key=f"view_chart_{signal.get('signal_id')}_{index}",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.selected_signal = signal
            st.session_state.current_symbol = symbol
            st.session_state.page = "📊 K 线图"
            st.rerun()
    
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

# 导航
page = st.sidebar.radio(
    "导航",
    ["📡 信号中心", "📊 K 线图", "📈 策略回测", "⚙️ 设置"],
    index=0,
    key="nav_radio"
)

# 同步 session state
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
                
                # 保存到文件
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
    
    # 显示选中的信号信息
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
        
        st.markdown("🔴 红色虚线 = 止损 | 🟢 绿色虚线 = 止盈 | 🔵 蓝色实线 = 入场")
    
    # 选择标的
    symbol = st.selectbox(
        "选择标的",
        ["BTC-USD", "ETH-USD"],
        index=0 if st.session_state.current_symbol == 'BTC-USD' else 1
    )
    
    with st.spinner(f"加载 {symbol} 数据..."):
        df = load_data(symbol)
        
        # 显示图表
        html_chart = create_tradingview_chart(symbol, df, st.session_state.selected_signal)
        st.components.v1.html(html_chart, height=680, scrolling=False)
    
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
