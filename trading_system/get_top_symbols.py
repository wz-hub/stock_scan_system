"""
获取 Binance 全市场交易量数据
按 24 小时交易量排序
"""
import requests
import pandas as pd
from datetime import datetime

print("📊 获取 Binance 全市场交易量数据")
print("="*80)

# Binance 24 小时行情接口
url = "https://api.binance.com/api/v3/ticker/24hr"

try:
    response = requests.get(url, timeout=30)
    data = response.json()
    
    print(f"✅ 获取到 {len(data)} 个交易对")
    
    # 转换为 DataFrame
    df = pd.DataFrame(data)
    
    # 只保留 USDT 交易对
    df = df[df['symbol'].str.endswith('USDT')]
    
    # 转换数据类型
    df['quoteVolume'] = pd.to_numeric(df['quoteVolume'])  # USDT 交易量
    df['count'] = pd.to_numeric(df['count'])  # 交易次数
    df['priceChangePercent'] = pd.to_numeric(df['priceChangePercent'])  # 24h 涨跌幅
    
    # 按 USDT 交易量排序
    df_sorted = df.sort_values('quoteVolume', ascending=False)
    
    print("\n🏆 交易量前 50 的币种（USDT 交易对）")
    print("="*80)
    
    # 显示前 50
    top_50 = df_sorted.head(50)
    
    for idx, row in top_50.iterrows():
        symbol = row['symbol'].replace('USDT', '')
        volume_usdt = float(row['quoteVolume']) / 1e6  # 百万 USDT
        price = float(row['lastPrice'])
        change_24h = float(row['priceChangePercent'])
        
        # 格式化
        if price < 1:
            price_str = f"${price:.6f}"
        elif price < 100:
            price_str = f"${price:.2f}"
        else:
            price_str = f"${price:,.2f}"
        
        change_emoji = "🟢" if change_24h >= 0 else "🔴"
        
        print(f"{idx+1:2d}. {symbol:8s}  {price_str:>12}  {change_emoji} {change_24h:+6.2f}%  24h 成交量：{volume_usdt:,.0f}M USDT")
    
    print("="*80)
    
    # 保存为 CSV
    output_file = '/home/wz/.openclaw/workspace/trading_system/data/top_symbols.csv'
    top_50.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n✅ 已保存到：{output_file}")
    
    # 生成 Python 列表（方便代码中使用）
    print("\n📋 Python 列表（前 20）:")
    top_20_symbols = df_sorted.head(20)['symbol'].tolist()
    print(f"symbols = {top_20_symbols}")
    
    print("\n📋 Python 列表（前 50）:")
    top_50_symbols = df_sorted.head(50)['symbol'].tolist()
    print(f"symbols = {top_50_symbols}")
    
except Exception as e:
    print(f"❌ 获取失败：{e}")
