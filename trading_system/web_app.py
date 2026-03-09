"""
交易策略回测系统 - Web 界面
使用 Streamlit + Plotly 实现
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys
import json

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from backtest.data_loader import DataLoader
from backtest.engine import BacktestEngine
from strategies import (
    TrendFollowingStrategy,
    Reversal123Strategy,
    SupportResistanceStrategy,
    PatternTradingStrategy,
    MACrossStrategy,
    VolatilityBreakoutStrategy,
    BollingerBandsStrategy,
    RSIStrategy,
    BreakoutStrategy
)

# 页面配置
st.set_page_config(
    page_title="交易策略回测系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #333;
    }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #00ff88;
    }
    .metric-label {
        color: #888;
        font-size: 0.9em;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2em;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data(symbol: str, start_date: str, end_date: str):
    """加载数据（缓存）"""
    loader = DataLoader()
    data_file = Path('data') / f"{symbol.replace('/', '_')}.csv"
    
    if data_file.exists():
        df = loader.load_csv(str(data_file))
    else:
        df = loader.download_yahoo(symbol, start_date, end_date)
    
    return df


def run_strategy_backtest(strategy, df, initial_capital=100000):
    """运行策略回测"""
    engine = BacktestEngine(initial_capital=initial_capital)
    engine.reset()
    
    signals_df = strategy.generate_signals(df)
    
    current_position = 0
    
    for i in range(len(signals_df)):
        idx = signals_df.index[i]
        row = signals_df.iloc[i]
        
        if pd.isna(row.get('close', np.nan)):
            current_position = int(row.get('position', 0)) if not pd.isna(row.get('position', 0)) else 0
            engine.update_equity(row['close'] if not pd.isna(row.get('close', np.nan)) else df.iloc[i]['close'])
            continue
        
        target_position = int(row.get('position', 0)) if not pd.isna(row.get('position', 0)) else 0
        
        if target_position != current_position:
            if current_position == 1 and target_position != 1:
                engine.sell(row['close'], str(idx.date()))
            elif current_position == -1 and target_position != -1:
                engine.buy(row['close'], str(idx.date()), reason='close_short')
            
            if target_position == 1 and current_position != 1:
                engine.buy(row['close'], str(idx.date()))
            elif target_position == -1 and current_position != -1:
                engine.sell(row['close'], str(idx.date()))
        
        current_position = target_position
        engine.update_equity(row['close'])
    
    if engine.position.direction != '':
        engine.close_all(df.iloc[-1]['close'], str(df.index[-1].date()))
    
    metrics = engine.get_metrics()
    metrics['strategy_name'] = strategy.name
    
    return metrics, engine, signals_df


def create_candlestick_chart(df, signals_df=None, strategy_name=""):
    """创建 K 线图"""
    # 创建子图
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{strategy_name} K 线图', '成交量')
    )
    
    # K 线图
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K 线',
            increasing_line_color='#00ff88',
            decreasing_line_color='#ff4444'
        ),
        row=1, col=1
    )
    
    # 添加信号标记
    if signals_df is not None and 'signal' in signals_df.columns:
        buy_signals = signals_df[signals_df['signal'] == 1]
        sell_signals = signals_df[signals_df['signal'] == -1]
        
        # 买入信号
        if len(buy_signals) > 0:
            fig.add_trace(
                go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['low'] * 0.98,
                    mode='markers',
                    marker=dict(symbol='triangle-up', size=15, color='#00ff88'),
                    name='买入信号',
                    hovertext=[f"价格：${p:.2f}" for p in buy_signals['close']],
                    hoverinfo='text+x'
                ),
                row=1, col=1
            )
        
        # 卖出信号
        if len(sell_signals) > 0:
            fig.add_trace(
                go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['high'] * 1.02,
                    mode='markers',
                    marker=dict(symbol='triangle-down', size=15, color='#ff4444'),
                    name='卖出信号',
                    hovertext=[f"价格：${p:.2f}" for p in sell_signals['close']],
                    hoverinfo='text+x'
                ),
                row=1, col=1
            )
    
    # 成交量
    colors = ['#00ff88' if df['close'].iloc[i] >= df['open'].iloc[i] else '#ff4444' 
              for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['volume'],
            name='成交量',
            marker_color=colors,
            opacity=0.5
        ),
        row=2, col=1
    )
    
    # 布局
    fig.update_layout(
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(x=0, y=1),
        hovermode='x unified',
        template='plotly_dark',
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    fig.update_xaxes(title_text="日期", row=2, col=1)
    fig.update_yaxes(title_text="价格 (USD)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    return fig


def create_equity_curve(engine):
    """创建权益曲线图"""
    fig = go.Figure()
    
    equity_series = pd.Series(engine.equity_curve)
    
    fig.add_trace(
        go.Scatter(
            y=equity_series,
            mode='lines',
            name='权益曲线',
            line=dict(color='#00ff88', width=2)
        )
    )
    
    # 添加初始资金线
    fig.add_trace(
        go.Scatter(
            y=[engine.initial_capital] * len(equity_series),
            mode='lines',
            name='初始资金',
            line=dict(color='#888', width=1, dash='dash')
        )
    )
    
    fig.update_layout(
        height=300,
        title='权益曲线',
        xaxis_title='交易日',
        yaxis_title='资金 (USD)',
        template='plotly_dark',
        showlegend=True,
        margin=dict(l=50, r=50, t=50, b=50)
    )
    
    return fig


# 侧边栏
st.sidebar.title("🎛️ 控制面板")

# 策略选择
st.sidebar.subheader("📊 策略选择")
strategies = {
    '趋势跟踪 (海龟)': TrendFollowingStrategy,
    '123/2B 反转': Reversal123Strategy,
    '支撑阻力': SupportResistanceStrategy,
    '形态交易': PatternTradingStrategy,
    '均线交叉': MACrossStrategy,
    '波动率突破': VolatilityBreakoutStrategy,
    '布林带': BollingerBandsStrategy,
    'RSI': RSIStrategy,
    '突破策略': BreakoutStrategy
}

selected_strategy_name = st.sidebar.selectbox(
    "选择策略",
    list(strategies.keys()),
    index=4  # 默认均线交叉
)

# 参数设置
st.sidebar.subheader("⚙️ 参数设置")

symbol = st.sidebar.text_input("交易标的", value="BTC-USD")
start_date = st.sidebar.date_input("开始日期", value=datetime(2022, 1, 1))
end_date = st.sidebar.date_input("结束日期", value=datetime(2024, 12, 31))
initial_capital = st.sidebar.number_input("初始资金 (USD)", value=100000, step=10000)

# 高级参数
with st.sidebar.expander("🔧 策略参数"):
    if selected_strategy_name == '均线交叉':
        fast_period = st.number_input("快线周期", value=12, min_value=5)
        slow_period = st.number_input("慢线周期", value=26, min_value=10)
        filter_ma = st.number_input("过滤均线", value=200, min_value=50)
    elif selected_strategy_name == '趋势跟踪 (海龟)':
        entry_period = st.number_input("入场周期", value=20, min_value=10)
        exit_period = st.number_input("出场周期", value=10, min_value=5)
        atr_period = st.number_input("ATR 周期", value=14, min_value=7)
    elif selected_strategy_name == 'RSI':
        rsi_period = st.number_input("RSI 周期", value=14, min_value=7)
        oversold = st.number_input("超卖线", value=30, min_value=20)
        overbought = st.number_input("超买线", value=70, min_value=60)
    else:
        st.info("该策略使用默认参数")

# 主界面
st.title("📈 交易策略回测系统")
st.markdown("---")

# 加载数据
with st.spinner(f"正在加载 {symbol} 数据..."):
    try:
        df = load_data(symbol, str(start_date), str(end_date))
        st.success(f"✅ 数据加载完成：{len(df)} 行 ({df.index[0].date()} 至 {df.index[-1].date()})")
    except Exception as e:
        st.error(f"❌ 数据加载失败：{e}")
        st.stop()

# 创建策略实例
strategy_class = strategies[selected_strategy_name]

if selected_strategy_name == '均线交叉':
    strategy = strategy_class(fast_period=fast_period, slow_period=slow_period, filter_ma=filter_ma)
elif selected_strategy_name == '趋势跟踪 (海龟)':
    strategy = strategy_class(entry_period=entry_period, exit_period=exit_period, atr_period=atr_period)
elif selected_strategy_name == 'RSI':
    strategy = strategy_class(rsi_period=rsi_period, oversold=oversold, overbought=overbought)
else:
    strategy = strategy_class()

# 运行回测
with st.spinner(f"正在运行 {selected_strategy_name} 回测..."):
    metrics, engine, signals_df = run_strategy_backtest(strategy, df, initial_capital)

# 显示统计指标
st.subheader("📊 回测结果")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_return = metrics.get('total_return', 0) * 100
    color = "#00ff88" if total_return > 0 else "#ff4444"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">总收益</div>
        <div class="metric-value" style="color: {color}">{total_return:+.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    win_rate = metrics.get('win_rate', 0) * 100
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">胜率</div>
        <div class="metric-value">{win_rate:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    total_trades = metrics.get('total_trades', 0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">交易次数</div>
        <div class="metric-value">{total_trades}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    sharpe = metrics.get('sharpe_ratio', 0)
    color = "#00ff88" if sharpe > 0.5 else "#ffaa00" if sharpe > 0 else "#ff4444"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">夏普比率</div>
        <div class="metric-value" style="color: {color}">{sharpe:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    max_dd = metrics.get('max_drawdown', 0) * 100
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">最大回撤</div>
        <div class="metric-value" style="color: #ff4444">{max_dd:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

# 显示图表
st.markdown("---")

# K 线图
st.subheader("🕯️ K 线图与信号")
candlestick_fig = create_candlestick_chart(df, signals_df, selected_strategy_name)
st.plotly_chart(candlestick_fig, use_container_width=True)

# 权益曲线
st.subheader("💰 权益曲线")
equity_fig = create_equity_curve(engine)
st.plotly_chart(equity_fig, use_container_width=True)

# 详细统计
with st.expander("📋 详细统计数据"):
    st.write(f"**策略名称**: {metrics.get('strategy_name', 'N/A')}")
    st.write(f"**总盈亏**: ${metrics.get('total_pnl', 0):,.2f}")
    st.write(f"**最终权益**: ${metrics.get('final_equity', 0):,.2f}")
    st.write(f"**盈利交易**: {metrics.get('winning_trades', 0)}")
    st.write(f"**亏损交易**: {metrics.get('losing_trades', 0)}")
    st.write(f"**平均盈利**: ${metrics.get('avg_win', 0):,.2f}")
    st.write(f"**平均亏损**: ${metrics.get('avg_loss', 0):,.2f}")
    st.write(f"**盈亏比**: {metrics.get('profit_factor', 0):.2f}")

# 信号列表 - 单独一个页面区域
st.markdown("---")
st.subheader("📡 交易信号列表")

if 'signal' in signals_df.columns:
    signal_rows = signals_df[signals_df['signal'] != 0]
    
    if len(signal_rows) > 0:
        # 创建信号详情表格
        signal_data = []
        for idx, row in signal_rows.iterrows():
            signal_action = "🟢 买入" if row['signal'] == 1 else "🔴 卖出"
            position_type = "开多" if row.get('position', 0) == 1 else "开空" if row.get('position', 0) == -1 else "平仓"
            
            signal_data.append({
                '日期': str(idx.date()),
                '信号类型': signal_action,
                '操作': position_type,
                '价格 (USD)': f"${row['close']:.2f}",
                '信号值': int(row['signal']),
                '仓位': int(row.get('position', 0))
            })
        
        signal_df = pd.DataFrame(signal_data)
        
        # 显示统计
        buy_count = len(signal_df[signal_df['信号值'] == 1])
        sell_count = len(signal_df[signal_df['信号值'] == -1])
        st.write(f"**总信号数**: {len(signal_df)} | 🟢 买入：{buy_count} | 🔴 卖出：{sell_count}")
        
        # 显示表格
        st.dataframe(
            signal_df[['日期', '信号类型', '操作', '价格 (USD)']],
            use_container_width=True,
            hide_index=True
        )
        
        # 导出按钮
        csv = signal_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 导出信号 CSV",
            data=csv,
            file_name=f"signals_{symbol}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("⚠️ 该策略在选定时间段内无交易信号")
else:
    st.info("ℹ️ 该策略未生成信号数据")

# 底部信息
st.markdown("---")
st.caption("📌 提示：图表支持缩放、平移和悬停查看详细信息 | 数据仅供参考，不构成投资建议")
