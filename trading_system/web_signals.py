#!/usr/bin/env python3
"""
信号中心 - Web 界面
显示所有历史信号，包含 AI 评分对比
"""
import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# 北京时间时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')

st.set_page_config(
    page_title="📡 信号中心 - AI 评分",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    div[data-testid="stMetricValue"] { font-size: 1.5em; }
    .signal-card {
        background: linear-gradient(135deg, #1e1e1e, #2a2a2a);
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #4CAF50;
    }
    .signal-card.sell {
        border-left-color: #f44336;
    }
    .ai-agree {
        background: linear-gradient(135deg, #1b5e20, #2e7d32);
        padding: 5px 10px;
        border-radius: 5px;
        display: inline-block;
        font-weight: bold;
    }
    .ai-disagree {
        background: linear-gradient(135deg, #b71c1c, #c62828);
        padding: 5px 10px;
        border-radius: 5px;
        display: inline-block;
        font-weight: bold;
    }
    .ai-wait {
        background: linear-gradient(135deg, #f57f17, #f9a825);
        padding: 5px 10px;
        border-radius: 5px;
        display: inline-block;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=60)  # 1 分钟缓存
def load_signals(limit=100):
    """加载信号数据"""
    db_path = Path(__file__).parent / 'cache' / 'trading.db'
    
    if not db_path.exists():
        return pd.DataFrame()
    
    try:
        conn = sqlite3.connect(db_path)
        
        query = f'''
            SELECT 
                signal_id, symbol, timeframe, strategy_name, action, direction,
                entry_price, stop_loss_price, take_profit_price, confidence,
                reason, position_pct, status, ai_score, ai_direction, ai_reason,
                timestamp, created_at
            FROM signals
            ORDER BY created_at DESC
            LIMIT {limit}
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    except Exception as e:
        st.error(f"加载数据失败：{e}")
        return pd.DataFrame()

# 侧边栏
st.sidebar.title("🎛️ 筛选")

# 加载数据
with st.spinner("📡 加载信号数据..."):
    signals_df = load_signals(limit=100)

if signals_df.empty:
    st.warning("📭 暂无信号数据")
    st.info("等待系统扫描生成信号...")
    st.stop()

# 筛选器
st.sidebar.markdown("### 🔍 筛选条件")

# 币种筛选
all_symbols = signals_df['symbol'].unique().tolist()
selected_symbols = st.sidebar.multiselect("币种", all_symbols, default=all_symbols[:10])

# 策略筛选
all_strategies = signals_df['strategy_name'].unique().tolist()
selected_strategy = st.sidebar.selectbox("策略", ["全部"] + all_strategies)

# 方向筛选
direction_filter = st.sidebar.radio("方向", ["全部", "LONG", "SHORT"])

# AI 判断筛选
ai_filter = st.sidebar.selectbox("AI 判断", ["全部", "一致", "分歧", "AI 观望"])

# 应用筛选
filtered_df = signals_df.copy()

if selected_symbols:
    filtered_df = filtered_df[filtered_df['symbol'].isin(selected_symbols)]

if selected_strategy != "全部":
    filtered_df = filtered_df[filtered_df['strategy_name'] == selected_strategy]

if direction_filter != "全部":
    filtered_df = filtered_df[filtered_df['direction'] == direction_filter]

if ai_filter != "全部":
    if ai_filter == "一致":
        filtered_df = filtered_df[filtered_df['ai_direction'] == filtered_df['direction']]
    elif ai_filter == "分歧":
        filtered_df = filtered_df[
            (filtered_df['ai_direction'] != filtered_df['direction']) & 
            (filtered_df['ai_direction'] != 'WAIT')
        ]
    elif ai_filter == "AI 观望":
        filtered_df = filtered_df[filtered_df['ai_direction'] == 'WAIT']

# 主界面
st.title("📡 信号中心")
st.caption(f"数据更新：{get_beijing_time()}")

st.markdown("---")

# 统计卡片
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("📊 总信号", len(filtered_df))

with col2:
    long_count = len(filtered_df[filtered_df['direction'] == 'LONG'])
    st.metric("🟢 做多", long_count)

with col3:
    short_count = len(filtered_df[filtered_df['direction'] == 'SHORT'])
    st.metric("🔴 做空", short_count)

with col4:
    if 'ai_direction' in filtered_df.columns:
        agree_count = len(filtered_df[filtered_df['ai_direction'] == filtered_df['direction']])
        st.metric("🤝 AI 一致", agree_count)
    else:
        st.metric("🤝 AI 一致", 0)

with col5:
    if 'ai_direction' in filtered_df.columns:
        disagree_count = len(filtered_df[
            (filtered_df['ai_direction'] != filtered_df['direction']) & 
            (filtered_df['ai_direction'] != 'WAIT')
        ])
        st.metric("⚠️ AI 分歧", disagree_count)
    else:
        st.metric("⚠️ AI 分歧", 0)

st.markdown("---")

# 信号列表
st.subheader(f"📋 信号列表 ({len(filtered_df)} 个)")

if not filtered_df.empty:
    # 显示详细表格
    display_df = filtered_df.copy()
    
    # 格式化列
    display_df['价格'] = display_df['entry_price'].apply(lambda x: f"${x:,.4f}" if x < 1 else f"${x:,.2f}")
    display_df['置信度'] = display_df['confidence'].apply(lambda x: f"{x:.0f}%")
    display_df['时间'] = display_df['created_at'].apply(lambda x: x[:16].replace('T', ' ') if x else '')
    
    # AI 判断列
    def get_ai_badge(row):
        if pd.isna(row.get('ai_direction')):
            return "⚪ 未评分"
        ai_dir = row['ai_direction']
        strategy_dir = row['direction']
        score = row.get('ai_score', 0)
        
        if ai_dir == 'WAIT':
            return f"⏸️ 观望 ({score}%)"
        elif ai_dir == strategy_dir:
            return f"✅ {ai_dir} ({score}%)"
        else:
            return f"❌ {ai_dir} ({score}%)"
    
    display_df['AI 判断'] = display_df.apply(get_ai_badge, axis=1)
    
    # 选择显示的列
    show_columns = [
        '时间', '币种' if '币种' in display_df.columns else 'symbol',
        '策略' if '策略' in display_df.columns else 'strategy_name',
        '方向' if '方向' in display_df.columns else 'direction',
        '价格', '置信度', 'AI 判断'
    ]
    
    # 重命名列
    column_names = {
        'symbol': '币种',
        'strategy_name': '策略',
        'direction': '方向',
        'entry_price': '价格',
        'confidence': '置信度',
        'created_at': '时间'
    }
    
    display_df = display_df.rename(columns=column_names)
    
    # 显示交互式表格
    st.dataframe(
        display_df[[column_names.get(col, col) for col in show_columns if column_names.get(col, col) in display_df.columns]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "时间": st.column_config.TextColumn("时间", width="medium"),
            "币种": st.column_config.TextColumn("币种", width="small"),
            "策略": st.column_config.TextColumn("策略", width="medium"),
            "方向": st.column_config.TextColumn("方向", width="small"),
            "价格": st.column_config.TextColumn("价格", width="small"),
            "置信度": st.column_config.TextColumn("置信度", width="small"),
            "AI 判断": st.column_config.TextColumn("AI 判断", width="medium")
        }
    )
    
    st.markdown("---")
    
    # 详细信号卡片
    st.subheader("📋 信号详情")
    
    for idx, row in filtered_df.head(20).iterrows():
        action = row.get('action', 'BUY')
        direction = row.get('direction', 'LONG')
        symbol = row.get('symbol', 'N/A')
        strategy = row.get('strategy_name', 'Unknown')
        price = row.get('entry_price', 0)
        confidence = row.get('confidence', 0)
        timestamp = row.get('created_at', '')[:16].replace('T', ' ') if row.get('created_at') else ''
        reason = row.get('reason', 'N/A')
        stop_loss = row.get('stop_loss_price', 0)
        take_profit = row.get('take_profit_price', 0)
        
        # AI 评分
        ai_score = row.get('ai_score')
        ai_direction = row.get('ai_direction')
        ai_reason = row.get('ai_reason', '')
        
        # 判断一致性
        ai_status = "unknown"
        if ai_direction:
            if ai_direction == 'WAIT':
                ai_status = "wait"
            elif ai_direction == direction:
                ai_status = "agree"
            else:
                ai_status = "disagree"
        
        # 信号卡片
        action_emoji = "🟢" if action == "BUY" else "🔴"
        
        with st.container():
            st.markdown(f"""
            <div class="signal-card {'sell' if action == 'SELL' else ''}">
                <h3>{action_emoji}【{strategy}】{symbol} {direction}</h3>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("💰 价格", f"${price:,.4f}" if price < 1 else f"${price:,.2f}")
            with col2:
                st.metric("📈 置信度", f"{confidence:.0f}%")
            with col3:
                st.metric("📅 时间", timestamp[:10] if timestamp else 'N/A')
            with col4:
                if ai_score:
                    st.metric("🤖 AI 评分", f"{ai_score}%")
                else:
                    st.metric("🤖 AI 评分", "未评分")
            
            # AI 判断状态
            if ai_direction:
                if ai_status == "agree":
                    st.markdown('<span class="ai-agree">✅ AI 同意</span>', unsafe_allow_html=True)
                elif ai_status == "disagree":
                    st.markdown('<span class="ai-disagree">❌ AI 反对 ({})</span>'.format(ai_direction), unsafe_allow_html=True)
                elif ai_status == "wait":
                    st.markdown('<span class="ai-wait">⏸️ AI 观望</span>', unsafe_allow_html=True)
            
            # 信号理由
            with st.expander("💡 信号理由", expanded=False):
                st.write(reason)
            
            # AI 理由
            if ai_reason:
                with st.expander("🤖 AI 分析", expanded=False):
                    st.write(ai_reason)
            
            # 风险管理
            col_stop, col_target, col_rr = st.columns(3)
            with col_stop:
                st.error(f"🛑 止损\n${stop_loss:,.4f}" if stop_loss < 1 else f"🛑 止损\n${stop_loss:,.2f}")
            with col_target:
                st.success(f"🎯 止盈\n${take_profit:,.4f}" if take_profit < 1 else f"🎯 止盈\n${take_profit:,.2f}")
            
            st.divider()

else:
    st.info("没有符合条件的信号")
