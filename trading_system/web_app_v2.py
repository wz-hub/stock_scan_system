"""
交易策略信号系统 - Web 界面 v2
使用 TradingView Lightweight Charts
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
    page_title="📡 交易信号中心",
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
        border: 1px solid #333;
        transition: all 0.3s;
    }
    .signal-card:hover {
        border-color: #00ff88;
        transform: translateY(-2px);
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #00ff88;
    }
    .buy-signal {
        border-left: 4px solid #00ff88;
    }
    .sell-signal {
        border-left: 4px solid #ff4444;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2em;
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


def get_latest_signals():
    """获取最新信号"""
    try:
        signal_files = sorted(Path('signals').glob('signal_*.json'), reverse=True)
        signals = []
        
        for file in signal_files[:20]:  # 最近 20 个
            with open(file) as f:
                signal = json.load(f)
                signals.append(signal)
        
        return signals
    except:
        return []


def create_tradingview_chart(symbol: str, df: pd.DataFrame, signals_df=None):
    """创建 TradingView 风格图表"""
    # 准备 K 线数据
    candle_data = []
    for idx, row in df.iterrows():
        candle_data.append({
            "time": idx.strftime('%Y-%m-%d'),
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        })
    
    # 准备信号标记
    markers = []
    if signals_df is not None and 'signal' in signals_df.columns:
        buy_signals = signals_df[signals_df['signal'] == 1]
        sell_signals = signals_df[signals_df['signal'] == -1]
        
        for idx, row in buy_signals.iterrows():
            markers.append({
                "time": idx.strftime('%Y-%m-%d'),
                "position": "belowBar",
                "color": "#00ff88",
                "shape": "arrowUp",
                "text": f"BUY @ {row['close']:.0f}"
            })
        
        for idx, row in sell_signals.iterrows():
            markers.append({
                "time": idx.strftime('%Y-%m-%d'),
                "position": "aboveBar",
                "color": "#ff4444",
                "shape": "arrowDown",
                "text": f"SELL @ {row['close']:.0f}"
            })
    
    # HTML 代码
    html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; }}
        #chart {{ width: 100%; height: 600px; }}
        .chart-container {{ position: relative; }}
    </style>
</head>
<body>
    <div class="chart-container">
        <div id="chart"></div>
    </div>
    <script>
        const chartContainer = document.getElementById('chart');
        const chart = LightweightCharts.createChart(chartContainer, {{
            width: chartContainer.clientWidth,
            height: 600,
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
        }});

        // K 线系列
        const candlestickSeries = chart.addCandlestickSeries({{
            upColor: '#00ff88',
            downColor: '#ff4444',
            borderVisible: false,
            wickUpColor: '#00ff88',
            wickDownColor: '#ff4444',
        }});

        candlestickSeries.setData({candle_data});
        
        // 添加信号标记
        candlestickSeries.setMarkers({markers});

        // 自适应大小
        window.addEventListener('resize', () => {{
            chart.applyOptions({{ width: chartContainer.clientWidth }});
        }});
    </script>
</body>
</html>
"""
    
    return html_code


# 侧边栏
st.sidebar.title("🎛️ 控制中心")

# 导航
page = st.sidebar.radio(
    "导航",
    ["📡 信号中心", "📊 K 线图", "📈 策略回测", "⚙️ 设置"],
    index=0
)

# 信号筛选
st.sidebar.subheader("🔍 筛选")
symbols = st.sidebar.multiselect(
    "标的",
    ["BTC-USD", "ETH-USD", "AAPL", "TSLA"],
    default=["BTC-USD"]
)

priority_filter = st.sidebar.multiselect(
    "优先级",
    ["HIGH", "MEDIUM", "LOW"],
    default=["HIGH", "MEDIUM"]
)

# 主界面
if page == "📡 信号中心":
    st.title("📡 交易信号中心")
    st.markdown("---")
    
    # 获取最新信号
    signals = get_latest_signals()
    
    if signals:
        # 统计
        col1, col2, col3, col4 = st.columns(4)
        
        buy_count = len([s for s in signals if s.get('action') == 'BUY'])
        sell_count = len([s for s in signals if s.get('action') == 'SELL'])
        high_priority = len([s for s in signals if s.get('priority') == 'HIGH'])
        avg_confidence = sum([s.get('confidence', 0) for s in signals]) / len(signals) if signals else 0
        
        with col1:
            st.metric("🟢 买入信号", buy_count)
        with col2:
            st.metric("🔴 卖出信号", sell_count)
        with col3:
            st.metric("🔴 高优先级", high_priority)
        with col4:
            st.metric("📊 平均置信度", f"{avg_confidence:.1f}%")
        
        st.markdown("---")
        
        # 信号列表
        st.subheader("最新信号")
        
        for signal in signals[:10]:
            action = signal.get('action', 'BUY')
            priority = signal.get('priority', 'MEDIUM')
            
            card_class = "buy-signal" if action == "BUY" else "sell-signal"
            
            st.markdown(f"""
            <div class="signal-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h3 style="margin: 0 0 10px 0;">
                            {'🟢' if action == 'BUY' else '🔴'} 
                            【{signal.get('strategy_name', 'Unknown')}】 
                            {signal.get('symbol', 'N/A')} 
                            {action}
                        </h3>
                        <p style="margin: 5px 0; color: #888;">
                            📅 {signal.get('timestamp', '')[:16].replace('T', ' ')} |
                            💰 ${signal.get('current_price', 0):,.2f} |
                            📊 {signal.get('direction', 'LONG')}
                        </p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.5em; color: {'#00ff88' if priority == 'HIGH' else '#ffaa00' if priority == 'MEDIUM' else '#888'};">
                            {priority}
                        </div>
                        <div style="color: #888;">置信度 {signal.get('confidence', 0):.0f}%</div>
                    </div>
                </div>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #333;">
                    <p style="margin: 5px 0;"><strong>💡 理由:</strong> {signal.get('reason', 'N/A')}</p>
                    <p style="margin: 5px 0;">
                        <strong>📐 风险:</strong> 
                        止损 ${signal.get('stop_loss_price', 0):,.2f} | 
                        止盈 ${signal.get('take_profit_price', 0):,.2f} | 
                        盈亏比 {signal.get('risk_reward_ratio', 0)}:1
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.info("暂无信号，运行信号生成器生成新信号")
        
        if st.button("🔄 生成新信号"):
            with st.spinner("正在扫描市场..."):
                df = load_data('BTC-USD')
                generator = SignalGenerator(capital=100000, enable_notification=True)
                signals = generator.scan_all_strategies(df, 'BTC-USD', scan_last_days=7)
                st.success(f"生成 {len(signals)} 个信号！")
                st.rerun()

elif page == "📊 K 线图":
    st.title("📊 K 线图 - TradingView 风格")
    st.markdown("---")
    
    # 选择标的
    symbol = st.selectbox("选择标的", ["BTC-USD", "ETH-USD"], index=0)
    
    with st.spinner(f"加载 {symbol} 数据..."):
        df = load_data(symbol)
        
        # 显示图表
        html_chart = create_tradingview_chart(symbol, df)
        st.components.v1.html(html_chart, height=620, scrolling=False)
    
    st.markdown("""
    **使用说明:**
    - 🔍 鼠标滚轮缩放
    - ✋ 拖拽平移
    - ➕ 右上角工具栏可添加指标、画线
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    
    st.subheader("📡 飞书推送")
    st.write("Webhook URL 已配置")
    
    st.subheader("📊 显示设置")
    theme = st.selectbox("主题", ["暗色", "亮色"], index=0)

# 底部
st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议 | 数据实时更新")
