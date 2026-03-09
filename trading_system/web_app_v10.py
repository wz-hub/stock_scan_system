"""
交易策略信号系统 - Web 界面 v10
- TradingView 官方图表（完整功能）
- 实时数据 + 时间周期切换
- 完整划线工具 + 技术指标
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
        
        # 交易量信息
        volume_text = signal.get('volume_info', '')
        if volume_text:
            if '✅' in volume_text:
                st.success(f"📊 成交量：{volume_text}")
            elif '⚠️' in volume_text:
                st.warning(f"📊 成交量：{volume_text}")
            else:
                st.info(f"📊 成交量：{volume_text}")
        
        # AI 评分
        ai_score = signal.get('ai_score')
        ai_recommendation = signal.get('ai_recommendation')
        ai_reasons = signal.get('ai_reasons', [])
        
        if ai_score:
            score_color = "🟢" if ai_score >= 80 else "🟡" if ai_score >= 70 else "🔴"
            st.markdown(f"**🤖 AI 评分:** {score_color} **{ai_score}/100** - {ai_recommendation}")
            
            if ai_reasons:
                with st.expander("📋 AI 分析详情"):
                    for reason in ai_reasons:
                        st.write(f"- {reason}")
        elif signal.get('ai_error'):
            st.caption(f"⚠️ AI 分析不可用：{signal.get('ai_error')}")
        
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
    st.title("📊 K 线图 - TradingView 专业版")
    st.markdown("---")
    
    st.markdown('<span class="live-badge">🔴 实时行情</span>', unsafe_allow_html=True)
    
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
        
        st.info(f"📌 提示：在图表中手动绘制水平线标记止损止盈价位：止损 ${signal.get('stop_loss_price'):,.2f} | 止盈 ${signal.get('take_profit_price'):,.2f}")
    else:
        st.info("👈 请在信号中心选择一个信号查看")
    
    symbol = st.selectbox("交易标的", ["BTC-USD", "ETH-USD"], index=0)
    
    # 转换 TradingView 品种代码
    tv_symbol = {
        "BTC-USD": "COINBASE:BTCUSD",
        "ETH-USD": "COINBASE:ETHUSD",
        "BTC-USDT": "BINANCE:BTCUSDT",
        "ETH-USDT": "BINANCE:ETHUSDT"
    }.get(symbol, f"COINBASE:{symbol.replace('-', '')}")
    
    # TradingView Technical Analysis Widget
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
        "hide_side_toolbar": false,
        "save_image": true,
        "container_id": "tv_chart",
        "studies": [
            "Volume@tv-basicstudies"
        ],
        "show_popup_button": true,
        "popup_width": "1000",
        "popup_height": "650",
        "allow_symbol_change": true,
        "details": true,
        "hotlist": true,
        "calendar": true,
        "news": [
            "headlines"
        ],
        "drawings_access": true,
        "disabled_features": [
        ],
        "enabled_features": [
            "study_templates",
            "charts_widget",
            "show_interval_dialog_on_key_press"
        ],
        "overrides": {{
            "mainSeriesProperties.candleStyle.upColor": "#00ff88",
            "mainSeriesProperties.candleStyle.downColor": "#ff4444",
            "mainSeriesProperties.candleStyle.borderUpColor": "#00ff88",
            "mainSeriesProperties.candleStyle.borderDownColor": "#ff4444",
            "mainSeriesProperties.candleStyle.wickUpColor": "#00ff88",
            "mainSeriesProperties.candleStyle.wickDownColor": "#ff4444"
        }}
    }});
    </script>
</body>
</html>
"""
    
    st.components.v1.html(tv_widget_html, height=730, scrolling=False)
    
    st.markdown("""
    **📊 TradingView 专业功能:**
    
    **⏱️ 时间周期切换:**
    - 点击顶部工具栏的时间周期按钮
    - 支持：1 分钟/5 分钟/15 分钟/30 分钟/1 小时/2 小时/4 小时/1 天/1 周/1 月
    - 或自定义时间周期
    
    **✏️ 划线工具:**
    - 点击顶部工具栏的画笔图标
    - 趋势线、水平线、斜线、射线
    - 斐波那契回撤/扩展
    - 通道线、平行线
    - 图形：矩形、圆形、三角形
    - 标注：文字、箭头、图标
    
    **📈 技术指标:**
    - 点击 "fx" 按钮
    - 100+ 技术指标：MA/EMA/RSI/MACD/布林带/KDJ/ATR 等
    - 可叠加多个指标
    - 可自定义指标参数
    
    **🔍 图表操作:**
    - 鼠标滚轮：缩放
    - 拖拽：平移
    - 右键菜单：更多选项
    - 十字光标：显示 OHLC 数据
    
    **💾 保存功能:**
    - 图表自动保存到 TradingView 账户
    - 可导出图片
    - 可分享图表链接
    
    **📰 其他功能:**
    - 新闻：查看相关市场新闻
    - 自选：添加到自选列表
    - 详情：查看品种详细信息
    - 热力图：市场资金流向
    
    **🎯 止损止盈标记:**
    TradingView 官方图表不支持自动绘制价格线，建议：
    1. 使用水平线工具手动标记止损止盈价位
    2. 在图表上方已显示具体价格，可参考绘制
    """)

elif page == "📈 策略回测":
    st.title("📈 策略回测")
    st.info("回测功能开发中...")

elif page == "⚙️ 设置":
    st.title("⚙️ 系统设置")
    
    # AI 大模型配置
    st.subheader("🤖 AI 大模型配置")
    
    from ai_scorer import AIScorer
    scorer = AIScorer()
    
    with st.form("ai_config_form"):
        ai_enabled = st.checkbox("启用 AI 评分", value=scorer.enabled)
        ai_api_url = st.text_input(
            "API 地址",
            value=scorer.config.get('api_url', ''),
            help="如：https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        )
        ai_api_key = st.text_input(
            "API Key",
            value=scorer.config.get('api_key', ''),
            type="password",
            help="你的大模型 API 密钥"
        )
        ai_model = st.selectbox(
            "模型",
            ["qwen3.5-plus", "qwen3.5-turbo", "qwen-plus", "qwen-turbo", "deepseek-chat", "gpt-3.5-turbo"],
            index=0 if scorer.config.get('model', '') == 'qwen3.5-plus' else 1
        )
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
            
            # 测试连接
            if ai_enabled and ai_api_key:
                st.info("🔍 测试连接中...")
                test_result = scorer.test_connection()
                if 'error' in test_result:
                    st.error(f"❌ 连接失败：{test_result['error']}")
                else:
                    st.success(f"✅ 连接成功！测试评分：{test_result.get('score', 'N/A')}")
    
    # 当前配置状态
    st.markdown("---")
    st.markdown("**当前配置状态:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("AI 状态", "✅ 已启用" if scorer.enabled else "❌ 未启用")
    with col2:
        st.metric("模型", scorer.model)
    with col3:
        st.metric("API", "已配置" if scorer.api_key else "未配置")
    
    # 飞书推送配置
    st.markdown("---")
    st.subheader("📡 飞书推送")
    st.write("✅ Webhook 已配置")
    st.code("https://open.feishu.cn/open-apis/bot/v2/hook/555c2a9b-538a-478e-8a4a-9eb3953fe54b")
    
    # 定时任务状态
    st.markdown("---")
    st.subheader("⏰ 定时任务")
    st.info("""
    **扫描频率:**
    - 周中（周一至周五）：每小时 1 次
    - 周末（周六至周日）：每 4 小时 1 次
    
    **查看定时任务:** `crontab -l`
    
    **查看扫描日志:** `tail -f /tmp/signals_scan.log`
    """)

st.markdown("---")
st.caption("📌 提示：信号仅供参考，不构成投资建议 | 图表由 TradingView 提供")
