"""
Web 页面 - 资金流向排行榜
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent))

from money_flow import MoneyFlowMonitor, format_money_value

st.set_page_config(
    page_title="💰 资金流向",
    page_icon="💰",
    layout="wide"
)

st.title("💰 全市场资金流向排行榜")
st.caption(f"数据更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 数据源：Binance 24h 行情")

st.markdown("---")

# 获取数据
@st.cache_data(ttl=300)  # 5 分钟缓存
def get_flow_data():
    monitor = MoneyFlowMonitor()
    return monitor.get_money_flow_ranking(top_n=50)

with st.spinner("💰 加载资金流向数据..."):
    ranking = get_flow_data()

if not ranking['inflow_top20']:
    st.error("❌ 获取数据失败，请稍后刷新")
    st.stop()

# 选项卡
tab1, tab2, tab3, tab4 = st.tabs(["🟢 净流入 Top20", "🔴 净流出 Top20", "📈 涨幅 Top20", "📉 跌幅 Top20"])

with tab1:
    st.subheader("🟢 资金净流入 Top20")
    
    # 创建表格数据
    df_inflow = pd.DataFrame(ranking['inflow_top20'])
    
    # 格式化显示
    display_df = df_inflow.copy()
    display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
    display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
    display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
    display_df['方向'] = display_df['net_flow'].apply(lambda x: "↑" if x > 0 else "↓")
    
    # 显示表格
    st.dataframe(
        display_df[['symbol_short', '净流量', '24h 成交量', '24h 涨跌', '方向', 'price']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol_short": "合约",
            "净流量": st.column_config.TextColumn("净流量"),
            "24h 成交量": st.column_config.TextColumn("24h 成交量"),
            "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
            "方向": st.column_config.TextColumn("方向"),
            "price": st.column_config.NumberColumn("价格", format="$%.4f")
        }
    )

with tab2:
    st.subheader("🔴 资金净流出 Top20")
    
    df_outflow = pd.DataFrame(ranking['outflow_top20'])
    
    display_df = df_outflow.copy()
    display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
    display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
    display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
    display_df['方向'] = display_df['net_flow'].apply(lambda x: "↑" if x > 0 else "↓")
    
    st.dataframe(
        display_df[['symbol_short', '净流量', '24h 成交量', '24h 涨跌', '方向', 'price']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol_short": "合约",
            "净流量": st.column_config.TextColumn("净流量"),
            "24h 成交量": st.column_config.TextColumn("24h 成交量"),
            "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
            "方向": st.column_config.TextColumn("方向"),
            "price": st.column_config.NumberColumn("价格", format="$%.4f")
        }
    )

with tab3:
    st.subheader("📈 24h 涨幅 Top20")
    
    df_pct_in = pd.DataFrame(ranking['pct_inflow_top20'])
    
    display_df = df_pct_in.copy()
    display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
    display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
    display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
    
    st.dataframe(
        display_df[['symbol_short', '24h 涨跌', '净流量', '24h 成交量', 'price']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol_short": "合约",
            "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
            "净流量": st.column_config.TextColumn("净流量"),
            "24h 成交量": st.column_config.TextColumn("24h 成交量"),
            "price": st.column_config.NumberColumn("价格", format="$%.4f")
        }
    )

with tab4:
    st.subheader("📉 24h 跌幅 Top20")
    
    df_pct_out = pd.DataFrame(ranking['pct_outflow_top20'])
    
    display_df = df_pct_out.copy()
    display_df['净流量'] = display_df['net_flow'].apply(format_money_value)
    display_df['24h 成交量'] = display_df['volume_24h'].apply(format_money_value)
    display_df['24h 涨跌'] = display_df['change_pct'].apply(lambda x: f"{x:+.2f}%")
    
    st.dataframe(
        display_df[['symbol_short', '24h 涨跌', '净流量', '24h 成交量', 'price']],
        use_container_width=True,
        hide_index=True,
        column_config={
            "symbol_short": "合约",
            "24h 涨跌": st.column_config.TextColumn("24h 涨跌"),
            "净流量": st.column_config.TextColumn("净流量"),
            "24h 成交量": st.column_config.TextColumn("24h 成交量"),
            "price": st.column_config.NumberColumn("价格", format="$%.4f")
        }
    )

# 侧边栏信息
st.sidebar.title("ℹ️ 使用说明")
st.sidebar.markdown("""
**数据来源:** Binance 现货 24h 行情

**计算方法:**
净流量 = 24h 成交量 × 涨跌幅

**解读:**
- 净流入 = 资金买入 > 卖出
- 净流出 = 资金卖出 > 买入

**更新频率:** 每 5 分钟自动刷新

**扫描集成:**
流入 Top20 + 流出 Top20
自动加入信号扫描器
""")

# 刷新按钮
if st.sidebar.button("🔄 立即刷新"):
    st.cache_data.clear()
    st.rerun()

# 底部统计
st.markdown("---")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("📊 扫描币种", len(ranking['all_data']))
with col2:
    total_inflow = sum(item['net_flow'] for item in ranking['inflow_top20'])
    st.metric("🟢 净流入总额", format_money_value(total_inflow))
with col3:
    total_outflow = abs(sum(item['net_flow'] for item in ranking['outflow_top20']))
    st.metric("🔴 净流出总额", format_money_value(total_outflow))
