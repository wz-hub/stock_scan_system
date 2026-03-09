"""
交易策略信号系统 - Web 界面 v3
完整 TradingView 图表 + 信号交互
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys
import hashlib

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
        border: 1px solid #333;
        cursor: pointer;
        transition: all 0.3s;
    }
    .signal-card:hover {
        border-color: #00ff88;
        transform: translateX(5px);
        box-shadow: 0 4px 15px rgba(0, 255, 136, 0.2);
    }
    .buy-signal {
        border-left: 4px solid #00ff88;
    }
    .sell-signal {
        border-left: 4px solid #ff4444;
    }
    .stButton>button {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
        color: #000;
        border: none;
        border-radius: 8px;
        padding: 10px 25px;
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


def create_tradingview_chart(symbol: str, df: pd.DataFrame, selected_signal=None):
    """创建完整 TradingView 图表"""
    
    # 准备 K 线数据
    candle_data = []
    volume_data = []
    
    for idx, row in df.iterrows():
        timestamp = int(idx.timestamp() * 1000)
        candle_data.append({
            "time": timestamp,
            "open": float(row['open']),
            "high": float(row['high']),
            "low": float(row['low']),
            "close": float(row['close'])
        })
        vol_color = '#00ff88' if float(row['close']) >= float(row['open']) else '#ff4444'
        volume_data.append({
            "time": timestamp,
            "value": float(row['volume']),
            "color": vol_color
        })
    
    # 准备信号标记
    markers = []
    price_lines = []
    
    if selected_signal:
        # 获取信号日期
        signal_date = selected_signal.get('timestamp', '')[:10]
        signal_price = selected_signal.get('current_price', 0)
        stop_loss = selected_signal.get('stop_loss_price', 0)
        take_profit = selected_signal.get('take_profit_price', 0)
        action = selected_signal.get('action', 'BUY')
        
        # 找到最接近的 K 线时间戳
        for idx, row in df.iterrows():
            if idx.strftime('%Y-%m-%d') == signal_date:
                timestamp = int(idx.timestamp() * 1000)
                
                # 添加信号标记
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
                
                # 添加价格线
                price_lines.append({
                    "price": stop_loss,
                    "color": "#ff4444",
                    "lineWidth": 2,
                    "lineStyle": 2,  # 虚线
                    "text": f"止损 ${stop_loss:.0f}"
                })
                
                price_lines.append({
                    "price": take_profit,
                    "color": "#00ff88",
                    "lineWidth": 2,
                    "lineStyle": 2,
                    "text": f"止盈 ${take_profit:.0f}"
                })
                
                price_lines.append({
                    "price": signal_price,
                    "color": "#0088ff",
                    "lineWidth": 1,
                    "lineStyle": 0,
                    "text": f"入场 ${signal_price:.0f}"
                })
                
                break
    
    # 生成唯一 ID
    chart_id = hashlib.md5(f"{symbol}_{datetime.now().timestamp()}".encode()).hexdigest()[:8]
    
    # HTML 代码 - 使用 TradingView Technical Analysis Charts
    html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://s3.tradingview.com/tv.js"></script>
    <style>
        body {{ margin: 0; padding: 0; background: #1e1e1e; }}
        #tv_chart {{ width: 100%; height: 650px; }}
    </style>
</head>
<body>
    <div id="tv_chart"></div>
    <script>
        const chart = new TradingView.widget({{
            "width": "100%",
            "height": 650,
            "symbol": "{symbol.replace('-', '')}",
            "interval": "D",
            "timezone": "Asia/Shanghai",
            "theme": "dark",
            "style": "1",
            "locale": "zh_CN",
            "toolbar_bg": "#1e1e1e",
            "enable_publishing": false,
            "hide_top_toolbar": false,
            "save_image": false,
            "container_id": "tv_chart",
            "overrides": {{
                "mainSeriesProperties.candleStyle.upColor": "#00ff88",
                "mainSeriesProperties.candleStyle.downColor": "#ff4444",
                "mainSeriesProperties.candleStyle.borderUpColor": "#00ff88",
                "mainSeriesProperties.candleStyle.borderDownColor": "#ff4444",
                "mainSeriesProperties.candleStyle.wickUpColor": "#00ff88",
                "mainSeriesProperties.candleStyle.wickDownColor": "#ff4444"
            }},
            "studies": [
                "Volume@tv-basicstudies",
                "MA@tv-basicstudies",
                "RSI@tv-basicstudies"
            ]
        }});
        
        // 添加价格线标记
        chart.onChartReady(function() {{
            {f'''
            chart.chart().createPositionLine({{
                "price": {stop_loss},
                "color": "#ff4444",
                "lineWidth": 2,
                "lineStyle": 2,
                "text": "止损 ${stop_loss:.0f}"
            }});
            chart.chart().createPositionLine({{
                "price": {take_profit},
                "color": "#00ff88",
                "lineWidth": 2,
                "lineStyle": 2,
                "text": "止盈 ${take_profit:.0f}"
            }});
            ''' if selected_signal else ''}
        }});
    </script>
</body>
</html>
"""
    
    return html_code


# 初始化 session state
if 'selected_signal' not in st.session_state:
    st.session_state.selected_signal = None
if 'current_symbol' not in st.session_state:
    st.session_state.current_symbol = 'BTC-USD'


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
    st.markdown("### 点击信号查看 K 线图与详细分析")
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
        
        # 信号列表
        for signal in filtered_signals:
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
            
            card_class = "buy-signal" if action == "BUY" else "sell-signal"
            priority_color = "#ff4444" if priority == "HIGH" else "#ffaa00" if priority == "MEDIUM" else "#888"
            
            # 创建可点击的卡片
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if st.button(
                    f"{'🟢' if action == 'BUY' else '🔴'} 【{strategy}】{symbol} {action} @ ${price:,.2f}",
                    key=f"signal_{signal.get('signal_id')}",
                    use_container_width=True
                ):
                    st.session_state.selected_signal = signal
                    st.session_state.current_symbol = symbol
                    st.rerun()
            
            with col2:
                st.markdown(f"""
                <div style="text-align: right; padding-top: 10px;">
                    <div style="color: {priority_color}; font-weight: bold;">{priority}</div>
                    <div style="color: #888; font-size: 0.9em;">{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 详细信息（展开）
            with st.expander(f"📋 详情 - {signal.get('signal_id')}"):
                st.write(f"**💡 信号理由:** {reason}")
                st.write(f"**📐 风险管理:**")
                st.write(f"- 止损：${stop_loss:,.2f}")
                st.write(f"- 止盈：${take_profit:,.2f}")
                st.write(f"- 盈亏比：{rr}:1")
                st.write(f"- 置信度：{confidence}%")
    
    else:
        st.warning("暂无符合条件的信号")
        
        if st.button("🔄 生成新信号"):
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
                
                st.success(f"生成 {len(signals)} 个信号！已保存到 signals/ 目录")
                st.rerun()

elif page == "📊 K 线图":
    st.title("📊 K 线图 - TradingView 完整版")
    st.markdown("---")
    
    # 显示选中的信号
    if st.session_state.selected_signal:
        signal = st.session_state.selected_signal
        st.info(f"📡 当前查看信号：**{signal.get('signal_id')}** | {signal.get('strategy_name')} | {signal.get('action')} @ ${signal.get('current_price'):,.2f}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 入场价", f"${signal.get('current_price'):,.2f}")
        with col2:
            st.metric("🛑 止损", f"${signal.get('stop_loss_price'):,.2f}")
        with col3:
            st.metric("🎯 止盈", f"${signal.get('take_profit_price'):,.2f}")
    
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
    **🎨 TradingView 功能:**
    - ✏️ **划线工具**: 点击顶部工具栏选择趋势线、水平线、斐波那契等
    - 📈 **技术指标**: 点击 "fx" 添加 MA/RSI/MACD 等
    - 🔍 **缩放平移**: 鼠标滚轮缩放，拖拽平移
    - 💾 **保存状态**: 图表自动保存
    - 📊 **信号标记**: 绿色箭头=买入，红色箭头=卖出，虚线=止损/止盈
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")
    st.code("https://open.feishu.cn/open-apis/bot/v2/hook/555c2a9b-538a-478e-8a4a-9eb3953fe54b")
    
    st.subheader("📊 显示设置")
    st.write("主题：暗色")

# 底部
st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议 | 数据实时更新")
